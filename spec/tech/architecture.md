# Архитектура фронтенда и контракт интеграции

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

Приведённые ниже REST-эндпоинт и пример ответа — исходный проектный контракт КТ-1,
а не работающий сервер. Для будущего LLM ответа `items` должны содержать полные
канонические `WardrobeItem`, а `referencedItemIds` должны совпадать с выбранными ID.
Сигнатура `askStylist` сохранена. Текущий frontend ещё использует mock до подключения
реального backend и синхронизации.

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
│  │ FastApi /api/recommend│    │  ChromaDB / Qdrant  │  │
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

## 3. Контракт REST API для интеграции с бэкендом

### Эндпоинт: `POST /api/recommend-outfit`
**Запрос (Request body):**
```json
{
  "query": "Подбери образ для деловой встречи",
  "wardrobe_ids": ["item-1", "item-2", "item-3", "item-4"],
  "context": {
    "occasion": "business",
    "weather": "rainy",
    "vibe": "minimalism"
  }
}
```

**Ответ (Response 200 OK):**
```json
{
  "text": "Для деловой встречи я подобрал сбалансированный смарт-кэжуал комплект...",
  "suggestedOutfit": {
    "id": "outfit-101",
    "title": "Деловой минимализм",
    "description": "Строгий, но комфортный образ со структурированным блейзером",
    "occasion": "Деловая встреча",
    "items": [
      {
        "id": "item-2",
        "title": "Черный структурированный блейзер",
        "category": "outerwear",
        "color": "Черный",
        "imageUrl": "https://..."
      }
    ],
    "stylistReasoning": "Контраст черного верха со светлым низом балансирует строгие пропорции.",
    "matchScore": 97,
    "confidenceTips": [
      "Заправьте рубашку в брюки для создания вертикали силуэта."
    ]
  },
  "referencedItemIds": ["item-2", "item-1", "item-4", "item-8"]
}
```
