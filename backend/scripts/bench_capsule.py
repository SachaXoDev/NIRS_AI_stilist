#!/usr/bin/env python3
"""Measure where the time goes on the full 50-item capsule, against a running server.

Three modes, as a user meets them:
  first   — the wardrobe is indexed for the first time, then an outfit is picked;
  repeat  — the same request again (nothing changed in the wardrobe);
  edited  — one item was edited, then an outfit is picked.

Each mode is split into indexing (sync), search (retrieval) and the LLM. Indexing is called
explicitly so its own breakdown is visible: how many texts and images were encoded and how many
were reused. To reproduce the "before" numbers start the server with RAG_EMBEDDING_CACHE=false;
for a truly cold first run point RAG_DATA_DIR at an empty directory.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx

from defense_smoke import OFFICE_QUERY, SmokeFailure, request_json, require

MODES = ("first", "repeat", "edited")


def measure(client: httpx.Client, user_id: str, wardrobe: list[dict[str, Any]]) -> dict[str, Any]:
    sync, sync_wall = request_json(client, "POST", "/api/wardrobe/sync", json={"user_id": user_id, "items": wardrobe})
    require(sync.get("indexed_count") == len(wardrobe), f"sync indexed {sync.get('indexed_count')} of {len(wardrobe)}")
    result, wall = request_json(client, "POST", "/api/recommend-outfit", json={
        "user_id": user_id, "query": OFFICE_QUERY, "context": {"occasion": "business"},
        "wardrobe": wardrobe, "mode": "hybrid",
    })
    timings = result.get("timings", {})
    index = sync.get("timings_ms", {})
    return {
        "index_ms": sync_wall + float(timings.get("syncMs", 0.0)),
        "index_text_ms": float(index.get("text_embedding_ms", 0.0)),
        "index_image_ms": float(index.get("image_embedding_ms", 0.0)),
        "index_persist_ms": float(index.get("persist_ms", 0.0)),
        "encoded": f"{sync.get('encoded_text_count', '?')}+{sync.get('encoded_image_count', '?')}",
        "reused": f"{sync.get('reused_text_count', '?')}+{sync.get('reused_image_count', '?')}",
        "search_ms": float(timings.get("retrievalMs", 0.0)),
        "llm_ms": float(timings.get("llmMs", 0.0)),
        "total_ms": sync_wall + wall,
        "source": result.get("source"),
        "retriever": (result.get("meta") or {}).get("retriever"),
        "model": (result.get("meta") or {}).get("llmModel"),
    }


def run(client: httpx.Client, user_id: str, repeats: int) -> dict[str, Any]:
    health, _ = request_json(client, "GET", "/health")
    capsule, _ = request_json(client, "GET", "/api/wardrobe/base-capsule")
    require(isinstance(capsule, list) and len(capsule) >= 50, "expected the 50-item base capsule")
    rows: dict[str, list[dict[str, Any]]] = {mode: [] for mode in MODES}
    try:
        rows["first"].append(measure(client, user_id, capsule))
        for _ in range(repeats):
            rows["repeat"].append(measure(client, user_id, capsule))
        for n in range(repeats):
            # A user edits one field of one item: only that item should need the encoders.
            edited = [dict(capsule[0], color=f"{capsule[0].get('color', '')} · правка {n + 1}"), *capsule[1:]]
            rows["edited"].append(measure(client, user_id, edited))
    finally:
        request_json(client, "POST", "/api/wardrobe/sync", json={"user_id": user_id, "items": []})
    return {"health": health, "items": len(capsule), "repeats": repeats, "rows": rows}


def median(rows: list[dict[str, Any]], key: str) -> float:
    return statistics.median(row[key] for row in rows)


def render(report: dict[str, Any]) -> str:
    retrieval = report["health"].get("retrieval", {})
    llm = report["health"].get("llm", {})
    cache = retrieval.get("embedding_cache")
    lines = [
        f"Капсула: {report['items']} вещей · поиск: {retrieval.get('engine')} · LLM: {llm.get('model')} "
        f"· кеш эмбеддингов: {'включён' if cache else 'выключен' if cache is False else 'нет данных'} "
        f"· повторов: {report['repeats']} (медиана)",
        "",
        "| Режим | Индексация, мс | из них текст / фото / запись | Закодировано (текст+фото) | Переиспользовано "
        "| Поиск, мс | LLM, мс | Всего, мс | Источник |",
        "|---|---:|---|---|---|---:|---:|---:|---|",
    ]
    names = {"first": "Первый подбор", "repeat": "Повторный запрос", "edited": "После правки одной вещи"}
    for mode in MODES:
        rows = report["rows"][mode]
        last = rows[-1]
        lines.append(
            f"| {names[mode]} | {median(rows, 'index_ms'):.0f} "
            f"| {median(rows, 'index_text_ms'):.0f} / {median(rows, 'index_image_ms'):.0f} / "
            f"{median(rows, 'index_persist_ms'):.0f} | {last['encoded']} | {last['reused']} "
            f"| {median(rows, 'search_ms'):.0f} | {median(rows, 'llm_ms'):.0f} | {median(rows, 'total_ms'):.0f} "
            f"| {last['source']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=600, help="HTTP timeout in seconds (default: %(default)s)")
    parser.add_argument("--repeats", type=int, default=3, help="Runs of the repeat/edited modes (default: %(default)s)")
    parser.add_argument("--label", default="", help="Shown above the table, e.g. 'до' or 'после'")
    parser.add_argument("--output", type=Path, help="Also save the raw measurements as JSON")
    args = parser.parse_args()
    user_id = f"bench-capsule-{uuid4().hex}"
    started = perf_counter()
    try:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            report = run(client, user_id, max(1, args.repeats))
    except (SmokeFailure, httpx.InvalidURL) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.label:
        print(f"### {args.label}\n")
    print(render(report))
    sources = {row["source"] for rows in report["rows"].values() for row in rows}
    if sources != {"llm"}:
        print(f"\nВнимание: не все ответы получены от LLM (источники: {sorted(map(str, sources))}).", file=sys.stderr)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"label": args.label, **report}, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(f"\nГотово за {perf_counter() - started:.1f} с", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
