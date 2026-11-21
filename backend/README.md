# Backend AI-стилиста — часть Егора, КТ-2

FastAPI-сервер, который связывает фронтенд, поиск по гардеробу (`rag/`, пакет `wardrobe_rag`) и языковую модель:

```
React SPA ──POST /api/recommend-outfit──▶ FastAPI (backend/)
                                           │ 1. синхронизация гардероба   ─▶ wardrobe_rag.sync
                                           │ 2. кандидаты по слотам       ─▶ wardrobe_rag.retrieve
                                           │ 3. LLM выбирает id и пишет тексты (Qwen / любая OpenAI-совместимая)
                                           │ 4. проверка выбора           ─▶ wardrobe_rag.validate_selection
                                           │ 5. при ошибке — повтор LLM, затем детерминированная сборка
                                           ▼
                              { text, suggestedOutfit, referencedItemIds, source, … }
```

Что гарантирует сервер:

- В образ попадают **только реальные вещи пользователя**: модель возвращает id, полные объекты подставляет сервер, а выбор проверяет пакет поиска (чужие и выдуманные id, две пары обуви, пропущенный обязательный слот, якорная вещь, устаревшая ревизия гардероба).
- **Неполный комплект не выдаётся за образ.** Если нет обуви или при −5 °C нет верхней одежды, приходит текст с объяснением и `missingSlots`, без карточки.
- **Источник ответа виден**: `source` = `llm` (настоящая модель), `mock`, `fallback` (модель недоступна или не прошла проверку — образ собран детерминированно) или `none` (образа нет).
- На корректный запрос сервер не отвечает 500 из-за LLM: сбой модели превращается в `fallback`.

## Запуск

Нужен Python 3.11–3.14 (как у `rag/`). Команды выполняются из каталога `backend/`.

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e ../rag          # поиск: Chroma, sentence-transformers, torch
.venv/bin/python -m uvicorn app.main:app --port 8000
```

**Windows (PowerShell)**

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e ..\rag
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Проверка: <http://localhost:8000/health>, интерактивная документация — <http://localhost:8000/docs>.

```bash
curl -s -X POST http://localhost:8000/api/recommend-outfit \
  -H "Content-Type: application/json" \
  -d '{"query": "Москва: +6°C, ветрено, деловая встреча"}'
```

Запрос с одним `query` работает сразу: при первом старте создаётся пользователь `demo` с базовой капсулой из 10 вещей.

Без `pip install -e ../rag` сервер тоже запустится — на встроенном лексическом поиске `builtin-bm25`. Это запасной режим для разработки фронтенда; он помечается в `/health`, в `meta.retriever` и в `warnings` каждого ответа.

### Модели поиска

Первый запуск с `wardrobe_rag` скачивает около 2,3 ГБ весов. Сделайте это заранее (подробности — в [`rag/README.md`](../rag/README.md)):

```bash
cd ../rag
python -m wardrobe_rag --cache-dir .model_cache --public-root ../public init-models
```

После этого в `backend/.env` можно поставить `RAG_OFFLINE=true` — модели берутся только из кеша. Сервер грузит модели на старте: до первого запроса может пройти несколько десятков секунд, зато сам первый запрос не тормозит.

### Подключение Qwen

Скопируйте `.env.example` в `.env` и раскомментируйте один из блоков:

| Вариант | Настройки | Когда выбирать |
|---|---|---|
| OpenRouter | `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_MODEL=qwen/qwen3.8-27b:free`, `LLM_API_KEY=…` | Быстро и без нагрузки на ноутбук; нужен интернет |
| Ollama | `LLM_PROVIDER=openai`, `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=qwen3:8b`, `LLM_API_KEY=ollama` | Полностью офлайн; на CPU отвечает медленнее |

Клиент один — OpenAI-совместимый `/chat/completions`, поэтому Llama, GPT-4o и другие модели подключаются теми же тремя переменными. Если провайдер не поддерживает `response_format`, поставьте `LLM_JSON_MODE=false`: JSON всё равно требуется промптом, разбирается терпимо (markdown-ограждения, `<think>`-блоки reasoning-моделей) и проверяется.

### Подключение фронтенда

В корне репозитория создайте `.env.local`:

```
VITE_USE_REAL_BACKEND=true
VITE_BACKEND_URL=http://localhost:8000
```

и перезапустите `npm run dev`. Без этого файла фронтенд работает на клиентском симуляторе, как раньше. Если бэкенд включён, но недоступен, фронтенд отвечает симулятором и дописывает об этом в текст ответа.

## API

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/recommend-outfit` | Подобрать образ (контракт КТ-1 + добавочные поля) |
| `POST` | `/api/recommend-outfit/stream` | То же потоком SSE |
| `POST` | `/api/wardrobe/sync` | Заменить гардероб пользователя полным снимком, вернуть `SyncResult` |
| `GET` | `/api/wardrobe?user_id=` | Текущий снимок гардероба на сервере |
| `GET` | `/api/wardrobe/base-capsule` | Базовая капсула бренда |
| `GET` / `PUT` | `/api/admin/settings` | Режим поиска, α, β, температура, персона стилиста |
| `GET` | `/health` | Состояние, LLM и движок поиска |

### Запрос рекомендации

```jsonc
{
  "query": "Подбери образ для деловой встречи",   // обязательно
  "wardrobe": [ /* полные WardrobeItem */ ],       // снимок гардероба: синхронизируется и используется
  "wardrobe_ids": ["item-1", "item-2"],            // или только id — поиск по уже синхронизированному снимку
  "user_id": "user-elena",                         // по умолчанию "demo"
  "context": { "occasion": "business", "weather": "rainy", "vibe": "minimalism" },
  "history": [{ "sender": "user", "text": "…" }],  // последние реплики диалога
  "anchor_item_id": "item-10",                     // образ вокруг вещи (иначе вещь ищется по названию в query)
  "mode": "multimodal", "alpha": 0.65, "visual_weight": 0.35,  // параметры поиска для панели защиты
  "debug": true                                    // вернуть полную диагностику поиска в поле retrieval
}
```

`user_id` — демо-идентификатор из тела запроса, **не защищённая сессия**: авторизации в учебном проекте нет.

### Ответ

```jsonc
{
  "text": "Собрал лаконичный деловой образ…",
  "suggestedOutfit": {                 // отсутствует, если образа нет
    "id": "outfit-3f2a…", "title": "…", "description": "…", "occasion": "…",
    "items": [ /* полные WardrobeItem из гардероба */ ],
    "stylistReasoning": "…", "matchScore": 87, "confidenceTips": ["…"]
  },
  "referencedItemIds": ["item-2", "item-1", "item-4", "item-8"],

  "source": "llm",                     // llm | mock | fallback | none
  "missingSlots": [],                  // чего не хватает для законченного образа
  "warnings": ["…"],                   // диагностика поиска, синхронизации и фолбэков
  "timings": { "syncMs": 12.1, "retrievalMs": 48.0, "llmFirstTextMs": 410.2, "llmMs": 1830.5, "totalMs": 1902.3 },
  "meta": { "llmProvider": "openai", "llmModel": "qwen/…", "llmAttempts": 1, "retriever": "wardrobe_rag",
            "wardrobeRevision": "…", "occasion": "Деловой выход", "matchScoreMethod": "эвристика: …" },
  "retrieval": { /* только при debug=true: RetrievalResult из rag/contracts + поле engine */ }
}
```

`matchScore` нужен карточке образа на фронтенде. Это **не вероятность и не оценка модели**: прозрачная эвристика из полноты обязательных слотов, позиции выбранных вещей в поисковой выдаче, доли вещей с поисковыми свидетельствами и сдержанности палитры. Формула возвращается в `meta.matchScoreMethod`.

### Поток SSE

`POST /api/recommend-outfit/stream` принимает то же тело и отдаёт `text/event-stream`:

| Событие | Данные | Когда |
|---|---|---|
| `status` | `{"stage": "retrieval" \| "generation" \| "validation"}` | Смена этапа |
| `retrieval` | Сводка поиска (при `debug` — полная диагностика) | До первого текста |
| `delta` | `{"text": "фрагмент"}` | Настоящие чанки LLM по мере генерации |
| `result` | Полный ответ, как у обычного эндпоинта | Последним; его `text` заменяет накопленные дельты |
| `error` | `{"message": "…"}` | Если поиск не смог обработать запрос |

Модель генерирует JSON, а пользователю показывается только значение поля `text`: сервер вытаскивает его из потока на лету. `timings.llmFirstTextMs` (первый текст) и `timings.llmMs` (готовый проверенный JSON) измеряются отдельно.

## Как устроен код

```
app/
├── main.py                    # фабрика приложения, CORS, /health
├── config.py                  # настройки из окружения / .env
├── schemas.py                 # контракт API (зеркало src/types/index.ts)
├── api/                       # recommend (JSON + SSE), wardrobe, admin
├── rag/
│   ├── base.py                # порт RagEngine: sync / retrieve / validate_selection / assemble
│   ├── wardrobe_rag_engine.py # адаптер к пакету rag/ (основной режим)
│   ├── builtin_engine.py      # запасной BM25 без моделей
│   └── factory.py             # выбор движка по RAG_ENGINE
├── services/
│   ├── orchestrator.py        # пайплайн: sync → retrieve → LLM → validate → repair → fallback
│   ├── analysis.py            # повод, якорная вещь по названию, погода (для запасного движка)
│   ├── prompts.py             # персона + правила + JSON-формат + сообщения на исправление
│   ├── validation.py          # разбор и проверка формы ответа LLM
│   ├── streaming.py           # извлечение поля "text" из потока JSON
│   ├── scoring.py             # эвристика matchScore
│   └── llm/                   # OpenAI-совместимый клиент, mock, фабрика
└── storage/app_store.py       # SQLite: настройки куратора, снимки для запасного движка
```

Промпт состоит из двух частей. **Персону** («ведущий стилист 12 STOREEZ…») куратор может менять через `PUT /api/admin/settings` (нужен `ADMIN_TOKEN`). **Правила состава и JSON-формат** зашиты в код и из админки не редактируются — иначе правкой текста можно сломать проверку. Запрос клиента и описания вещей передаются как данные; фото (`imageUrl`, в том числе base64) в промпт не попадают.

## Тесты

```bash
.venv/bin/python -m pytest          # Windows: .\.venv\Scripts\python.exe -m pytest
```

119 тестов, сеть и веса моделей не нужны:

- `test_api.py` — HTTP-контракт, исправление и фолбэк LLM, SSE, синхронизация, админка (встроенный движок);
- `test_wardrobe_rag_integration.py` — та же цепочка поверх **настоящих** Chroma, BM25, RRF и `validate_selection` из `rag/`; подменён только кодировщик (детерминированные тестовые векторы, как в `rag/tests`). Пропускается, если `rag/` не установлен;
- `test_openai_client.py` — протокол `/chat/completions` и разбор потока на поддельном HTTP-транспорте;
- `test_builtin_engine.py`, `test_analysis.py`, `test_validation.py`, `test_streaming.py` — модули по отдельности.

Что тестами **не** покрыто и проверяется вручную на машине показа: работа с настоящими весами моделей и ответы настоящей Qwen.

## Чек-лист перед показом

1. `pip install -e ../rag` и `init-models` выполнены; в `.env` — `RAG_ENGINE=wardrobe_rag`, `RAG_OFFLINE=true`.
2. `/health` показывает `"engine": "wardrobe_rag"` и нужную модель LLM.
3. Запрос «Москва: +6°C, ветрено, деловая встреча» с `"debug": true`: в `retrieval` есть вклады каналов, в образе есть верхняя одежда, `source` = `llm`.
4. Гардероб без обуви → `missingSlots: ["shoes"]`, карточки нет.
5. Фронтенд с `VITE_USE_REAL_BACKEND=true` получает ответ сервера (в ответе нет приписки про симулятор).
6. Отключите интернет или остановите Ollama и убедитесь, что приходит `source: "fallback"`, а не ошибка.
