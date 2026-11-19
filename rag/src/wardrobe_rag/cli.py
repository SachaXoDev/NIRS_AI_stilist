"""Executable engineering demo and evaluation, independent of FastAPI and LLM."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from .embedding import SentenceTransformerEmbedder
from .images import ImageLoader
from .indexing import IndexingPipeline
from .schemas import RetrievalRequest, WardrobeItem
from .store import ChromaWardrobeStore


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _runtime(args):
    from .retrieval import RetrievalEngine
    from .service import RAGService
    loader = ImageLoader(Path(args.public_root), Path(args.upload_root) if args.upload_root else None)
    embedder = SentenceTransformerEmbedder(cache_dir=Path(args.cache_dir), device=args.device, offline=args.offline)
    store = ChromaWardrobeStore(Path(args.data_dir))
    indexer = IndexingPipeline(store, embedder, loader)
    return RAGService(indexer, RetrievalEngine(store, embedder, loader)), embedder, store


def parser():
    result = argparse.ArgumentParser(description="Real multilingual text/image wardrobe RAG (Matvey KT-2)")
    result.add_argument("--data-dir", default=".rag_data")
    result.add_argument("--public-root", default="../public")
    result.add_argument("--upload-root")
    result.add_argument("--cache-dir", default=".model_cache")
    result.add_argument("--offline", action="store_true", help="Require models already downloaded to cache")
    result.add_argument("--device", default="cpu")
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("init-models", help="Download/load all real encoders before offline demonstration")
    index = sub.add_parser("index", help="Replace one user's full wardrobe snapshot")
    index.add_argument("--input", required=True)
    index.add_argument("--user", required=True)
    search = sub.add_parser("search")
    search.add_argument("--user", required=True)
    search.add_argument("--query", default="")
    search.add_argument("--image")
    search.add_argument("--mode", choices=["bm25", "dense", "hybrid", "visual", "multimodal"], default="hybrid")
    search.add_argument("--alpha", type=float, default=.65)
    search.add_argument("--visual-weight", type=float, default=.35)
    search.add_argument("--temperature", type=float)
    search.add_argument("--rain", action="store_true", default=None)
    search.add_argument("--wind", action="store_true", default=None)
    search.add_argument("--anchor")
    search.add_argument("--output")
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--dataset", default="data/queries_test.json")
    evaluate.add_argument("--corpus", help="Override corpus declared by the dataset manifest")
    evaluate.add_argument("--user", default="research")
    evaluate.add_argument("--output", default="results/text")
    evaluate.add_argument("--modes", nargs="+", default=["bm25", "dense", "hybrid"])
    evaluate.add_argument("--repeats", type=int, default=3)
    evaluate.add_argument("--warmup", type=int, default=1)
    prep = sub.add_parser("prepare-visual-queries", help="Make disclosed transformed-SVG query fixtures")
    prep.add_argument("--output", default="data/visual_queries")
    prep.add_argument("--corpus", default="data/wardrobe_seed.json")
    demo = sub.add_parser("demo", help="Local engineering UI, real retrieval and visual search; no LLM")
    demo.add_argument("--input", default="data/wardrobe_demo_weather.json")
    demo.add_argument("--user", default="demo")
    demo.add_argument("--host", default="127.0.0.1")
    demo.add_argument("--port", type=int, default=8765)
    schemas = sub.add_parser("export-schemas", help="Export Pydantic JSON contracts for backend integration")
    schemas.add_argument("--output", default="contracts")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        started = perf_counter()
        if args.command == "export-schemas":
            from .schemas import RetrievalResult, SelectionValidation, SyncResult, QueryContext
            destination = Path(args.output)
            destination.mkdir(parents=True, exist_ok=True)
            for model in (WardrobeItem, RetrievalRequest, RetrievalResult, SelectionValidation, SyncResult, QueryContext):
                (destination / f"{model.__name__}.schema.json").write_text(
                    json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(destination), "schemas": 6}))
            return 0
        if args.command == "prepare-visual-queries":
            from PIL import Image, ImageEnhance
            loader = ImageLoader(Path(args.public_root))
            destination = Path(args.output)
            destination.mkdir(parents=True, exist_ok=True)
            manifest = []
            for raw in _json(args.corpus):
                item = WardrobeItem.model_validate(raw)
                image = loader(item.imageUrl)
                # Near-duplicate instance retrieval only; these are not real photographs.
                small = image.resize((320, 400))
                canvas = Image.new("RGB", (360, 440), "#f4f1eb")
                canvas.paste(ImageEnhance.Contrast(small).enhance(.93), (20, 20))
                filename = f"{item.id}.png"
                canvas.save(destination / filename)
                manifest.append({"item_id": item.id, "query_image": filename, "source": item.imageUrl})
            (destination / "provenance.json").write_text(json.dumps({"kind": "transformed SVG instance queries; not photos", "items": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"prepared": len(manifest), "output": str(destination)}, ensure_ascii=False))
            return 0
        if args.command == "init-models":
            embedder = SentenceTransformerEmbedder(cache_dir=Path(args.cache_dir), device=args.device, offline=args.offline)
            print(json.dumps({"provenance": embedder.prepare(), "fingerprint": embedder.fingerprint,
                              "model_load_ms": (perf_counter() - started) * 1000}, ensure_ascii=False, indent=2))
            return 0
        service, embedder, store = _runtime(args)
        if args.command == "demo":
            from .demo import serve_demo
            service.sync(args.user, _json(args.input))
            serve_demo(service, args.user, host=args.host, port=args.port)
            return 0
        if args.command == "index":
            raw = _json(args.input)
            items = raw["items"] if isinstance(raw, dict) else raw
            response = service.sync(args.user, items)
        elif args.command == "search":
            context = {"temperature_c": args.temperature, "rain": args.rain, "wind": args.wind}
            request = RetrievalRequest(user_id=args.user, query=args.query, query_image=args.image,
                                       mode=args.mode, alpha=args.alpha, visual_weight=args.visual_weight,
                                       anchor_item_id=args.anchor, context=context)
            response = service.retrieve(request)
        else:
            from .evaluation import evaluate, load_corpus, load_dataset, validate_dataset
            dataset = load_dataset(args.dataset)
            dataset["user_id"] = args.user
            corpus_path = Path(args.corpus).resolve() if args.corpus else Path(dataset["_corpus_path"])
            dataset["_corpus_path"] = str(corpus_path)
            items = load_corpus(corpus_path)
            validate_dataset(dataset, items)
            sync = service.sync(args.user, items)
            metadata = {"initialization_and_sync_ms": (perf_counter() - started) * 1000,
                        "sync": sync.model_dump(mode="json"), "models": embedder.provenance,
                        "model_fingerprint": embedder.fingerprint, "python": sys.version,
                        "platform": platform.platform(), "corpus_file": corpus_path.name,
                        "cpu": os.environ.get("PROCESSOR_IDENTIFIER") or platform.processor() or platform.machine(),
                        "logical_cpus": os.cpu_count(),
                        "omp_threads": os.environ.get("OMP_NUM_THREADS"),
                        "mkl_threads": os.environ.get("MKL_NUM_THREADS"),
                        "packages": {name: version(name) for name in
                                     ("wardrobe-rag", "chromadb", "rank-bm25", "sentence-transformers",
                                      "transformers", "torch", "torchvision", "resvg-py")},
                        "corpus_revision": store.get_revision(args.user)}
            def retrieve(raw):
                return service.retrieve(RetrievalRequest.model_validate(raw))
            summary = evaluate(retrieve, dataset, Path(args.output), modes=tuple(args.modes),
                               repeats=args.repeats, warmup=args.warmup, metadata=metadata)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        output = response.model_dump_json(indent=2)
        if args.command == "search" and args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(output, encoding="utf-8")
        print(output)
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
