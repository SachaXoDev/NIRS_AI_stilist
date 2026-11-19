# Измерения retrieval

Запросов: 10; повторов: 3; прогревов на запрос/режим: 1.

| Режим | HitRate@1 | HitRate@3 | MRR@3 | Все слоты @3 | Median, ms | p95, ms |
|---|---:|---:|---:|---:|---:|---:|
| visual | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 49.38 | 50.80 |

HitRate и MRR показаны как macro-average по категориям. Покомпонентные результаты находятся в summary.json и per_query.csv.

Latency — последовательные вызовы retrieval внутри процесса после прогрева. Индексация, скачивание/загрузка модели, LLM и браузер сюда не входят. first_observed_call_ms в JSON — первый наблюдавшийся вызов, а не гарантированный холодный запуск нового процесса.

Кандидаты fallback=true исключены из рангов HitRate/MRR и релевантного покрытия слотов. Они учитываются отдельно в candidate_slot_coverage_with_fallback: это возможность собрать категории, а не качество поиска.

Повторные измерения не увеличивают число независимых тестовых запросов. На небольшой выборке p95 следует интерпретировать осторожно.

Происхождение корпуса и разметки:

```json
{
  "kind": "near_duplicate_instance_smoke",
  "annotation_status": "identity_labels",
  "images": "Transformed rasterizations of original SVGs, prepared by the image pipeline.",
  "limitations": "Same source item exists in the index; measures instance robustness, not unseen-photo semantic generalization."
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
    "initialization_and_sync_ms": 8683.889200001431,
    "sync": {
      "user_id": "research",
      "revision": "0b0107c6d0e8474c15b7956350c21e023646fcc56f3c846bf696e3547282858d",
      "indexed_count": 10,
      "image_count": 10,
      "added_count": 0,
      "updated_count": 0,
      "deleted_count": 0,
      "unchanged_count": 10,
      "warnings": [],
      "timings_ms": {
        "prepare_ms": 8041.679400001158,
        "total_ms": 8041.860799999995
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
    "corpus_file": "wardrobe_seed.json",
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
    "corpus_revision": "0b0107c6d0e8474c15b7956350c21e023646fcc56f3c846bf696e3547282858d"
  },
  "dataset_sha256": "5dc2fb5582fb7d6af9f6964183e147338d2eaec30a458e1106a4de9cf8177198",
  "corpus_sha256": "b6ddf99384d098f264f7e0de9b691e3ecfedac9bc552b910225ed639f9d62c2c"
}
```
