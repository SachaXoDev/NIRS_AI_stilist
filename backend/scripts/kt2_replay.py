#!/usr/bin/env python3
"""Re-check recorded KT-2 answers with the current server-side review. No model is called.

A benchmark run stores every model answer in per_query.json. This script feeds those answers
through `app.kt2_grounding` again and grades the result with the benchmark's own rules, so the
effect of the review layer is measured on fixed retrieval AND fixed model output:

    python scripts/kt2_replay.py kt2_data/conclusions_run

It also lists, per question, the sentences of the cited documents that the answer left out —
the candidates the optional coverage pass (KT2_COVERAGE_PASS=true) would show to the model.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kt2_benchmark as bench  # noqa: E402
from app.kt2_grounding import render, review_answer, unused_sentences  # noqa: E402

_LINE = re.compile(r"^(?P<text>.*?)\s*(?P<ids>(?:\[D\d{2}\]\s*)+)$")


def recorded_draft(answer: str) -> list[tuple[str, str]]:
    """Recover `[(text, source id)]` from an answer rendered as one statement per line."""
    draft = []
    for line in answer.split("\n"):
        match = _LINE.match(line.strip())
        if not match:
            raise ValueError(f"Cannot split a recorded answer line into text and citation: {line!r}")
        draft.append((match["text"], bench.CITATION.findall(match["ids"])[0]))
    return draft


def replay(row: dict) -> dict | None:
    response = row.get("response")
    if not response or response["refused"]:
        return None
    documents = {hit["id"]: hit["text"] for hit in response["hits"]}
    question = row["request"]["question"]
    review = review_answer(question, documents, recorded_draft(response["answer"]))
    answer = render(review.parts)
    by_id = {hit["id"]: hit for hit in response["hits"]}
    cited = list(dict.fromkeys(doc_id for part in review.parts for doc_id in part.source_ids))
    checked = dict(response, answer=answer, sources=[by_id[doc_id] for doc_id in cited])
    return {
        "id": row["id"],
        "kind": row["kind"],
        "answer": answer,
        "checks": review.notes,
        "unverified": [part.text for part in review.parts if not part.verified],
        "unused": [{"id": doc_id, "text": sentence}
                   for doc_id, sentence in unused_sentences(question, documents, review.parts)],
        "before": row["metrics"],
        "after": bench.grade(row["ground_truth"], checked),
    }


def facts(metrics: dict) -> int:
    return sum(check["passed"] for check in metrics["fact_checks"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path, help="Directory with per_query.json from kt2_benchmark.py")
    parser.add_argument("--output", type=Path, help="Save the re-checked answers as JSON")
    args = parser.parse_args()
    rows = json.loads((args.run / "per_query.json").read_text(encoding="utf-8"))
    results = [result for result in map(replay, rows) if result]

    print("| Вопрос | Факты до → после | Источники до → после | Что изменил сервер | Не отражено предложений |")
    print("|---|---|---|---|---:|")
    for result in results:
        before, after = result["before"], result["after"]
        total = len(before["fact_checks"])
        print(f"| {result['id']} | {facts(before)}/{total} → {facts(after)}/{total} "
              f"| {', '.join(before['source_ids'])} → {', '.join(after['source_ids'])} "
              f"| {'; '.join(result['checks']) or '—'} | {len(result['unused'])} |")
    positives = [result for result in results if result["kind"] == "positive"]
    print(f"\nОтветов: {len(results)}. Эвристическая Accuracy: "
          f"{sum(r['before']['accuracy'] for r in positives)} → {sum(r['after']['accuracy'] for r in positives)}; "
          f"фактов: {sum(facts(r['before']) for r in positives)} → {sum(facts(r['after']) for r in positives)}; "
          f"ответов с правками сервера: {sum(bool(r['checks']) for r in results)}; "
          f"с неподтверждённым значением: {sum(bool(r['unverified']) for r in results)}.")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
