# Измерения retrieval

Запросов: 10; повторов: 3; прогревов на запрос/режим: 1.

| Режим | HitRate@1 | HitRate@3 | MRR@3 | Все слоты @3 | Median, ms | p95, ms |
|---|---:|---:|---:|---:|---:|---:|
| visual | 0.8000 | 1.0000 | 0.9000 | 1.0000 | 18.51 | 21.90 |

HitRate и MRR показаны как macro-average по категориям. Покомпонентные результаты находятся в summary.json и per_query.csv.

Latency — последовательные вызовы retrieval внутри процесса после прогрева. Индексация, скачивание/загрузка модели, LLM и браузер сюда не входят. first_observed_call_ms в JSON — первый наблюдавшийся вызов, а не гарантированный холодный запуск нового процесса.

Кандидаты fallback=true исключены из рангов HitRate/MRR и релевантного покрытия слотов. Они учитываются отдельно в candidate_slot_coverage_with_fallback: это возможность собрать категории, а не качество поиска.

Повторные измерения не увеличивают число независимых тестовых запросов. На небольшой выборке p95 следует интерпретировать осторожно.

Происхождение корпуса и разметки:

```json
{
  "kind": "illustration_smoke",
  "annotation_status": "assistant_draft_requires_independent_team_review",
  "images": "10 supplied SVG illustrations, some contain printed labels; not a clothing photo benchmark.",
  "limitations": "Text-to-image category ranks have only 2 candidates. Use a global image collection if reporting nontrivial image retrieval."
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
    "initialization_and_sync_ms": 9352.933800000756,
    "sync": {
      "user_id": "research",
      "revision": "0b0107c6d0e8474c15b7956350c21e023646fcc56f3c846bf696e3547282858d",
      "indexed_count": 10,
      "image_count": 10,
      "added_count": 10,
      "updated_count": 0,
      "deleted_count": 0,
      "unchanged_count": 0,
      "warnings": [],
      "timings_ms": {
        "prepare_ms": 8058.18889999864,
        "text_embedding_ms": 337.60269999766024,
        "image_embedding_ms": 243.1536000003689,
        "persist_ms": 76.39730000300915,
        "total_ms": 8715.37570000146
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
  "dataset_sha256": "a387f1d68cb2198f1fd02378064bedfbae5dffc9f097e4d457cdc1802925a7df",
  "corpus_sha256": "b6ddf99384d098f264f7e0de9b691e3ecfedac9bc552b910225ed639f9d62c2c"
}
```
