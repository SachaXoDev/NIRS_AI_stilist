# Измерения retrieval

Запросов: 4; повторов: 1; прогревов на запрос/режим: 0.

| Режим | HitRate@1 | HitRate@3 | MRR@3 | Все слоты @3 | Median, ms | p95, ms |
|---|---:|---:|---:|---:|---:|---:|
| visual | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 420.57 | 1653.64 |

HitRate и MRR показаны как macro-average по категориям. Покомпонентные результаты находятся в summary.json и per_query.csv.

Latency — последовательные вызовы retrieval внутри процесса после прогрева. Индексация, скачивание/загрузка модели, LLM и браузер сюда не входят. first_observed_call_ms в JSON — первый наблюдавшийся вызов, а не гарантированный холодный запуск нового процесса.

Кандидаты fallback=true исключены из рангов HitRate/MRR и релевантного покрытия слотов. Они учитываются отдельно в candidate_slot_coverage_with_fallback: это возможность собрать категории, а не качество поиска.

Повторные измерения не увеличивают число независимых тестовых запросов. На небольшой выборке p95 следует интерпретировать осторожно.

Происхождение корпуса и разметки:

```json
{
  "kind": "separate_real_photos_same_instance",
  "annotation_status": "identity_labels_from_museum_accessions",
  "images": "provenance.json",
  "limitations": "Four historical museum coats in one slot. This measures cross-view instance matching, not semantic generalization, street-photo robustness, or outfit quality. Query and index are separate photographs but can share a studio setup and photographer. Interpret Hit@1 and per-query ranks; the default retriever returns only two outerwear candidates, so Hit@3 effectively measures Hit@2 and MRR@3 only sees those two ranks."
}
```

Если annotation_status указывает draft/requires_review, метрики предварительные до независимой проверки ground truth командой. SVG и их преобразования не подтверждают качество поиска по новым фотографиям одежды.

Конфигурация и оборудование:

```json
{
  "runtime": {
    "python": "3.12.0",
    "system": "macOS-15.3.2-arm64-arm-64bit"
  },
  "metadata": {
    "initialization_and_sync_ms": 32402.76049997192,
    "sync": {
      "user_id": "photo-pilot",
      "revision": "7b34ef4f07f4081fb31c8d6a5c55ebb5d9d51185888d7ab6aa6adc90c85422a9",
      "indexed_count": 4,
      "image_count": 4,
      "added_count": 4,
      "updated_count": 0,
      "deleted_count": 0,
      "unchanged_count": 0,
      "warnings": [],
      "timings_ms": {
        "prepare_ms": 24717.88683399791,
        "text_embedding_ms": 3499.4734170031734,
        "image_embedding_ms": 2573.067124991212,
        "persist_ms": 131.1989160021767,
        "total_ms": 30922.29216702981
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
    "python": "3.12.0 (v3.12.0:0fb18b02c8, Oct  2 2023, 09:45:56) [Clang 13.0.0 (clang-1300.0.29.30)]",
    "platform": "macOS-15.3.2-arm64-arm-64bit",
    "corpus_file": "corpus.json",
    "cpu": "arm",
    "logical_cpus": 8,
    "omp_threads": "2",
    "mkl_threads": null,
    "packages": {
      "wardrobe-rag": "0.1.0",
      "chromadb": "1.5.9",
      "rank-bm25": "0.2.2",
      "sentence-transformers": "5.7.0",
      "transformers": "5.24.0",
      "torch": "2.15.0",
      "torchvision": "0.29.2",
      "resvg-py": "0.5.0"
    },
    "corpus_revision": "7b34ef4f07f4081fb31c8d6a5c55ebb5d9d51185888d7ab6aa6adc90c85422a9"
  },
  "dataset_sha256": "4ff02cf6b8cf737731f35cb8923d266a3c34f3909e3de268b6df312cafed2503",
  "corpus_sha256": "1428822e8c1d13e72e76b08dcab46c4cf48b2f82b1764da72e32844c23d4a4fb"
}
```
