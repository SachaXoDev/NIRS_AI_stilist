"""Run the three slot-search acceptance examples against Chroma and real encoders."""
import argparse
import json
import tempfile
from pathlib import Path

from wardrobe_rag import RAGService, RetrievalEngine
from wardrobe_rag.embedding import SentenceTransformerEmbedder
from wardrobe_rag.images import ImageLoader
from wardrobe_rag.indexing import IndexingPipeline
from wardrobe_rag.store import ChromaWardrobeStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    home = Path(__file__).resolve().parents[1]
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=home / ".model_cache")
    args = parser.parse_args()

    def load(name):
        return json.loads((home / "data" / name).read_text(encoding="utf-8"))

    items = {item["id"]: item for name in ("wardrobe_seed.json", "wardrobe_capsule_extra.json") for item in load(name)}
    results = []
    loader = ImageLoader(home.parent / "public")
    embedder = SentenceTransformerEmbedder(cache_dir=args.cache_dir, offline=True, device="cpu")
    with tempfile.TemporaryDirectory(prefix="slot-demo-", ignore_cleanup_errors=True) as temporary:
        store = ChromaWardrobeStore(Path(temporary))
        service = RAGService(IndexingPipeline(store, embedder, loader), RetrievalEngine(store, embedder, loader))
        for case in load("slot_search_examples.json"):
            request = case["request"]
            service.sync(request["user_id"], [items[item_id] for item_id in case["wardrobe_ids"]])
            result = service.retrieve_slot(request)
            ids = [candidate.item_id for candidate in result.candidates]
            assert ids == case["expected_ids"], (case["name"], ids)
            assert result.kept_item_ids == case["kept_ids"] and result.replaced_item_id == case["expected_replaced_id"]
            assert all(candidate.item.category == request["slot"] and not candidate.fallback for candidate in result.candidates)
            if case["name"] == "add_rain_layer":
                assert result.context.rain is True
            results.append({"case": case["name"], "request": request, "result": result.model_dump(mode="json")})
            print(f"{case['name']}: {ids}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
