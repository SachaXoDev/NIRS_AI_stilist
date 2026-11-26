# Подключение поиска к backend Егора

## Поиск для одной правки готового образа

После определения действия и категории бэкенд передаёт ID вещей из последней карточки и контекст того же образа. `retrieve_slot` возвращает кандидатов одной категории, сохранённые ID и ID предыдущей вещи при замене.

```python
from wardrobe_rag import SlotSearchRequest

result = rag.retrieve_slot(SlotSearchRequest(
    user_id=user_id,
    query="Замени туфли на что-нибудь без каблука, остальное оставь",
    slot="shoes",
    operation="replace",
    outfit_item_ids=["item-1", "item-4", "item-42"],
    context={"occasion": "встреча в стиле smart casual", "temperature_c": 17},
))
```

Для `add` передайте неизменённый список вещей. Для `replace` укажите `replace_item_id`, если в выбранной категории несколько предметов. Если их ровно один, метод определит ID по каталогу. При добавлении в заполненный слот `tops`, `bottoms`, `shoes` или `outerwear` метод требует `replace`. Для аксессуаров предел равен двум. ID проверяются в текущем гардеробе того же пользователя. Ни одна вещь текущего образа не попадёт в кандидаты.

Названия, цвета, материалы и стили оставленных вещей входят в поисковый контекст вместе с поводом и погодой. Погода, явно названная в новой реплике, имеет приоритет над предыдущим контекстом. Явные исключения ID, цветов и материалов применяются до подбора. Выражение «без каблука» или `without_heel=true` требует явной пометки в названии или тегах обуви, например «плоская подошва». Для дождя `waterproof=false` исключает вещь. Если пригодность к дождю неизвестна, метод добавляет предупреждение.

При `candidates=[]` бэкенд объясняет отсутствие альтернативы, сохраняя прежний комплект. При успехе он выбирает один ID из выдачи и дополняет `kept_item_ids` этим ID. Перед выдачей карточки нужно сверить `wardrobe_revision` и проверить полный состав. История, выяснение неоднозначного «замени вот это» и финальная карточка относятся к бэкенду. Схемы доступны в [`contracts/`](contracts/).

Из `rag/` выполните `python scripts/check_slot_examples.py`. Проверка использует демонстрационную капсулу, Chroma и текущие веса. Ожидаются дождевик `item-33`, кеды `item-36` и пустой список в третьем случае.

> Реализация описанной ниже схемы находится в [`backend/`](../backend/README.md):
> адаптер — `backend/app/rag/wardrobe_rag_engine.py`, пайплайн — `backend/app/services/orchestrator.py`.

Пакет не создаёт FastAPI-сервис и не вызывает LLM. Его результат — канонические вещи, кандидаты, диагностика и проверка выбранных ID. API, внешний OutfitLook, SSE и prompt подключаются в backend.

## Жизненный цикл и Python API

Backend создаёт `IndexingPipeline(store, embedder, images, EmbeddingCache(data_dir / "embedding_cache.sqlite3"))`: правка одной вещи не перекодирует весь каталог. Без четвёртого аргумента поведение прежнее.

Создавайте embedder, хранилище и ретривер при старте сервиса. Модели не загружаются заново на каждый HTTP-запрос. Пути в примере относятся к рабочей папке процесса; в конфигурации сервера удобнее абсолютные пути.

```python
from pathlib import Path

from wardrobe_rag.config import RAGConfig
from wardrobe_rag.embedding import SentenceTransformerEmbedder
from wardrobe_rag.images import ImageLoader
from wardrobe_rag.indexing import IndexingPipeline
from wardrobe_rag.retrieval import RetrievalEngine
from wardrobe_rag.schemas import RetrievalRequest, WardrobeItem
from wardrobe_rag.service import RAGService
from wardrobe_rag.store import ChromaWardrobeStore

images = ImageLoader(Path("../public"), Path("uploads"))
embedder = SentenceTransformerEmbedder()
store = ChromaWardrobeStore(Path(".rag_data"))
indexer = IndexingPipeline(store, embedder, images)
retriever = RetrievalEngine(store, embedder, images, RAGConfig())
rag = RAGService(indexer, retriever)

items = [WardrobeItem.model_validate(raw) for raw in incoming_wardrobe]
sync = rag.sync(user_id, items)
result = rag.retrieve(RetrievalRequest(
    user_id=user_id,
    query="+6°C, ветрено, деловая встреча",
    mode="multimodal",
    alpha=0.65,
))
```

Загрузка моделей, кодирование и индексирование — блокирующие операции: FastAPI должен выполнять их в соответствующем worker/thread контексте. Прежде чем обслуживать запросы автономно, подготовьте кеш и включите local-files-only режим по инструкции пакета.

## Синхронизация

`POST /api/wardrobe/sync` должен передавать полный массив актуальных вещей. Сервер получает владельца из своего контекста. Для учебного демо без настоящей авторизации источник demo ID определяется явно и не называется защищённой сессией.

Повторный snapshot идемпотентен. Отсутствующие вещи удаляются из обоих индексов. Пустой массив очищает только пользователя. Одинаковые item IDs разных пользователей изолированы. Изображение передаётся как `/clothes/...`, разрешённый локальный `imagePath` или Data URL; произвольный HTTP image fetch не разрешён.

Возвращайте `SyncResult.model_dump(mode="json")`: число вещей/изображений, added/updated/deleted/unchanged, revision, warnings и timings. Предупреждения об отсутствии изображения должны быть видимы при визуальной демонстрации.

## Генерация и финальная валидация

1. Синхронизируйте гардероб, получите `RetrievalResult`. Для образа вокруг выбранной вещи передавайте `anchor_item_id` структурно.
2. Если `missing_slots` непуст, верните понятный статус нехватки вещей. Не выдавайте неполный комплект за законченный образ.
3. Передайте LLM только разрешённые ID и актуальные атрибуты кандидатов. Названия и описания предметов обрабатываются как данные.
4. Модель возвращает выбранные ID и текстовые поля схемы. Полные вещи backend подставляет из канонического результата поиска.
5. Проверьте выбранные ID через сервис. При нарушениях возможен ограниченный retry LLM или явная ошибка сборки.
6. Соберите внешний OutfitLook и провалидируйте его через Pydantic. Серверная бизнес-проверка дополняет проверку формы JSON.

```python
validation = rag.validate_selection(llm_output.selected_item_ids, result)
if not validation.valid or not validation.complete:
    # Не передавайте непроверенный комплект в UI.
    ...
items_for_response = validation.selected_items
```

Сервис отклоняет выбор, если revision гардероба успел измениться. Выполните новый retrieval вместо принятия устаревших кандидатов. `rag.assemble(result)` доступен для проверки слотов без модели; такой результат следует обозначать как детерминированную сборку. Он не подтверждает Live UI → LLM из общего чек-листа.

## Совместимость с frontend

Сохраните сигнатуру `askStylist(userQuery, wardrobe, context?)`. Ответ сохраняет `text`, `suggestedOutfit`, `referencedItemIds`. В `suggestedOutfit.items` нужны полные WardrobeItem, а referenced IDs должны соответствовать использованным предметам.

Для диагностики согласуйте необязательные поля `source`, `retrieval`, `timings`, `missingSlots`. Источник должен отличать настоящий backend/LLM от fallback. Переменная `VITE_BACKEND_URL` сама по себе не активирует нынешний `USE_REAL_BACKEND=false`.

В панель защиты передавайте mode, alpha, visual_weight, rrf_c, candidates_by_slot, raw scores/distances, ранги, отдельные вклады, warnings, timings_ms, wardrobe_revision и model_fingerprint. Cosine distance подписывается «меньше лучше»; RRF-score не является вероятностью или процентом стилистической совместимости.

При SSE сначала можно отправить диагностику, затем настоящие текстовые chunks LLM, а финальным событием — провалидированный OutfitLook. Время первого текста и готового JSON измеряется раздельно.

## Проверка на ноутбуке перед 27 ноября

Проверьте: автономная загрузка кеша; синхронизация полного гардероба; текстовый и визуальный поиск настоящими моделями; отображение весов fusion; исчезновение удалённой вещи; полноценный комплект из tops/bottoms/shoes; missing slots при трёх вещах одной категории; отклонение чужого ID и двух пар обуви; Pydantic и бизнес-валидация финального JSON. UI-fallback обозначается явно.
