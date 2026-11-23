# Поиск гардероба — часть Матвея, КТ-2

Для добавления или замены одной вещи используйте `RAGService.retrieve_slot` или команду `wardrobe_rag search-slot --request ПУТЬ_К_JSON`. Контракт и три проверочных примера описаны в [INTEGRATION.md](INTEGRATION.md). Фотопилот на 12 парах, команда запуска и результаты описаны в [RESEARCH.md](RESEARCH.md#расширенный-фотопилот-на-12-пальто).

Пакет `wardrobe_rag` работает независимо от FastAPI и LLM: сохраняет гардероб в Chroma, выполняет BM25, текстовый и визуальный поиск, возвращает кандидатов по слотам и проверяет выбранные ID. Подключение к backend — [INTEGRATION.md](INTEGRATION.md), исследование — [RESEARCH.md](RESEARCH.md).

## Окружение

Поддерживается Python 3.11–3.14; для ноутбука показа рекомендуется Python 3.12. CPU поддерживается, GPU необязателен. Диапазоны зависимостей задаёт `pyproject.toml`; фактические версии использованного окружения указываются в результатах проверки.

С `uv` можно установить зафиксированные зависимости командой `uv sync --locked --extra test` из `rag/`. Затем запускайте `uv run --locked python -m wardrobe_rag ...`. Готовность моделей и индекса проверена на Windows с Python 3.14.3 и CPU.

PowerShell, из корня репозитория:

```powershell
cd rag
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

Linux/macOS:

```bash
cd rag
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

Далее `python` означает интерпретатор этого окружения. В PowerShell можно указывать `.\.venv\Scripts\python.exe` полностью, без изменения execution policy.

Первый запуск требует сети для скачивания весов. Затем тот же кеш используется автономно:

```powershell
python -m wardrobe_rag --cache-dir .model_cache --public-root ../public init-models
```

Перед показом 27 ноября создайте окружение на ноутбуке Егора и скачайте модели заранее. Три набора весов занимают около 2,3 ГБ, дополнительно нужно место под пакеты и индекс. Переносить можно исходники, data-файлы и полный модельный кеш. Проверяйте автономный запуск с тем же `--cache-dir` и флагом `--offline`.

## Режимы и модели

| Режим | Источник ранжирования |
|---|---|
| `bm25` | Только лексические совпадения |
| `dense` | Текстовый MPNet |
| `hybrid` | BM25 + текстовый Dense через weighted RRF |
| `visual` | Русский текст → изображения или изображение → изображения |
| `multimodal` | BM25 + текстовый Dense + визуальный Dense |

Семантическая модель — `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Для изображения используется `sentence-transformers/clip-ViT-B-32`, для русского запроса к изображениям — выровненная с ним `clip-ViT-B-32-multilingual-v1`, как в [примере авторов](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1).

MPNet и CLIP хранятся в отдельных векторных коллекциях; их векторы не складываются. Сливаются ранги. Исходно `alpha=0.65`, `visual_weight=0.35`, `rrf_c=60`. В мультимодальном режиме веса каналов: BM25=`1-alpha`, текст=`alpha*(1-visual_weight)`, изображения=`alpha*visual_weight`. Если один Dense-канал недоступен, его вес перераспределяется внутри Dense-группы с диагностикой.

Отбор ограничен пользователем и категорией до Top-K. Возвращается до 3 tops, 3 bottoms, 3 shoes, 2 outerwear и 2 accessories. Нулевые лексические совпадения не получают фиктивных BM25-рангов. Метрики и веса не являются вероятностью качества или процентом гармонии.

## Данные и изображения

`WardrobeItem` принимает текущие frontend-поля и необязательные `imagePath`, структурированный `weather`. `user_id` передаётся отдельно. Один `item-1` может принадлежать нескольким личным гардеробам без коллизии.

`sync` полностью заменяет снимок одного пользователя: изменения переиндексируются, удалённые вещи исчезают, повторный снимок не создаёт дубликатов. Пустой массив очищает только указанного пользователя. Поисковый текст собирается из актуальных полей; потенциально устаревший `embeddingSnippet` исключён.

Изображения принимаются из `public_root`, разрешённого `upload_root` и PNG/JPEG/WebP Data URL. SVG растеризуются. Произвольные HTTP/file URL, пути вне разрешённых каталогов и внешние ресурсы SVG не загружаются.

Экспорт исходной капсулы из TypeScript без ручного дублирования:

```powershell
node scripts/export_frontend_seed.mjs
```

Файлы: `data/wardrobe_seed.json` — исходные 10 вещей; `data/wardrobe_eval.json` — явно синтетический корпус 60 вещей; `queries_test.json` — 20 тестовых запросов, `queries_dev.json` — 6 отдельных dev-примеров. Визуальные запросы вынесены в `queries_visual_text.json` и `queries_visual_image.json`.

## Запуск

Команды выполняются из `rag/`; глобальные опции ставятся перед именем команды:

```powershell
python -m wardrobe_rag --data-dir .rag_data --public-root ../public index --input data/wardrobe_seed.json --user demo
python -m wardrobe_rag --data-dir .rag_data --public-root ../public search --user demo --mode hybrid --query "Москва: +6°C, ветрено, деловая встреча"
python -m wardrobe_rag --data-dir .rag_data --public-root ../public search --user demo --mode visual --query "бежевый тренч"
python -m wardrobe_rag --data-dir .rag_data --public-root ../public search --user demo --mode visual --image /clothes/shirt.svg
python -m wardrobe_rag --data-dir .rag_data --public-root ../public search --user demo --mode multimodal --query "вечернее открытие выставки в галерее"
```

Для настоящей фотографии задайте `--upload-root` и путь внутри неё. Отсутствующие в автономном кеше модели вызывают ошибку; приложение не заменяет их искусственными эмбеддингами. Для текущих аргументов CLI доступны `--help` и `evaluate --help`.

JSON поиска содержит `candidates_by_slot`, `required_slots`, `missing_slots`, warnings, timings, revision и модельный fingerprint. У каждого кандидата есть исходные scores/distances, ранги и вклады RRF. Cosine distance: меньше — лучше. Это результат retrieval, а не текст LLM.

Отдельная инженерная панель показывает запрос из браузера, настоящие веса и вклады каналов, вещи по слотам и загрузку изображения:

```powershell
python -m wardrobe_rag --offline demo --port 8765
```

Откройте `http://127.0.0.1:8765`. Это локальная демонстрация работы модуля поиска. В панели нет LLM; её нельзя выдавать за выполненный общий сценарий UI → LLM.

По умолчанию стенд использует 10 исходных вещей с дополнительными погодными признаками в `data/wardrobe_demo_weather.json`. В сценарии «+6°C, ветер» учебная разметка помечает рубашку слишком лёгкой для основного верха, а блейзер незащищающим от ветра. Тренч и кашемировый джемпер проходят фильтры. Эти пороги заданы для сценария показа. Для исходной капсулы без разметки укажите `--input data/wardrobe_seed.json`.

Проверка трёх вещей и отсутствующей обуви:

```powershell
python -m wardrobe_rag --offline demo --input data/wardrobe_demo_three.json --port 8766
python -m wardrobe_rag --offline demo --input data/wardrobe_demo_missing_shoes.json --port 8767
```

При параллельном запуске стендов задайте каждому свой глобальный `--data-dir`, например `--data-dir .rag_data_three`. Для загрузки изображения на защите выберите `data/visual_queries/item-6.png`. Если файла нет, сначала выполните `python -m wardrobe_rag prepare-visual-queries`.

## Комплект и ограничения

Базовые обязательные слоты: верх, низ, обувь. Холодная погода или дождь могут сделать outerwear обязательным. Явные погодные факты используются в ограничениях; неизвестные значения вызывают предупреждения. `season` не доказывает температурную пригодность.

`assemble_outfit` — детерминированная сборка для проверки ограничений. Она перебирает допустимые сочетания и использует небольшую явно заданную эвристику цветовых акцентов. Это не обученная оценка вкуса и не ответ LLM. `validate_selection` проверяет ID, дубликаты, количество предметов в категориях, обязательные слоты и якорную вещь. Сервис дополнительно отклоняет результат при изменении revision гардероба.

При нехватке обуви возвращается неполный результат; чужие вещи не подставляются. В первой версии допускается один предмет каждого основного слота. Рубашка + джемпер как две отдельные роли многослойности потребует расширения схемы.

Если для существующей категории нет retrieval-свидетельств, возможны явно обозначенные `fallback=true` кандидаты с score=0 и отсутствующими рангами. Они помогают заполнить категории, но исключены из HitRate/MRR и релевантного покрытия слотов. Поэтому fallback не завышает качество поиска.

## Проверки и границы исследования

```powershell
python -m pytest
python -m wardrobe_rag --help
python -m wardrobe_rag evaluate --help
```

Запуски экспериментов выполняются отдельно:

```powershell
python -m wardrobe_rag --offline --data-dir .rag_data_eval --public-root ../public evaluate --dataset data/queries_test.json --corpus data/wardrobe_eval.json --user research --output results/text --repeats 3
python -m wardrobe_rag --public-root ../public prepare-visual-queries --corpus data/wardrobe_seed.json --output data/visual_queries
python -m wardrobe_rag --offline --data-dir .rag_data_visual --public-root ../public --upload-root data/visual_queries evaluate --dataset data/queries_visual_text.json --corpus data/wardrobe_seed.json --user demo --modes visual --output results/visual_text --repeats 3
python -m wardrobe_rag --offline --data-dir .rag_data_visual --public-root ../public --upload-root data/visual_queries evaluate --dataset data/queries_visual_image.json --corpus data/wardrobe_seed.json --user demo --modes visual --output results/visual_image --repeats 3
```

Каждый прогон сохраняет summary.json, per_query.csv, measurements.csv, raw_rankings.jsonl и research_report.md. Пилотная ground truth требует независимого просмотра командой до научных выводов; подбор alpha на финальных 20 запросах не проводится.

Unit-тесты используют только тестовый детерминированный embedder и настоящую Chroma: реальные веса для них не скачиваются. Проверяются persistence, синхронизация, обновление/удаление, изоляция владельцев, изображения, fusion, слоты и финальная валидация. Реальные encoder/evaluation прогоны выполняются отдельно и фиксируются в артефактах.

Десять стартовых SVG проверяют работу image pipeline. Они не подтверждают качество поиска по фотографиям. Повторение SVG в синтетическом корпусе также не создаёт независимый визуальный benchmark. Эти ограничения сохранены в исследовательском отчёте.

Фронтенд запускается прежними командами из корня репозитория. Live UI → LLM требует подключения пакета к backend Егора и клиентскому API Александры.
