# Измерения retrieval

Запросов: 12; повторов: 1; прогревов на запрос/режим: 1.

| Режим | HitRate@1 | HitRate@3 | MRR@12 | Все слоты @3 | Median, ms | p95, ms |
|---|---:|---:|---:|---:|---:|---:|
| visual | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 76.44 | 82.46 |

HitRate и MRR показаны как macro-average по категориям. Покомпонентные результаты находятся в summary.json и per_query.csv.

Latency — последовательные вызовы retrieval внутри процесса после прогрева. Индексация, скачивание/загрузка модели, LLM и браузер сюда не входят. first_observed_call_ms в JSON — первый наблюдавшийся вызов, а не гарантированный холодный запуск нового процесса.

Кандидаты fallback=true исключены из рангов HitRate/MRR и релевантного покрытия слотов. Они учитываются отдельно в candidate_slot_coverage_with_fallback: это возможность собрать категории, а не качество поиска.

Повторные измерения не увеличивают число независимых тестовых запросов. На небольшой выборке p95 следует интерпретировать осторожно.

Происхождение корпуса и разметки:

```json
{
  "kind": "separate_real_photos_same_instance",
  "annotation_status": "identity_labels_from_met_object_ids",
  "images": "provenance.json",
  "limitations": "Twelve 19th-century museum coats in one slot. Catalogue front views and query back views are independent exposures. Lighting and backdrop often match within a pair. This is not an estimate of accuracy on modern wardrobes or street photography."
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
    "sync": {
      "user_id": "expanded-museum-pilot",
      "revision": "b3fef5813e620028659e14f8dc2d4ed78e57d9c38c5db75ba22d6e9ed4eb4654",
      "indexed_count": 12,
      "image_count": 12,
      "added_count": 12,
      "updated_count": 0,
      "deleted_count": 0,
      "unchanged_count": 0,
      "warnings": [],
      "timings_ms": {
        "prepare_ms": 14302.844299993012,
        "text_embedding_ms": 294.1176999884192,
        "image_embedding_ms": 642.2440000023926,
        "persist_ms": 140.14810000662692,
        "total_ms": 15379.449100000784
      }
    },
    "init_and_index_ms": 15380.413499995484,
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
    "candidate_depth": 12,
    "platform": "Windows-10-10.0.19045-SP0",
    "versions": {
      "chromadb": "1.5.9",
      "sentence-transformers": "5.7.0",
      "transformers": "5.23.0",
      "torch": "2.15.0"
    }
  },
  "dataset_sha256": "d6716b475fa5b9a185181c9a4cacf71ee966841dc293dd41262365699260a8bc",
  "corpus_sha256": "0931baa1b8be624930e98c02b34bd1b0924ba8259966f0c9135cad5c9d2e2869"
}
```
