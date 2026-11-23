"""Measure full image-to-image ranks on the expanded CC0 front/back photo pilot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from wardrobe_rag import RAGConfig, RAGService, RetrievalEngine
from wardrobe_rag.embedding import SentenceTransformerEmbedder
from wardrobe_rag.evaluation import evaluate, load_corpus, load_dataset
from wardrobe_rag.images import ImageLoader
from wardrobe_rag.indexing import IndexingPipeline
from wardrobe_rag.store import ChromaWardrobeStore


RAG_DIR = Path(__file__).resolve().parents[1]
PILOT = RAG_DIR / "data/photo_pilot_expanded"


def verify_pairs(dataset, items, manifest):
    indexed = {item["id"]: item for item in items}
    queries = {entry["query_image"]: entry for entry in dataset["queries"]}
    paired_ids = {pair["id"] for pair in manifest["pairs"]}
    if len(paired_ids) != len(manifest["pairs"]) or paired_ids != indexed.keys() or len(queries) != len(items):
        raise ValueError("Expected one distinct catalogue/query photo pair per indexed item")
    seen_hashes = set()
    for pair in manifest["pairs"]:
        item = indexed[pair["id"]]
        front, back = pair["index_photo"], pair["query_photo"]
        entry = queries[back["file"]]
        if (item["category"] != "outerwear" or item["imageUrl"] != "/" + front["file"]
                or entry.get("query") != "" or entry["relevant_by_slot"] != {"outerwear": [item["id"]]}
                or front["source_url"] == back["source_url"] or front["source_sha256"] == back["source_sha256"]):
            raise ValueError(f"Invalid image-only pair {pair['id']}")
        for photo in (front, back):
            path = (PILOT / photo["file"]).resolve()
            if not path.is_relative_to(PILOT) or not path.is_file():
                raise ValueError(f"Missing or invalid photo: {photo['file']}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != photo["sha256"] or digest in seen_hashes:
                raise ValueError(f"Photo mismatch or duplicate: {photo['file']}")
            seen_hashes.add(digest)


def write_full_ranks(output, dataset, corpus_size):
    relevant = {entry["id"]: entry["relevant_by_slot"]["outerwear"][0] for entry in dataset["queries"]}
    rows = []
    for line in (output / "raw_rankings.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["request"]["query"] or row["request"]["mode"] != "visual":
            raise ValueError("The run must be image-only visual retrieval")
        ranked = row["result"]["candidates_by_slot"]["outerwear"]
        if len(ranked) != corpus_size or any(candidate["fallback"] or candidate["visual_distance"] is None for candidate in ranked):
            raise ValueError("Visual retrieval did not rank every indexed photograph")
        ids = [candidate["item"]["id"] for candidate in ranked]
        expected = relevant[row["query_id"]]
        rank = ids.index(expected) + 1
        true_distance = ranked[rank - 1]["visual_distance"]
        first_distance = ranked[0]["visual_distance"]
        rows.append(dict(query_id=row["query_id"], expected_id=expected, rank=rank, first_id=ids[0],
                         expected_distance=f"{true_distance:.6f}", first_distance=f"{first_distance:.6f}",
                         distance_gap=f"{true_distance-first_distance:.6f}",
                         ranked_ids=" | ".join(ids),
                         ranked_cosine_distances=" | ".join(f"{c['visual_distance']:.6f}" for c in ranked)))
    with (output / "ranks.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RAG_DIR / "results/photo_pilot_expanded")
    parser.add_argument("--cache-dir", type=Path, default=RAG_DIR / ".model_cache")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Choose an empty output directory to preserve prior measurements")
    dataset = load_dataset(PILOT / "queries.json")
    items = load_corpus(PILOT / "corpus.json")
    rights = json.loads((PILOT / "provenance.json").read_text(encoding="utf-8"))
    verify_pairs(dataset, items, rights)
    output.mkdir(parents=True, exist_ok=True)
    loader = ImageLoader(PILOT, PILOT)
    embedder = SentenceTransformerEmbedder(cache_dir=args.cache_dir, offline=True, device=args.device)
    store = ChromaWardrobeStore(output / "index")
    default_config = RAGConfig()
    config = RAGConfig(top_k={**default_config.top_k, "outerwear": len(items)},
                       candidate_pool=max(len(items), default_config.candidate_pool))
    service = RAGService(IndexingPipeline(store, embedder, loader), RetrievalEngine(store, embedder, loader, config))
    started = perf_counter()
    sync = service.sync(dataset["user_id"], items)
    if sync.image_count != len(items):
        raise RuntimeError(f"Some catalogue photos were not indexed: {sync.warnings}")
    metadata = {
        "sync": sync.model_dump(mode="json"), "init_and_index_ms": (perf_counter() - started) * 1000,
        "models": embedder.provenance, "model_fingerprint": embedder.fingerprint,
        "candidate_depth": len(items), "platform": platform.platform(),
        "versions": {name: version(name) for name in ("chromadb", "sentence-transformers", "transformers", "torch")},
    }
    summary = evaluate(service.retrieve, dataset, output, modes=("visual",), repeats=1, warmup=1, metadata=metadata)
    rows = write_full_ranks(output, dataset, len(items))
    hits = sum(row["rank"] == 1 for row in rows)
    assert abs(summary["modes"]["visual"]["metrics"]["hit_rate@1"] - hits / len(rows)) < 1e-9
    print(f"HitRate@1: {hits}/{len(rows)} = {hits/len(rows):.1%}")
    print(f"Full ranks: {output / 'ranks.csv'}")


if __name__ == "__main__":
    main()
