# Архитектура фронтенда и контракт интеграции

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
