# Измерения retrieval

Запросов: 20; повторов: 3; прогревов на запрос/режим: 1.

| Режим | HitRate@1 | HitRate@3 | MRR@3 | Все слоты @3 | Median, ms | p95, ms |
|---|---:|---:|---:|---:|---:|---:|
| bm25 | 0.8000 | 0.9500 | 0.8667 | 0.8500 | 4.00 | 4.51 |
| dense | 0.7333 | 0.9500 | 0.8389 | 0.9000 | 38.14 | 41.35 |
| hybrid | 0.8333 | 0.9833 | 0.9028 | 0.9500 | 40.25 | 43.19 |

HitRate и MRR показаны как macro-average по категориям. Покомпонентные результаты находятся в summary.json и per_query.csv.

Latency — последовательные вызовы retrieval внутри процесса после прогрева. Индексация, скачивание/загрузка модели, LLM и браузер сюда не входят. first_observed_call_ms в JSON — первый наблюдавшийся вызов, а не гарантированный холодный запуск нового процесса.

Кандидаты fallback=true исключены из рангов HitRate/MRR и релевантного покрытия слотов. Они учитываются отдельно в candidate_slot_coverage_with_fallback: это возможность собрать категории, а не качество поиска.

Повторные измерения не увеличивают число независимых тестовых запросов. На небольшой выборке p95 следует интерпретировать осторожно.

Происхождение корпуса и разметки:

```json
{
  "kind": "synthetic_pilot",
  "annotation_status": "assistant_draft_requires_independent_team_review",
  "created": "2026-11-19",
  "corpus": "wardrobe_eval.json",
  "corpus_items": 60,
  "source_seed": "wardrobe_seed.json (10 frontend items unchanged)",
  "synthetic_extra_items": 50,
  "images": "Existing category SVG surrogates; text-only benchmark, not photographic evidence.",
  "label_policy": "Declared from descriptions before observing rankings. Several compatible IDs per required slot.",
  "alpha_policy": "Predeclared 0.65. Test labels must not be used to choose alpha.",
  "independence": "Draft scenarios are not an independently annotated external benchmark."
}
```

Если annotation_status указывает draft/requires_review, метрики предварительные до независимой проверки ground truth командой. SVG и их преобразования не подтверждают качество поиска по новым фотографиям одежды.

Конфигурация и оборудование:

```json
{
  "runtime": {
    "python": "3.14.3",
    "system": "Windows-10-10.0.19045-SP0"
  },
  "metadata": {
    "initialization_and_sync_ms": 14543.18069999863,
    "sync": {
      "user_id": "research",
      "revision": "b6fa92f0c16a7d796bc23146ee68d85305f49b24c20d18ba5bc024823bed52f6",
      "indexed_count": 60,
      "image_count": 60,
      "added_count": 60,
      "updated_count": 0,
      "deleted_count": 0,
      "unchanged_count": 0,
      "warnings": [],
      "timings_ms": {
        "prepare_ms": 10499.795700001414,
        "text_embedding_ms": 1829.774699999689,
        "image_embedding_ms": 1475.755500003288,
        "persist_ms": 104.10240000055637,
        "total_ms": 13909.461700000975
      }
    },
    "models": {
      "models": {
        "text": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "image": "sentence-transformers/clip-ViT-B-32",
        "visual_text": "sentence-transformers/clip-ViT-B-32-multilingual-v1"
      },
      "revisions": {
        "text": "4328cf26390c98c5e3c738b4460a05b95f4911f5",
        "image": "327ab6726d33c0e22f920c83f2ff9e4bd38ca37f",
        "visual_text": "58edf8cada9e398793dca955574a48cbb7f18be2"
      },
      "device": "cpu",
      "offline": true
    },
    "model_fingerprint": "3dd91d47be2542103e17e84332216e8869bfd003b55dcba16c8186264cb34f50",
    "python": "3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]",
    "platform": "Windows-10-10.0.19045-SP0",
    "corpus_file": "wardrobe_eval.json",
    "cpu": "Intel64 Family 6 Model 154 Stepping 3, GenuineIntel",
    "logical_cpus": 20,
    "omp_threads": "4",
    "mkl_threads": "4",
    "packages": {
      "wardrobe-rag": "0.1.0",
      "chromadb": "1.5.9",
      "rank-bm25": "0.2.2",
      "sentence-transformers": "5.7.0",
      "transformers": "5.23.0",
      "torch": "2.15.0",
      "torchvision": "0.29.2",
      "resvg-py": "0.5.0"
    },
    "corpus_revision": "b6fa92f0c16a7d796bc23146ee68d85305f49b24c20d18ba5bc024823bed52f6"
  },
  "dataset_sha256": "d31ab589969e2f73d0773303f288af5a0113dbc01578227c46c6849c4ff798d7",
  "corpus_sha256": "520acb80362fb5c4acdc36f0a18ae795c096f7b84e9c1e86cdcd33415929bbae"
}
```
