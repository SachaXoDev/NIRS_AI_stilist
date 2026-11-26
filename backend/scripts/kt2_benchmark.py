#!/usr/bin/env python3
"""Benchmark the running KT-2 demo API (no local retrieval or generation)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

import httpx

DATA = Path(__file__).resolve().parents[1] / "kt2_data"
ENDPOINT = "/api/kt2/ask"
K = 3
DOCUMENT_IDS = {f"D{i:02}" for i in range(1, 31)}
POSITIVE_IDS = {f"Q{i:02}" for i in range(1, 11)}
TRAP_IDS = {f"Q{i:02}" for i in range(11, 16)}
REFUSAL = "В документах нет этой информации."
CITATION = re.compile(r"\[(D[0-9]{2})\]")
TOKEN = re.compile(r"[^\W_]+(?:(?<=[0-9])[.,:](?=[0-9])[^\W_]+)*|[×₽]")
# Keep label/value colons («Год покупки: 1998») inside fact phrases, but treat
# a standalone negative answer («Нет: это метамерия») as a separate clause.
CLAUSE_BREAK = re.compile(r"[;!?…\n]+|(?<![0-9])[.,]|[.,](?![0-9])|\bнет\s*:")
NEGATORS = {"не", "нет", "ни", "нельзя", "никогда", "без", "вместо", "кроме", "запрещено", "неверно", "ошибочно"}
METRIC_RULES = {
    "recall_at_3": "Macro over positives: relevant IDs in the first 3 hits / all labeled relevant IDs.",
    "mrr_at_3": "Macro over positives: reciprocal of the rank of the first relevant hit, or 0.",
    "accuracy": "Positives only: all required fact groups match, not refused, and nonempty inline "
    "citations match sources in order and cite only labeled relevant hits.",
    "refusal_accuracy": "Traps only: refused=true, canonical refusal text (normalized), and no citations.",
    "phrase_matching": "Match one contiguous whole-token phrase per group within a clause, ignoring "
    "citation markers, case, ё/е and cosmetic punctuation. Decimal commas match points; time colons "
    "remain distinct. Reject apparent negation up to four tokens before or immediately after a phrase. "
    "This can miss paraphrases, negation and contradictions and does not verify extra claims or which "
    "source supports each fact. Review answers manually.",
    "incomplete_run": "Any request, generation or response error (or a model change) invalidates "
    "aggregate metrics; errors are not refusals.",
}


def normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")


def tokens(text: str) -> list[str]:
    return [part.replace(",", ".") for part in TOKEN.findall(normalized(text))]


def phrase_positions(words: list[str], phrase: list[str]):
    for start in range(len(words) - len(phrase) + 1):
        if words[start:start + len(phrase)] == phrase:
            yield start


def match_fact(clauses: list[list[str]], alternatives: list[str]) -> dict[str, Any]:
    matched = []
    negated = []
    for alternative in alternatives:
        phrase = tokens(alternative)
        for clause in clauses:
            for start in phrase_positions(clause, phrase):
                before = clause[max(0, start - 4):start]
                after = clause[start + len(phrase):start + len(phrase) + 1]
                if NEGATORS.intersection(before + after):
                    negated.append(alternative)
                else:
                    matched.append(alternative)
    # If the answer both affirms and negates an alias, do not credit the group.
    return {"alternatives": alternatives, "affirmative_matches": sorted(set(matched)),
            "negated_matches": sorted(set(negated)), "passed": bool(matched) and not negated}


def answer_clauses(text: str) -> list[list[str]]:
    return [tokens(clause) for clause in CLAUSE_BREAK.split(normalized(CITATION.sub(" ", text)))]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        check(key not in result, f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON value: {value}")


def parse_float(value: str) -> float:
    number = float(value)
    check(math.isfinite(number), f"Non-finite JSON number: {value}")
    return number


def parse_json(data: bytes) -> Any:
    return json.loads(data, object_pairs_hook=unique_keys, parse_constant=reject_constant, parse_float=parse_float)


def dataset_rows(data: bytes, expected_ids: set[str], filename: str) -> dict[str, dict[str, Any]]:
    rows = parse_json(data)
    check(isinstance(rows, list) and len(rows) == len(expected_ids),
          f"{filename}: expected exactly {len(expected_ids)} rows")
    result = {}
    for row in rows:
        check(isinstance(row, dict), f"{filename}: expected an object per row")
        row_id = row.get("id")
        check(isinstance(row_id, str) and row_id in expected_ids, f"{filename}: unexpected ID {row_id!r}")
        check(row_id not in result, f"{filename}: duplicate ID {row_id}")
        result[row_id] = row
    return result


def validate_dataset(files: dict[str, bytes]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    docs = dataset_rows(files["corpus.json"], DOCUMENT_IDS, "corpus.json")
    for doc_id, doc in docs.items():
        check(set(doc) == {"id", "title", "text"} and nonempty(doc["title"]) and nonempty(doc["text"]),
              f"{doc_id}: expected nonempty title and text")
    questions = dataset_rows(files["questions.json"], POSITIVE_IDS | TRAP_IDS, "questions.json")
    seen_questions: set[tuple[str, ...]] = set()
    for query_id, row in questions.items():
        question, reference = row.get("question"), row.get("reference_answer")
        relevant, facts = row.get("relevant_ids"), row.get("required_facts")
        check(nonempty(question) and len(question.strip()) <= 1000 and tokens(question),
              f"{query_id}: invalid question")
        key = tuple(tokens(question))
        check(key not in seen_questions, f"{query_id}: duplicate question text")
        seen_questions.add(key)
        check(nonempty(reference), f"{query_id}: missing reference answer")
        check(isinstance(relevant, list) and all(isinstance(doc_id, str) and doc_id in docs for doc_id in relevant),
              f"{query_id}: relevant_ids must list known document IDs")
        check(len(relevant) == len(set(relevant)), f"{query_id}: duplicate relevant ID")
        check(isinstance(facts, list), f"{query_id}: required_facts must be a list of phrase groups")
        if query_id in TRAP_IDS:
            check(not relevant and not facts and reference == REFUSAL,
                  f"{query_id}: a trap needs empty labels and the canonical refusal reference")
            continue
        check(len(relevant) >= K and facts and tokens(reference) != tokens(REFUSAL),
              f"{query_id}: a positive needs at least {K} relevant IDs, facts, and a non-refusal reference")
        clauses = answer_clauses(reference)
        seen_groups: set[frozenset[tuple[str, ...]]] = set()
        for number, group in enumerate(facts, start=1):
            label = f"{query_id}: fact group {number}"
            check(isinstance(group, list) and group and all(nonempty(p) and tokens(p) for p in group),
                  f"{label}: expected nonempty phrase alternatives")
            key_group = frozenset(tuple(tokens(phrase)) for phrase in group)
            check(key_group not in seen_groups, f"{label}: duplicate fact group")
            seen_groups.add(key_group)
            check(match_fact(clauses, group)["passed"], f"{label}: no unambiguous match in the reference")
    return docs, [questions[query_id] for query_id in sorted(questions)]


def validate_response(result: Any, docs: dict[str, dict[str, Any]]) -> None:
    check(isinstance(result, dict), "Expected a JSON object")
    check(nonempty(result.get("answer")), "Expected nonempty answer text")
    check(type(result.get("refused")) is bool, "Expected a boolean refused flag")
    check(nonempty(result.get("model")), "Expected a model identifier")
    for field in ("hits", "sources"):
        entries = result.get(field)
        check(isinstance(entries, list) and len(entries) <= K, f"Expected at most {K} entries in {field}")
        seen = set()
        for entry in entries:
            check(isinstance(entry, dict), f"Expected citation objects in {field}")
            doc_id = entry.get("id")
            check(isinstance(doc_id, str) and doc_id in docs and doc_id not in seen,
                  f"Unknown or duplicate {field} ID: {doc_id!r}")
            seen.add(doc_id)
            check(all(entry.get(key) == docs[doc_id][key] for key in ("title", "text")),
                  f"{field}: {doc_id} differs from the local corpus")
            score = entry.get("score")
            check(type(score) in (int, float) and 0 < score and score <= sys.float_info.max,
                  f"{field}: invalid BM25 score for {doc_id}")
    hits = result["hits"]
    check(all(a["score"] >= b["score"] for a, b in zip(hits, hits[1:])), "Hits are not in descending score order")
    by_id = {hit["id"]: hit for hit in hits}
    check(all(source == by_id.get(source["id"]) for source in result["sources"]),
          "Sources must be a subset of the retrieved hits with the same scores")


def grade(row: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    top_ids = [hit["id"] for hit in result["hits"][:K]]
    relevant = set(row["relevant_ids"])
    hit_ranks = [rank for rank, doc_id in enumerate(top_ids, start=1) if doc_id in relevant]
    inline_ids = list(dict.fromkeys(CITATION.findall(result["answer"])))
    source_ids = [source["id"] for source in result["sources"]]
    matches = inline_ids == source_ids
    expected_evidence = bool(source_ids) and matches and relevant.issuperset(source_ids)
    answer_tokens = tokens(result["answer"])
    refusal_tokens = tokens(REFUSAL)
    non_refusal = not result["refused"] and next(phrase_positions(answer_tokens, refusal_tokens), None) is None
    canonical_refusal = answer_tokens == refusal_tokens
    clauses = answer_clauses(result["answer"])
    facts = [match_fact(clauses, group) for group in row["required_facts"]]
    correct_answer = all(fact["passed"] for fact in facts) and non_refusal and expected_evidence
    correct_refusal = result["refused"] and canonical_refusal and not inline_ids and not source_ids
    return {
        "top_3_ids": top_ids,
        "relevant_hit_ranks": hit_ranks,
        "inline_citation_ids": inline_ids,
        "source_ids": source_ids,
        "citations_match_sources": matches,
        "expected_evidence": expected_evidence,
        "non_refusal": non_refusal,
        "canonical_refusal_text": canonical_refusal,
        "fact_checks": facts,
        "recall_at_3": len(hit_ranks) / len(relevant) if relevant else None,
        "mrr_at_3": (1 / hit_ranks[0] if hit_ranks else 0.0) if relevant else None,
        "accuracy": correct_answer if relevant else None,
        "correct_refusal": correct_refusal if not relevant else None,
    }


def ask(client: httpx.Client, question: dict[str, Any], docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = {"question": question["question"]}
    row = {"id": question["id"], "kind": "positive" if question["relevant_ids"] else "trap",
           "request": payload, "ground_truth": question, "http_status": None,
           "response": None, "metrics": None, "error": None}
    started = perf_counter()
    try:
        response = client.post(ENDPOINT, json=payload)
    except httpx.RequestError as exc:
        row["error"] = {"kind": "network_error", "detail": str(exc), "exception": type(exc).__name__}
        return row
    finally:
        row["request_elapsed_ms"] = (perf_counter() - started) * 1000
    row["http_status"] = response.status_code
    if not response.is_success:
        # The demo translates upstream LLM failure or invalid model output to 502.
        kind = "generation_error" if response.status_code == 502 else "http_error"
        row["error"] = {"kind": kind, "detail": response.text}
        return row
    try:
        result = parse_json(response.content)
        validate_response(result, docs)
    except ValueError as exc:
        row["error"] = {"kind": "invalid_response", "detail": str(exc), "body": response.text}
        return row
    row["response"] = result
    row["metrics"] = grade(question, result)
    return row


def aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    positives = [row["metrics"] for row in rows if row["kind"] == "positive"]
    traps = [row["metrics"] for row in rows if row["kind"] == "trap"]
    return {
        "recall_at_3": mean(row["recall_at_3"] for row in positives),
        "mrr_at_3": mean(row["mrr_at_3"] for row in positives),
        "accuracy": sum(row["accuracy"] for row in positives) / len(positives),
        "refusal_accuracy": sum(row["correct_refusal"] for row in traps) / len(traps),
    }


def write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8012", help="Base URL of the running demo API")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout in seconds (default: %(default)s)")
    parser.add_argument("--output", type=Path, default=DATA / "results", help="Directory for summary.json and per_query.json")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")

    started = perf_counter()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "api": {"base_url": args.base_url, "method": "POST", "path": ENDPOINT, "timeout_s": args.timeout},
        "dataset_sha256": None,
        "dataset_files_sha256": None,
        "dataset_sha256_method": "SHA-256 of sorted compact JSON mapping file names to SHA-256 of original bytes",
        "dataset_sha256_scope": "Local inputs. Returned hit titles and texts are checked against the local corpus.",
        "expected_counts": {"documents": len(DOCUMENT_IDS), "positive": len(POSITIVE_IDS), "trap": len(TRAP_IDS)},
        "status": "failed",
        "model": None,
        "metric_rules": METRIC_RULES,
        "metrics": None,
        "errors": [],
    }
    rows: list[dict[str, Any]] = []
    try:
        files = {name: (DATA / name).read_bytes() for name in ("corpus.json", "questions.json")}
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        summary["dataset_files_sha256"] = hashes
        summary["dataset_sha256"] = hashlib.sha256(
            json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        docs, questions = validate_dataset(files)
    except (OSError, ValueError) as exc:
        summary["errors"].append({"kind": "dataset_error", "detail": str(exc)})
    else:
        summary["document_count"] = len(docs)
        try:
            with httpx.Client(base_url=args.base_url, timeout=args.timeout, trust_env=False) as client:
                for question in questions:
                    row = ask(client, question, docs)
                    rows.append(row)
                    if row["error"]:
                        summary["errors"].append({"id": row["id"], **row["error"]})
                    outcome = row["error"]["kind"] if row["error"] else "answered"
                    print(f"{row['id']}: {outcome}", file=sys.stderr, flush=True)
        except httpx.InvalidURL as exc:
            summary["errors"].append({"kind": "invalid_base_url", "detail": str(exc)})

    answered = [row for row in rows if row["metrics"] is not None]
    models = sorted({row["response"]["model"] for row in answered})
    summary["observed_models"] = models
    if len(models) == 1:
        summary["model"] = models[0]
    elif len(models) > 1:
        summary["errors"].append({"kind": "model_changed", "detail": models})
    summary["counts"] = {
        "attempted": len(rows), "answered": len(answered),
        "answered_by_kind": {kind: sum(row["kind"] == kind for row in answered) for kind in ("positive", "trap")},
        "errors_by_kind": dict(Counter(error["kind"] for error in summary["errors"])),
    }
    if not summary["errors"] and len(answered) == len(POSITIVE_IDS | TRAP_IDS) and len(models) == 1:
        summary["status"] = "complete"
        summary["metrics"] = aggregate(answered)
    summary["elapsed_s"] = perf_counter() - started
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        write_json(args.output / "per_query.json", rows)
        write_json(args.output / "summary.json", summary)
    except (OSError, ValueError) as exc:
        print(f"FAIL: cannot write benchmark artifacts: {exc}", file=sys.stderr)
        return 1
    expected = len(POSITIVE_IDS | TRAP_IDS)
    print(f"{summary['status']}: {len(answered)}/{expected} answered; artifacts: {args.output}")
    if summary["metrics"] is not None:
        print(json.dumps(summary["metrics"]))
        return 0
    for error in summary["errors"]:
        print(f"{error.get('id', 'run')} {error['kind']}: {error['detail']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
