from __future__ import annotations

import json

import pytest

from wardrobe_rag.evaluation import evaluate, retrieval_metrics, validate_dataset


def test_metrics_use_first_relevant_rank_and_respect_cutoff():
    values = retrieval_metrics(["wrong", "a", "b"], {"a", "b"})
    assert values == {"hit_rate@1": 0.0, "hit_rate@3": 1.0, "mrr@3": 0.5}
    assert retrieval_metrics(["x", "y", "z", "a"], {"a"})["mrr@3"] == 0
    assert retrieval_metrics([], {"a"}) == {"hit_rate@1": 0.0, "hit_rate@3": 0.0, "mrr@3": 0.0}


def test_invalid_labels_duplicate_ranking_and_cutoffs_are_rejected():
    with pytest.raises(ValueError):
        retrieval_metrics(["a"], set())
    with pytest.raises(ValueError):
        retrieval_metrics(["a", "a"], {"a"})
    with pytest.raises(ValueError):
        retrieval_metrics(["a"], {"a"}, ks=(0,))


def dataset():
    return {
        "schema_version": 1,
        "user_id": "test-user",
        "required_slots": ["tops", "bottoms", "shoes"],
        "queries": [{"id": "q1", "query": "день", "relevant_by_slot": {"tops": ["top"], "bottoms": ["bottom"], "shoes": ["shoe"]}}],
    }


def test_fallback_fills_categories_but_cannot_inflate_retrieval_metrics(tmp_path):
    def retrieve(request):
        return {
            "candidates_by_slot": {
                slot: [{"item": {"id": identifier}, "score": 0, "fallback": True}]
                for slot, identifier in (("tops", "top"), ("bottoms", "bottom"), ("shoes", "shoe"))
            },
            "timings_ms": {"bm25": 0.1},
        }

    summary = evaluate(retrieve, dataset(), tmp_path, modes=("bm25",), repeats=2, warmup=0)
    mode = summary["modes"]["bm25"]
    assert mode["metrics"]["hit_rate@3"] == 0
    assert mode["metrics"]["mrr@3"] == 0
    assert mode["candidate_slot_coverage_with_fallback"] == 1
    assert mode["full_slot_coverage"]["@3"] == 0
    assert mode["query_slot_pairs"] == 3
    assert mode["retrieval_calls"] == 2
    assert mode["latency_ms"]["samples"] == 2
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["query_count"] == 1
    assert (tmp_path / "per_query.csv").is_file()
    assert len((tmp_path / "raw_rankings.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_ground_truth_cannot_reference_wrong_category():
    corpus = [{"id": "top", "category": "shoes"}, {"id": "bottom", "category": "bottoms"}, {"id": "shoe", "category": "shoes"}]
    with pytest.raises(ValueError, match="another category"):
        validate_dataset(dataset(), corpus)
