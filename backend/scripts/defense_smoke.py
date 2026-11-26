#!/usr/bin/env python3
"""Check the live defense scenarios against an already running FastAPI server."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx

RETRIEVER = "wardrobe_rag"
MODE = "hybrid"
PROVIDER = "openai"  # OpenAI-compatible adapter, including Ollama.
SOURCE = "llm"
CORE_SLOTS = {"tops", "bottoms", "shoes"}
STYLE_QUERY = "С чем носить широкие брюки?"
OFFICE_QUERY = "Подбери образ в офис."
BEACH_QUERY = "Подбери образ на пляж: +30°C, сухая погода."
BEACH_ITEMS = {"item-18", "item-27", "item-39"}
BEACH_CLOSED_SHOES = {"item-18", "item-27", "item-35"}
DEMO_ITEMS = BEACH_ITEMS | BEACH_CLOSED_SHOES | {"item-1", "item-4", "item-6", "item-8", "item-12", "item-21"}


class SmokeFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def request_json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> tuple[Any, float]:
    started = perf_counter()
    try:
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        raise SmokeFailure(f"{method} {path}: HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
    except (httpx.RequestError, ValueError) as exc:
        raise SmokeFailure(f"{method} {path}: {exc}") from exc
    return data, (perf_counter() - started) * 1000


def recommend(
    client: httpx.Client, case: str, user_id: str, model: str, query: str, *,
    source: str = SOURCE, **payload: Any,
) -> dict[str, Any]:
    try:
        result, elapsed = request_json(client, "POST", "/api/recommend-outfit", json={
            "user_id": user_id, "query": query, "debug": True, **payload,
        })
    except SmokeFailure as exc:
        raise SmokeFailure(f"{case}: {exc}") from exc
    require(isinstance(result, dict), f"{case}: expected a recommendation object, got {result!r}")
    meta = result.get("meta")
    require(isinstance(meta, dict), f"{case}: response metadata is missing")
    timings = result.get("timings")
    require(isinstance(timings, dict), f"{case}: response timings are missing")
    measured = " ".join(
        f"{key}={timings[key]:.1f}" for key in ("syncMs", "retrievalMs", "llmMs", "totalMs")
        if isinstance(timings.get(key), (int, float))
    )
    print(
        f"[{case}] clientMs={elapsed:.1f} {measured} source={result.get('source')} "
        f"retriever={meta.get('retriever', '-')} ids={result.get('referencedItemIds')} "
        f"missing={result.get('missingSlots')}",
        flush=True,
    )
    require(result.get("source") == source,
            f"{case}: expected source={source!r}, got {result.get('source')!r}; warnings={result.get('warnings')!r}")
    require(meta.get("llmProvider") == PROVIDER and meta.get("llmModel") == model,
            f"{case}: model metadata does not match /health: {meta!r}")
    attempts = meta.get("llmAttempts")
    require(type(attempts) is int and (attempts > 0 if source == SOURCE else attempts == 0),
            f"{case}: unexpected LLM attempt count {attempts!r} for source={source!r}")
    text = result.get("text")
    require(isinstance(text, str) and bool(text.strip()), f"{case}: response text is empty")
    return result


def check_no_card(result: dict[str, Any], case: str, missing: list[str]) -> None:
    require(result.get("suggestedOutfit") is None, f"{case}: unexpected outfit card")
    require(result.get("referencedItemIds") == [], f"{case}: unexpected referenced items")
    require(result.get("missingSlots") == missing,
            f"{case}: expected missingSlots={missing!r}, got {result.get('missingSlots')!r}")


def check_retrieval(
    result: dict[str, Any], case: str, occasion: str, slots: set[str],
) -> dict[str, Any]:
    require(result["meta"].get("retriever") == RETRIEVER, f"{case}: expected meta.retriever={RETRIEVER}")
    retrieval = result.get("retrieval")
    require(isinstance(retrieval, dict) and retrieval.get("engine") == RETRIEVER,
            f"{case}: missing debug diagnostics for {RETRIEVER}")
    require(retrieval.get("mode") == MODE, f"{case}: expected retrieval mode={MODE}")
    context = retrieval.get("context")
    require(isinstance(context, dict) and context.get("occasion") == occasion,
            f"{case}: expected retrieval occasion={occasion!r}, got {context!r}")
    required = retrieval.get("required_slots")
    require(isinstance(required, list) and all(isinstance(slot, str) for slot in required)
            and Counter(required) == Counter(slots),
            f"{case}: expected required slots {sorted(slots)}, got {required!r}")
    require(retrieval.get("missing_slots") == result.get("missingSlots"),
            f"{case}: retrieval and response disagree on missing slots")
    return retrieval


def check_outfit(
    result: dict[str, Any], case: str, capsule: dict[str, dict[str, Any]], slots: set[str],
) -> set[str]:
    require(result.get("missingSlots") == [], f"{case}: complete outfit must not report missing slots")
    outfit = result.get("suggestedOutfit")
    require(isinstance(outfit, dict), f"{case}: expected an outfit card")
    items = outfit.get("items")
    require(isinstance(items, list) and bool(items), f"{case}: expected items in the card")
    require(not result["text"].startswith("В образ вошли:"), f"{case}: chat repeats the item inventory")
    ids = []
    counts: Counter[str] = Counter()
    for item in items:
        require(isinstance(item, dict), f"{case}: expected wardrobe item objects in the card")
        item_id = item.get("id")
        require(isinstance(item_id, str) and item_id in capsule, f"{case}: item outside capsule: {item_id!r}")
        canonical = capsule[item_id]
        title, category = canonical["title"], canonical["category"]
        require(item.get("title") == title and item.get("category") == category,
                f"{case}: card item {item_id} disagrees with the capsule")
        ids.append(item_id)
        counts[category] += 1
    require(result.get("referencedItemIds") == ids and len(set(ids)) == len(ids),
            f"{case}: referenced IDs must match the distinct card items in order")
    require(all(counts[slot] == 1 for slot in slots),
            f"{case}: card must contain one item per required slot, got {dict(counts)}")
    require(counts["outerwear"] <= 1 and counts["accessories"] <= 2,
            f"{case}: card has too many optional items, got {dict(counts)}")
    return set(ids)


def run_wardrobe_cases(
    client: httpx.Client, user_id: str, model: str,
    capsule: dict[str, dict[str, Any]], history: list[dict[str, Any]],
) -> None:
    full_wardrobe = list(capsule.values())
    common = {"mode": MODE}

    office = recommend(client, "office", user_id, model, OFFICE_QUERY, **common,
                       context={"occasion": "business"}, wardrobe=full_wardrobe, history=history)
    check_outfit(office, "office", capsule, CORE_SLOTS)
    office_retrieval = check_retrieval(office, "office", "business", CORE_SLOTS)

    # Legacy client without itemIds: «потеплее» still uses the full model-driven selection.
    # Targeted edits with itemIds are covered by edit_smoke.py and the backend API tests.
    office_history = [
        *history,
        {"sender": "user", "text": OFFICE_QUERY},
        {"sender": "assistant", "text": office["text"], "hasOutfit": True},
    ]
    warmer = recommend(client, "warmer", user_id, model, "А можно потеплее?", **common, history=office_history)
    warm_slots = CORE_SLOTS | {"outerwear"}
    check_outfit(warmer, "warmer", capsule, warm_slots)
    warmer_retrieval = check_retrieval(warmer, "warmer", "business", warm_slots)
    revision = office_retrieval.get("wardrobe_revision")
    require(bool(revision) and warmer_retrieval.get("wardrobe_revision") == revision,
            "warmer: follow-up must use the office wardrobe revision")

    missing = recommend(client, "missing shoes", user_id, model, OFFICE_QUERY, **common, source="none",
                        context={"occasion": "business"},
                        wardrobe_ids=[item["id"] for item in full_wardrobe if item["category"] != "shoes"])
    check_no_card(missing, "missing shoes", ["shoes"])
    check_retrieval(missing, "missing shoes", "business", CORE_SLOTS)

    beach = recommend(client, "beach", user_id, model, BEACH_QUERY, **common)
    beach_retrieval = check_retrieval(beach, "beach", "beach", CORE_SLOTS)
    require(beach_retrieval["context"].get("temperature_c") == 30, "beach: expected +30°C in retrieval context")
    beach_ids = check_outfit(beach, "beach", capsule, CORE_SLOTS)
    require(BEACH_ITEMS <= beach_ids, f"beach: expected beach shirt, shorts and sandals, got {sorted(beach_ids)}")

    closed_shoe = capsule["item-35"]
    weather = closed_shoe.get("weather")
    require(closed_shoe["category"] == "shoes" and isinstance(weather, dict) and weather.get("open_shoes") is False,
            "beach without sandals: item-35 must be explicitly marked as a closed shoe")
    no_sandals = recommend(client, "beach without sandals", user_id, model, BEACH_QUERY, **common,
                           source="none", wardrobe_ids=sorted(BEACH_CLOSED_SHOES))
    check_no_card(no_sandals, "beach without sandals", ["shoes"])
    check_retrieval(no_sandals, "beach without sandals", "beach", CORE_SLOTS)


def run(client: httpx.Client, user_id: str, *, full_capsule: bool) -> None:
    health, elapsed = request_json(client, "GET", "/health")
    require(isinstance(health, dict) and health.get("status") == "ok", f"Unhealthy backend: {health!r}")
    llm = health.get("llm")
    require(isinstance(llm, dict) and llm.get("provider") == PROVIDER and bool(llm.get("model")),
            f"/health: expected an OpenAI-compatible LLM, got {llm!r}")
    retrieval = health.get("retrieval")
    require(isinstance(retrieval, dict) and retrieval.get("engine") == RETRIEVER,
            f"/health: expected {RETRIEVER}, got {retrieval!r}")
    model = llm["model"]
    print(f"[health] clientMs={elapsed:.1f} provider={PROVIDER} model={model} retriever={RETRIEVER}", flush=True)

    style = recommend(client, "style without wardrobe", user_id, model, STYLE_QUERY, wardrobe=[])
    check_no_card(style, "style without wardrobe", [])
    require("retrieval" not in style and "retriever" not in style["meta"],
            "style without wardrobe: advice must not use retrieval")
    require(not {"syncMs", "retrievalMs"}.intersection(style["timings"]),
            "style without wardrobe: advice must not sync or search a wardrobe")
    history = [{"sender": "user", "text": STYLE_QUERY}, {"sender": "assistant", "text": style["text"]}]

    items, elapsed = request_json(client, "GET", "/api/wardrobe/base-capsule")
    require(isinstance(items, list) and bool(items) and all(
        isinstance(item, dict) and all(isinstance(item.get(key), str) and item[key] for key in ("id", "title", "category"))
        for item in items
    ), "Base capsule must contain wardrobe items with IDs, titles, and categories")
    capsule = {item["id"]: item for item in items}
    require(len(capsule) == len(items), "Base capsule contains duplicate item IDs")
    require((BEACH_ITEMS | BEACH_CLOSED_SHOES) <= capsule.keys(), "Base capsule is missing the beach smoke fixtures")
    print(f"[capsule] clientMs={elapsed:.1f} items={len(items)}", flush=True)
    if not full_capsule:
        require(DEMO_ITEMS <= capsule.keys(), "Base capsule is missing the defense smoke fixtures")
        capsule = {item_id: item for item_id, item in capsule.items() if item_id in DEMO_ITEMS}
    print(f"[wardrobe] items={len(capsule)}", flush=True)

    passed = False
    try:
        run_wardrobe_cases(client, user_id, model, capsule, history)
        passed = True
    finally:
        try:
            sync, elapsed = request_json(client, "POST", "/api/wardrobe/sync", json={"user_id": user_id, "items": []})
            require(isinstance(sync, dict) and sync.get("indexed_count") == 0,
                    f"Could not clear smoke wardrobe {user_id}")
            print(f"[cleanup] clientMs={elapsed:.1f} indexed_count=0", flush=True)
        except SmokeFailure as exc:
            if passed:
                raise
            print(f"Cleanup failed for {user_id}: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI server URL (default: %(default)s)")
    parser.add_argument("--timeout", type=float, default=300, help="HTTP timeout in seconds (default: %(default)s)")
    parser.add_argument("--full-capsule", action="store_true", help="Index all 50 items instead of the small defense subset")
    args = parser.parse_args()
    if not 0 < args.timeout < float("inf"):
        parser.error("--timeout must be a finite positive number")
    user_id = f"defense-smoke-{uuid4().hex}"
    started = perf_counter()
    print(f"Defense smoke: {args.base_url} user_id={user_id}", flush=True)
    try:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            run(client, user_id, full_capsule=args.full_capsule)
    except (SmokeFailure, httpx.InvalidURL) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: six live scenarios ({perf_counter() - started:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
