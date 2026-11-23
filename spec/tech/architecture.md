# Архитектура фронтенда и контракт интеграции

## Реализованный backend КТ-2 (22 ноября 2026)

В `backend/` находится FastAPI-сервер — связующее звено между React-приложением, пакетом
поиска `wardrobe_rag` и языковой моделью. Запуск, переменные окружения и полное описание
API: [backend/README.md](../../backend/README.md).

```
React SPA (src/services/stylistApi.ts)
        │  POST /api/recommend-outfit  { query, wardrobe, wardrobe_ids, user_id, context }
        ▼
FastAPI backend/app
  1. sync              — снимок гардероба → wardrobe_rag (Chroma, BM25, эмбеддинги)
  2. retrieve          — кандидаты по слотам, required_slots, missing_slots
  3. LLM               — OpenAI-совместимый клиент (Qwen / Llama / GPT-4o), JSON: id вещей + тексты
  4. validate_selection — проверка выбранных id пакетом поиска
  5. repair / fallback — повтор LLM с причинами отказа, затем детерминированная сборка
        │
        ▼
  { text, suggestedOutfit, referencedItemIds, source, missingSlots, warnings, timings, meta }
```

Ключевые решения:

- **Модель возвращает только id и тексты.** Полные `WardrobeItem` сервер подставляет из
  проверенного результата поиска, поэтому выдуманная вещь не может попасть в ответ.
- **Двойная проверка.** Форма JSON проверяется Pydantic-схемой, состав образа —
  `RAGService.validate_selection` (чужие id, повторы, лимиты слотов, обязательные слоты,
  якорная вещь, изменившаяся ревизия гардероба).
- **Неполный комплект не выдаётся за образ.** При непустом `missing_slots` LLM не вызывается:
  клиент получает текст с объяснением и `missingSlots`, без `suggestedOutfit`.
- **Источник ответа явный.** `source`: `llm` | `mock` | `fallback` | `none`. Сбой LLM не даёт
  HTTP 500, а превращается в `fallback` с предупреждением.
- **Поиск подключён как библиотека**, а не по HTTP: модели и Chroma создаются один раз при
  старте, блокирующие вызовы выполняются в пуле потоков. Если пакет или кеш моделей
  недоступны, включается запасной встроенный BM25 — он помечается в `/health`,
  `meta.retriever` и `warnings`. На показе задаётся `RAG_ENGINE=wardrobe_rag`, и тогда сервер
  без настоящего поиска просто не стартует.
- **`user_id` — демо-идентификатор** из тела запроса (id текущего пользователя фронтенда),
  не защищённая сессия. Авторизации на сервере нет.
- **`matchScore`** — прозрачная эвристика (полнота слотов, позиция в выдаче, поисковые
  свидетельства, палитра), а не вероятность. Формула приходит в `meta.matchScoreMethod`.

## Реализованный модуль поиска КТ-2 (19 ноября 2026)

В `rag/` находится независимый Python-пакет `wardrobe_rag`. Он реализует постоянный
индекс Chroma, BM25, текстовые и визуальные эмбеддинги, RRF, кандидатов по слотам,
проверку выбранных ID и исследовательский runner. FastAPI и LLM остаются следующим
этапом интеграции. Команда `demo` поднимает отдельный локальный инженерный стенд с
настоящим поиском и вкладом каждого канала; генерации LLM в этом стенде нет.

Полный актуальный Python-контракт и пример подключения: [rag/INTEGRATION.md](../../rag/INTEGRATION.md).
JSON Schema экспортируется `python -m wardrobe_rag export-schemas`.
TypeScript-типы `RetrievalResult`/`RetrievalCandidate` отражают диагностический ответ.
У `WardrobeItem` добавлены необязательные `imagePath` и `weather`; текущий UI и seed
продолжают работать без них. Погодные поля — явно размеченные факты, `null` означает
неизвестное свойство. `embeddingSnippet` не заменяет актуальные атрибуты при индексации.

Поиску передаётся серверный `user_id`, полный снимок вещей и запрос. Один и тот же
`item.id` у разных пользователей изолирован. Изменения и удаление синхронизируются
полным снимком; `wardrobe_revision` позволяет отклонить устаревший выбор после LLM.
Результат содержит `candidates_by_slot`, `required_slots`, `missing_slots`,
`timings_ms`, `model_fingerprint`, `alpha`, `visual_weight`, исходные расстояния,
ранги и вклады RRF. Неранжированные резервные кандидаты помечаются `fallback=true`
и исключаются из HitRate/MRR. `score` не является процентом совместимости.

Раздел 3 ниже описывает контракт REST API так, как он реализован в `backend/`. В ответе
`items` содержат полные канонические `WardrobeItem`, а `referencedItemIds` совпадают с
выбранными ID. Сигнатура `askStylist` сохранена. Фронтенд по умолчанию работает на
клиентском симуляторе; настоящий сервер включается переменной `VITE_USE_REAL_BACKEND=true`.

## 1. Архитектурная схема взаимодействия

```
┌────────────────────────────────────────────────────────┐
│                    REACT SPA (ФРОНТЕНД)               │
│                                                        │
│   ┌────────────────────┐      ┌────────────────────┐   │
│   │  WardrobeSidebar   │      │      ChatArea      │   │
│   │ (Каталог одежды)   │      │  (Диалог стилиста) │   │
│   └─────────┬──────────┘      └─────────┬──────────┘   │
│             │                           │              │
│             ▼                           ▼              │
│       [LocalStorage]           [OutfitCard / Modals]   │
│             │                           │              │
│             └───────────┬───────────────┘              │
│                         ▼                              │
│              src/services/stylistApi.ts                │
└─────────────────────────┼──────────────────────────────┘
                          │ HTTP REST POST (JSON)
                          ▼
┌────────────────────────────────────────────────────────┐
│                   BACKEND (RAG & BM25)                 │
│                                                        │
│  ┌───────────────────────┐    ┌─────────────────────┐  │
│  │ FastAPI  backend/     │    │  ChromaDB  (rag/)   │  │
│  └──────────┬────────────┘    │  (Векторная база)   │  │
│             │                 └─────────┬───────────┘  │
│             ▼                           ▼              │
│  [BM25 Поиск по тегам] ────► [Мультимодальный CLIP]   │
│                                         │              │
│                                         ▼              │
│                               [LLM Стилист Генератор]  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Модель данных (Types)

### Элемент гардероба (`WardrobeItem`)
```typescript
interface WardrobeItem {
  id: string;
  title: string;
  category: 'tops' | 'bottoms' | 'outerwear' | 'shoes' | 'accessories';
  color: string;
  season: 'all' | 'spring/summer' | 'autumn/winter';
  style: string[];
  tags: string[];
  imageUrl: string;
  brand?: string;
  material?: string;
  embeddingSnippet?: string;
  uploadedAt: string;
}
```

### Образ аутфита (`OutfitLook`)
```typescript
interface OutfitLook {
  id: string;
  title: string;
  description: string;
  occasion: string;
  items: WardrobeItem[];
  stylistReasoning: string;
  matchScore: number; // e.g. 96
  confidenceTips: string[];
}
```

---

## 3. Контракт REST API (реализован в `backend/`)

### Эндпоинт: `POST /api/recommend-outfit`
**Запрос (Request body):**
```json
{
  "query": "Подбери образ для деловой встречи",
  "wardrobe": [{ "id": "item-1", "title": "Белая хлопковая рубашка оверсайз", "category": "tops", "...": "..." }],
  "wardrobe_ids": ["item-1", "item-2", "item-3", "item-4"],
  "user_id": "user-elena",
  "context": {
    "occasion": "business",
    "weather": "rainy",
    "vibe": "minimalism"
  }
}
```

- `query` — единственное обязательное поле.
- `wardrobe` — полный снимок вещей пользователя (гардероб хранится в `localStorage`, поэтому
  фронтенд присылает его целиком). Сервер синхронизирует снимок с индексом и ищет только по нему.
  Повторная отправка того же снимка не вызывает переиндексацию.
- `wardrobe_ids` без `wardrobe` (исходный контракт КТ-1) — поиск по ранее синхронизированному
  снимку пользователя, ограниченный этими id.
- Необязательные: `history` (реплики диалога), `anchor_item_id` (образ вокруг вещи; если не
  задан, вещь определяется по названию в тексте запроса), `mode`, `alpha`, `visual_weight`,
  `query_image`, `debug` (вернуть полную диагностику поиска).

**Ответ (Response 200 OK):**
```json
{
  "text": "Для деловой встречи я подобрал сбалансированный смарт-кэжуал комплект...",
  "suggestedOutfit": {
    "id": "outfit-3f2a9c41d0b7",
    "title": "Деловой минимализм",
    "description": "Строгий, но комфортный образ со структурированным блейзером",
    "occasion": "Деловая встреча",
    "items": [
      {
        "id": "item-2",
        "title": "Черный структурированный блейзер",
        "category": "outerwear",
        "color": "Черный",
        "season": "all",
        "style": ["business", "smart-casual", "chic"],
        "tags": ["жакет", "блейзер"],
        "imageUrl": "/clothes/blazer.svg",
        "uploadedAt": "2026-10-02"
      }
    ],
    "stylistReasoning": "Контраст черного верха со светлым низом балансирует строгие пропорции.",
    "matchScore": 87,
    "confidenceTips": [
      "Заправьте рубашку в брюки для создания вертикали силуэта."
    ]
  },
  "referencedItemIds": ["item-2", "item-1", "item-4", "item-8"],

  "source": "llm",
  "missingSlots": [],
  "warnings": [],
  "timings": { "syncMs": 12.1, "retrievalMs": 48.0, "llmMs": 1830.5, "totalMs": 1902.3 },
  "meta": {
    "llmProvider": "openai",
    "llmModel": "qwen/qwen3.8-27b:free",
    "llmAttempts": 1,
    "retriever": "wardrobe_rag",
    "wardrobeRevision": "…",
    "occasion": "Деловая встреча",
    "matchScoreMethod": "эвристика: …; не вероятность"
  }
}
```

Поля `text`, `suggestedOutfit`, `referencedItemIds` — исходный контракт КТ-1. Остальные поля
добавочные, клиент может их игнорировать:

| Поле | Значение |
|---|---|
| `source` | `llm` — образ выбрала модель; `mock` — LLM_PROVIDER=mock; `fallback` — модель недоступна или не прошла проверку, образ собран детерминированно; `none` — образа нет |
| `missingSlots` | Категории, которых не хватает для законченного образа. Если список непуст, `suggestedOutfit` отсутствует |
| `warnings` | Диагностика синхронизации, поиска и фолбэков |
| `timings` | Миллисекунды по этапам; в потоке дополнительно `llmFirstTextMs` |
| `meta` | Провайдер и модель LLM, число попыток, движок поиска, ревизия гардероба |
| `retrieval` | Только при `debug: true`: `RetrievalResult` (см. `rag/contracts`) с полем `engine` |

Ошибки: `422` — некорректное тело запроса; `503` — поисковый движок не смог обработать запрос
(например, гардероб изменился во время генерации).

### Эндпоинт: `POST /api/recommend-outfit/stream` (SSE)

То же тело запроса, ответ — `text/event-stream`. Порядок событий: `status` → `retrieval`
(диагностика поиска) → `delta` (настоящие чанки текста LLM) → `status` → `result` (полный
проверенный ответ, как у обычного эндпоинта) либо `error`. Текст из `result` авторитетен и
заменяет накопленные дельты.

В режиме `VITE_USE_REAL_BACKEND=true` чат использует этот эндпоинт. Черновик показывается
только в своём диалоге, не сохраняется в истории и заменяется событием `result`.
При удалении диалога или выходе запрос отменяется; при обрыве потока автономный ответ
явно помечается как локальная симуляция.

### Эндпоинт: `POST /api/wardrobe/sync`

```json
{ "user_id": "user-elena", "items": [ { "id": "item-1", "...": "..." } ] }
```

Полный снимок гардероба: повтор идемпотентен, отсутствующие вещи удаляются из индекса, пустой
массив очищает гардероб только этого пользователя. Ответ — `SyncResult` пакета поиска
(`revision`, `indexed_count`, `image_count`, `added_count`, `updated_count`, `deleted_count`,
`unchanged_count`, `warnings`, `timings_ms`). `GET /api/wardrobe?user_id=…` возвращает текущий снимок.

### Эндпоинты куратора: `GET` / `PUT /api/admin/settings`

Панель куратора получает режим поиска (`mode`), веса (`alpha`, `visualWeight`),
`temperature` и `personaPrompt` с сервера. Модель и движок отображаются без возможности
подмены из браузера. При записи куратор вводит токен, который передаётся в `X-Admin-Token`
и должен совпадать с `ADMIN_TOKEN` сервера. Токен не сохраняется в браузерном хранилище.
