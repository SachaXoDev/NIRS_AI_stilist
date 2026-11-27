"""Generate the 16:9 AI LOOKBOOK defense deck with python-pptx and rsvg-convert.

Optional --wardrobe-screen and --kt2-screen accept real site captures (PNG/JPG).
Regeneration reuses the named captures from the existing deck unless overridden.
The original garment illustrations are rendered from public/clothes at generation.
"""

import argparse
import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import subprocess

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
DEFAULT_DECK = ROOT / "AI_Stylist_Presentation.pptx"
DATA = ROOT / "backend" / "kt2_data"
WIDTH, HEIGHT = 13 + 1 / 3, 7.5
LEFT, RIGHT = 0.6, WIDTH - 0.6
FONT = "Inter"


@dataclass(frozen=True)
class Theme:
    canvas: str
    panel: str
    fill: str
    edge: str
    ink: str
    muted: str
    accent: str
    on_accent: str


# Current site tokens from index.css and the actual App/Chat/Outfit components.
DAY = Theme("F6F4F0", "FCFAF7", "EFECE6", "DFD9CF", "1E1B18", "6B6359", "1E1B18", "F7F5F0")
NIGHT = Theme("191A1D", "25272C", "212328", "40434B", "EEECEF", "CAC7D0", "D7C2C7", "211D22")
STAND_ACCENT = "FB7185"  # backend/app/kt2_demo.html
STAND_PANEL = "171717"
STAND_LINK = "FDA4AF"
WARDROBE_CAPTURE = "Live screen — Wardrobe"
KT2_CAPTURE = "Live screen — KT-2 answer"

BLOUSE = ("ivory-bow-blouse", "Молочная блуза", "с воротником-бантом")
SKIRT = ("graphite-pencil-skirt", "Графитовая юбка", "прямой крой")
DERBIES = ("burgundy-derbies", "Бордовые дерби", "низкий каблук")
PUMPS = ("black-block-heel-pumps", "Чёрные лодочки", "устойчивый каблук")


def rgb(hex_value):
    return RGBColor.from_string(hex_value)


def box(slide, x, y, w, h, fill, edge=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    if edge:
        shape.line.color.rgb = rgb(edge)
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    return shape


def text(slide, x, y, w, h, value, size, color, *, bold=False, align=PP_ALIGN.LEFT,
         tracking=0, link=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    shape.name = value.split("\n", 1)[0]
    frame = shape.text_frame
    frame.clear()
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.word_wrap = True
    for i, line in enumerate(value.split("\n")):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.space_before = paragraph.space_after = Pt(0)
        paragraph.line_spacing = 1.07
        run = paragraph.add_run()
        run.text = line
        if link:
            run.hyperlink.address = link
        font = run.font
        font.name = FONT
        font.size = Pt(size)
        font.bold = bold
        font.underline = bool(link)
        font.color.rgb = rgb(color)
        properties = run._r.get_or_add_rPr()
        properties.set("lang", "ru-RU")
        if tracking:
            properties.set("spc", str(tracking))  # hundredths of a point
    return shape


def label(slide, x, y, w, value, color):
    return text(slide, x, y, w, 0.24, value, 10.5, color, bold=True, tracking=110)


def button(slide, x, y, w, value, fill, ink, *, link=None):
    box(slide, x, y, w, 0.39, fill)
    text(slide, x + 0.11, y, w - 0.22, 0.39, value, 11.5, ink, bold=True, tracking=30, link=link)


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body


def new_slide(prs, number, section, theme=DAY):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(theme.canvas)
    label(slide, LEFT, 0.25, 1.48, "12 STOREEZ", theme.ink)
    box(slide, 1.95, 0.29, 0.013, 0.16, theme.edge)
    label(slide, 2.11, 0.25, 2.25, "AI LOOKBOOK", theme.muted)
    text(slide, RIGHT - 4.5, 0.25, 4.5, 0.24, section, 10.5, theme.muted,
         bold=True, tracking=85, align=PP_ALIGN.RIGHT)
    box(slide, 0, 0.71, WIDTH, 0.012, theme.edge)
    box(slide, LEFT, 7.04, RIGHT - LEFT, 0.012, theme.edge)
    text(slide, LEFT, 7.10, 6.7, 0.26, "НИРС 2026  /  ЗАЩИТА КТ-2", 9.5, theme.muted, tracking=85)
    text(slide, RIGHT - 1.4, 7.10, 1.4, 0.26, f"{number:02d} / 08", 10, theme.muted,
         tracking=75, align=PP_ALIGN.RIGHT)
    return slide


def heading(slide, theme, title, subtitle=None):
    text(slide, LEFT, 0.95, RIGHT - LEFT, 0.64, title, 34, theme.ink, bold=True)
    if subtitle:
        text(slide, LEFT, 1.64, RIGHT - LEFT, 0.35, subtitle, 15.5, theme.muted)


def picture(slide, data, name, description, x, y, width):
    shape = slide.shapes.add_picture(BytesIO(data), Inches(x), Inches(y), width=Inches(width))
    shape.name = name
    shape._element.nvPicPr.cNvPr.set("descr", description)
    return shape


def garment_assets():
    assets = {}
    for slug, _, _ in (BLOUSE, SKIRT, DERBIES, PUMPS):
        source = ROOT / "public" / "clothes" / "capsule" / f"{slug}.svg"
        assets[slug] = subprocess.run(["rsvg-convert", "--width", "540", str(source)],
                                      check=True, capture_output=True).stdout
    return assets


def garment(slide, assets, item, x, y, w, theme, *, highlight=False):
    slug, title, detail = item
    image_h = (w - 0.024) * 400 / 360
    cap_h = 0.75
    box(slide, x, y, w, image_h + cap_h, theme.panel, theme.edge)
    picture(slide, assets[slug], title, f"Иллюстрация из гардероба: {title}", x + 0.012, y + 0.012, w - 0.024)
    if highlight:
        edge = NIGHT.accent if theme == NIGHT else "8A5D66"
        box(slide, x, y + image_h, w, 0.034, edge)
    text(slide, x + 0.10, y + image_h + 0.08, w - 0.20, 0.30, title, 11.2, theme.ink, bold=True)
    text(slide, x + 0.10, y + image_h + 0.38, w - 0.20, 0.27, detail, 9.4, theme.muted)


def slide_cover(prs, assets):
    t = DAY
    s = new_slide(prs, 1, "ПЕРСОНАЛЬНЫЙ СТИЛИСТ", t)
    label(s, LEFT, 1.37, 5.1, "НИРС 2026  /  МГТУ ИМ. Н. Э. БАУМАНА", t.muted)
    text(s, LEFT - 0.03, 1.92, 6.2, 1.69, "Ваш гардероб.\nВаш AI-стилист.", 46, t.ink, bold=True)
    text(s, LEFT, 3.98, 5.64, 0.93, "Лукбук собирает и редактирует образы из ваших вещей. Стенд КТ-2 отвечает на вопросы по карточкам капсулы.", 17, t.muted)
    button(s, LEFT, 5.25, 1.77, "ЗАЩИТА КТ-2", t.accent, t.on_accent)
    text(s, LEFT, 6.43, 6.1, 0.26, "Александра Ходина  ·  Матвей Рыбин  ·  Егор Баринов", 12, t.muted)

    x, y, w = 6.64, 1.28, RIGHT - 6.64
    box(s, x, y, w, 5.40, t.fill)
    label(s, x + 0.25, y + 0.24, 4.6, "ГАРДЕРОБ  /  БАЗОВАЯ КАПСУЛА", t.ink)
    text(s, x + 0.29, y + 0.67, w - 0.58, 0.41, "Офисный образ", 23, t.ink, bold=True)
    for i, item in enumerate((BLOUSE, SKIRT, DERBIES)):
        garment(s, assets, item, x + 0.25 + i * 1.90, y + 1.30, 1.79, t)
    box(s, x + 0.25, y + 4.29, w - 0.50, 0.012, t.edge)
    text(s, x + 0.25, y + 4.52, w - 0.50, 0.35, "Верх · Низ · Обувь", 15.5, t.muted)
    notes(s, "Учебный проект НИРС, а не официальный сервис бренда. Визуальная эстетика вдохновлена 12 STOREEZ. Справа — иллюстрации вещей из сайта. Сформулировать две части защиты: продуктовый чат и отдельный эксперимент на той же базовой капсуле.")


def slide_product(prs):
    t = DAY
    s = new_slide(prs, 2, "ЗАДАЧА И РЕШЕНИЕ", t)
    heading(s, t, "Полный шкаф, а надеть нечего")
    box(s, LEFT, 2.02, 4.24, 4.56, t.ink)
    label(s, LEFT + 0.24, 2.30, 3.76, "ПРОБЛЕМА", "DDD2C7")
    text(s, LEFT + 0.24, 2.82, 3.76, 1.36, "Привычные вещи,\nпривычные образы", 26, t.on_accent, bold=True)
    text(s, LEFT + 0.24, 4.51, 3.76, 1.08,
         "Вещи забываются, а повод и погода меняются. Каталог магазина не подскажет, что собрать из того, что уже есть.", 16, "DDD2C7")
    rows = (
        ("01", "Собрать гардероб", "Добавить свои вещи или базовую капсулу из 50 вещей. Капсула дополняет гардероб, а не заменяет его."),
        ("02", "Описать задачу", "Назвать повод, погоду или вещь, от которой нужно оттолкнуться. Стилист предложит образ и объяснит выбор."),
        ("03", "Уточнить и сохранить", "Попросить заменить одну вещь без смены всего комплекта и сохранить удачный вариант в Лукбук."),
    )
    x = 5.18
    for i, (number, title, desc) in enumerate(rows):
        y = 2.02 + i * 1.52
        box(s, x, y, RIGHT - x, 0.012, t.edge)
        text(s, x, y + 0.20, 0.65, 0.37, number, 15, t.muted, tracking=95)
        text(s, x + 0.76, y + 0.16, RIGHT - x - 0.76, 0.46, title, 23, t.ink, bold=True)
        text(s, x + 0.76, y + 0.68, RIGHT - x - 0.86, 0.59, desc, 15.3, t.muted)
    box(s, x, 6.58, RIGHT - x, 0.012, t.edge)
    notes(s, "Цель: помочь человеку использовать уже имеющиеся вещи, а не выдать абстрактный наряд. Составы, крой, оттенки и свойства карточек становятся контекстом поиска. Покажем подбор и точечную правку отдельно от количественной оценки поиска по карточкам.")


def slide_interface(prs, capture, assets):
    t = DAY
    s = new_slide(prs, 3, "ИНТЕРФЕЙС", t)
    heading(s, t, "Три раздела одного Лукбука")
    x, y, w = LEFT, 1.89, 7.62
    if capture:
        shot = picture(s, capture, WARDROBE_CAPTURE, "Снимок работающего сайта: базовая капсула из 50 вещей, вкладки и фильтры", x, y, w)
        shot_h = shot.height / Inches(1)
        if shot_h > 4.78:
            shot.height = Inches(4.78)
            shot.crop_bottom = 1 - 4.78 / shot_h
        label(s, x, 6.75, w, "СНИМОК САЙТА  /  ГАРДЕРОБ С ДОБАВЛЕННОЙ КАПСУЛОЙ", t.muted)
    else:
        box(s, x, y, w, 4.76, t.fill, t.edge)
        label(s, x + 0.24, y + 0.24, w - 0.48, "ГАРДЕРОБ (50)  /  БАЗОВАЯ КАПСУЛА", t.ink)
        text(s, x + 0.24, y + 0.72, w - 0.48, 0.36,
             "Все     Верх     Низ     Верхняя одежда     Обувь     Аксессуары", 12, t.muted)
        for i, item in enumerate((BLOUSE, SKIRT, DERBIES, PUMPS)):
            garment(s, assets, item, x + 0.24 + 1.81 * i, y + 1.36, 1.69, t)
        label(s, x, 6.75, w, "СХЕМА ГАРДЕРОБА  /  ИЛЛЮСТРАЦИИ ИЗ КАПСУЛЫ", t.muted)
    x = 8.57
    for i, (num, title, detail) in enumerate((
        ("01", "Стилист", "История диалогов, подсказки по поводу и погоде, карточка образа в чате."),
        ("02", "Гардероб", "Каталог вещей с поиском и фильтрами по категории, подкатегории и стилю."),
        ("03", "Лукбук", "Сохранённые сочетания: к ним можно вернуться и поделиться формулой образа."),
    )):
        y = 2.01 + 1.40 * i
        box(s, x, y, RIGHT - x, 0.012, t.edge)
        label(s, x, y + 0.23, 0.56, num, t.muted)
        text(s, x + 0.62, y + 0.12, RIGHT - x - 0.62, 0.43, title, 22, t.ink, bold=True)
        text(s, x + 0.62, y + 0.64, RIGHT - x - 0.62, 0.56, detail, 14.4, t.muted)
    box(s, x, 6.22, RIGHT - x, 0.012, t.edge)
    text(s, x, 6.36, RIGHT - x, 0.38, "Мобильная навигация · Дневная и вечерняя темы", 12, t.muted)
    notes(s, "Слева показан гостевой гардероб после действия «Базовая капсула». Личные вещи при этом не удаляются. Три вкладки соответствуют реальному сайту. В мобильной версии навигация адаптируется; интерфейс поддерживает дневную и вечернюю темы.")


def slide_architecture(prs):
    t = NIGHT
    s = new_slide(prs, 4, "АРХИТЕКТУРА", t)
    heading(s, t, "Чат и стенд работают по-разному", "Общая демо-капсула, разные индексы, выходы и критерии проверки.")
    lanes = (
        ("01  /  ОСНОВНОЙ ЧАТ", t.accent, (
            ("React → FastAPI", "Запрос, гардероб,\nповод и погода"),
            ("Гибридный RAG", "Фильтры и поиск по слотам:\nBM25 + Dense, Chroma¹"),
            ("Qwen + проверка", "Модель выбирает ID,\nсервер проверяет состав"),
            ("Карточка / SSE", "Готовый образ,\nобъяснение и правка"),
        )),
        ("02  /  ИЗОЛИРОВАННЫЙ СТЕНД КТ-2", STAND_LINK, (
            ("Вопрос о вещах", "Отдельный экран /kt2\nи независимый API"),
            ("Свой BM25", "Обратный индекс;\nдо 3 из 30 карточек"),
            ("Локальная Qwen", "Ответ по карточкам,\nбез выбора аутфита"),
            ("Ответ или отказ", "Цитаты и выдача BM25\nпоказаны отдельно"),
        )),
    )
    for row, (tag, accent, tiles) in enumerate(lanes):
        y = 2.25 + row * 2.04
        label(s, LEFT, y, 8.0, tag, accent)
        for i, (title, desc) in enumerate(tiles):
            x = LEFT + i * 3.095
            box(s, x, y + 0.39, 2.84, 1.37, t.panel, t.edge)
            text(s, x + 0.15, y + 0.53, 2.54, 0.34, title, 17.2, t.ink, bold=True)
            text(s, x + 0.15, y + 0.94, 2.54, 0.59, desc, 13.1, t.muted)
            if i < 3:
                text(s, x + 2.84, y + 0.71, 0.255, 0.47, "→", 11.5, accent, align=PP_ALIGN.CENTER)
    text(s, LEFT, 6.46, RIGHT - LEFT, 0.35,
         "¹ В модуле основного чата есть визуальный поиск CLIP; для /kt2 эмбеддинги и Chroma не нужны.", 12.5, t.muted)
    notes(s, "Основной backend синхронизирует личный гардероб, фильтрует по поводу/погоде, подбирает кандидатов по слотам и валидирует ID. Неполный или непроверенный комплект не выдаётся за готовую карточку. Пакет wardrobe_rag включает Chroma, гибридное ранжирование и визуальный поиск CLIP. Для бенчмарка реализован независимый собственный обратный индекс BM25; его метрики не описывают гибридный ретривер. Лукбук настраивается на локальную Qwen или другой OpenAI-совместимый провайдер; у стенда собственная локальная модель.")


def slide_edit(prs, assets):
    t = DAY
    s = new_slide(prs, 5, "ПРОДУКТОВЫЙ СЦЕНАРИЙ", t)
    heading(s, t, "Меняем обувь, а не весь образ", "Основной чат  /  пример офисного образа из вещей демо-капсулы")
    groups = (
        (LEFT, "01  /  ПОДБОР", "«Подбери лаконичный образ для деловой встречи в офисе»", DERBIES),
        (6.87, "02  /  ПРАВКА", "«Замени обувь, остальное оставь»", PUMPS),
    )
    for x, tag, prompt, shoes in groups:
        box(s, x, 2.23, 5.86, 3.95, t.fill, t.edge)
        label(s, x + 0.17, 2.38, 5.52, tag, t.muted)
        text(s, x + 0.17, 2.69, 5.52, 0.44, prompt, 13.4, t.ink, bold=True)
        for i, item in enumerate((BLOUSE, SKIRT, shoes)):
            garment(s, assets, item, x + 0.17 + 1.86 * i, 3.28, 1.79, t,
                    highlight=shoes == PUMPS and i == 2)
    text(s, 6.46, 4.15, 0.41, 0.52, "→", 20, t.ink, align=PP_ALIGN.CENTER)
    box(s, LEFT, 6.36, RIGHT - LEFT, 0.43, t.ink)
    text(s, LEFT + 0.15, 6.36, RIGHT - LEFT - 0.30, 0.43,
         "Блуза и юбка остаются. Дерби сменяются на лодочки. В живом демо сверяем ID вещей в двух карточках.", 13.4, t.on_accent)
    notes(s, "Это пример из предыдущего показа, воспроизведённый редактируемыми карточками и реальными иллюстрациями сайта. Не обещать конкретную пару обуви в каждом новом запуске: критерий демонстрации — заменился только слот обуви, ID верха и низа не изменились. Отдельные сценарии поиска по категории и тесты backend/tests/test_outfit_edit.py проверяют точечные правки; бенчмарк КТ-2 этот сценарий не измеряет.")


def format_decimal(value, digits):
    return f"{value:.{digits}f}".replace(".", ",")


def slide_benchmark(prs):
    t = DAY
    s = new_slide(prs, 6, "КТ-2  /  РЕЗУЛЬТАТЫ", t)
    runs = [json.loads((DATA / directory / "summary.json").read_text(encoding="utf-8")) for directory in (
        "capsule_run", "capsule_stopwords_run", "capsule_generation_run",
    )]
    final = runs[-1]
    counts = final["counts"]
    ordinary, traps = (counts["answered_by_kind"][kind] for kind in ("positive", "trap"))
    metrics = final["metrics"]
    heading(s, t, "Поиск и ответы по капсуле", f"k = 3  ·  {final['document_count']} из 50 карточек  ·  {ordinary} обычных вопросов  ·  {traps} ловушек  ·  {counts['answered']}/{counts['attempted']} без ошибок")
    cards = (
        ("ПОИСК  /  RECALL@3", f"{metrics['recall_at_3']:.0%}", "30 из 30 размеченных попаданий"),
        ("ПОИСК  /  MRR@3", format_decimal(metrics["mrr_at_3"], 2), "Первый релевантный — №1"),
        ("ОТВЕТ  /  АВТОЗАЧЁТ", f"{round(metrics['accuracy'] * ordinary)}/{ordinary}", "Эвристическая Accuracy"),
        ("ОТВЕТ  /  ОТКАЗЫ", f"{round(metrics['refusal_accuracy'] * traps)}/{traps}", "Корректные отказы на ловушках"),
    )
    for i, (tag, value, desc) in enumerate(cards):
        x = LEFT + i * 3.09
        fill, ink, muted = (t.ink, t.on_accent, "DDD2C7") if i < 2 else (t.panel, t.ink, t.muted)
        box(s, x, 2.22, 2.86, 1.61, fill, t.edge)
        label(s, x + 0.14, 2.37, 2.58, tag, muted)
        text(s, x + 0.14, 2.67, 2.58, 0.63, value, 36, ink, bold=True)
        text(s, x + 0.14, 3.38, 2.58, 0.27, desc, 10.7, muted)

    label(s, LEFT, 4.10, 7.2, "ТРИ ПРОГОНА  /  ОДИН НАБОР И ОДНА МОДЕЛЬ", t.muted)
    cols = (0.15, 4.61, 5.80)
    text(s, LEFT + cols[1], 4.37, 1.04, 0.22, "Recall@3", 9.5, t.muted, bold=True, align=PP_ALIGN.RIGHT)
    text(s, LEFT + cols[2], 4.37, 1.34, 0.22, "Автозачёт", 9.5, t.muted, bold=True, align=PP_ALIGN.RIGHT)
    for i, (title, value) in enumerate(zip(("Исходный BM25", "BM25 без частых служебных слов", "Тот же BM25 + ссылка на каждое свойство"), runs)):
        y = 4.62 + 0.46 * i
        m = value["metrics"]
        box(s, LEFT, y, 7.30, 0.44, t.fill if i == 2 else t.panel)
        text(s, LEFT + cols[0], y, 4.42, 0.44, title, 12.1, t.ink, bold=i == 2)
        recall = format_decimal(m["recall_at_3"] * 100, 2).removesuffix(",00") + "%"
        text(s, LEFT + cols[1], y, 1.04, 0.44, recall, 11.5, t.ink, bold=True, align=PP_ALIGN.RIGHT)
        text(s, LEFT + cols[2], y, 1.34, 0.44, f"{round(m['accuracy'] * ordinary)}/{ordinary}", 11.5, t.ink, bold=True, align=PP_ALIGN.RIGHT)
    text(s, LEFT, 6.12, 7.30, 0.34, "Источники: сохранённые summary.json и per_query.json.", 11.3, t.muted)

    x = 8.18
    box(s, x, 4.14, RIGHT - x, 2.28, t.fill)
    label(s, x + 0.17, 4.32, RIGHT - x - 0.34, "ОГРАНИЧЕНИЕ  /  Q01", t.muted)
    text(s, x + 0.17, 4.67, RIGHT - x - 0.34, 0.68,
         "Автооценка не распознала «лён и хлопок» вместо «льна с хлопком». Ручная сверка: ответ верен.", 14, t.ink)
    text(s, x + 0.17, 5.49, RIGHT - x - 0.34, 0.69,
         "Эвристика не проверяет все добавленные утверждения. Сбои модели не считаются отказами.", 13.1, t.muted)
    text(s, LEFT, 6.62, RIGHT - LEFT, 0.27, "Метрики относятся только к /kt2: сборку и точечную правку образа проверяем отдельно.", 12.5, t.ink, bold=True)
    notes(s, f"Итоговый источник: backend/kt2_data/capsule_generation_run/summary.json и per_query.json. Модель: {final['model']}. На 10 обычных вопросах размечено по три релевантных ID. Recall@3 — средняя доля релевантных ID в топ-3; MRR@3 — средний обратный ранг первого. Автозачёт требует совпадения групп фактов и корректных ссылок на размеченные карточки. Корректный отказ на ловушке — канонический текст, флаг отказа и отсутствие цитат. Ошибка запроса делает прогон неполным. MRR@3 = 1,00 и отказы = 5/5 во всех трёх прогонах; 15/15 без ошибок в каждом. После удаления служебных слов восстановились беговые шорты для Q04. После уточнения промпта улучшился Q06 без изменения выдачи. Итоговый Q01 не прошёл эвристику из-за формулировки, а не ошибки поиска. Не переносить цифры на личные гардеробы, гибридный поиск или правку аутфитов.")


def slide_team(prs):
    t = DAY
    s = new_slide(prs, 7, "КОМАНДА И СТАТУС", t)
    heading(s, t, "Кто сделал проект и что дальше")
    members = (
        ("АХ", "Александра Ходина", "FRONTEND & PRODUCT LEAD", "Сценарии и дизайн, React-интерфейс, интеграция чата и клиентская обработка SSE."),
        ("МР", "Матвей Рыбин", "RAG & SEARCH ENGINEER", "Индексация гардероба, гибридный ретривер, текстовые и визуальные эмбеддинги."),
        ("ЕБ", "Егор Баринов", "BACKEND & LLM ENGINEER", "FastAPI, оркестрация поиска и LLM, серверная валидация и потоковая выдача."),
    )
    for i, (monogram, name, role, desc) in enumerate(members):
        x = LEFT + i * 4.14
        box(s, x, 1.92, 3.86, 2.23, t.panel, t.edge)
        circle = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.18), Inches(2.10), Inches(0.43), Inches(0.43))
        circle.fill.solid()
        circle.fill.fore_color.rgb = rgb("E5DFD5")
        circle.line.fill.background()
        text(s, x + 0.18, 2.10, 0.43, 0.43, monogram, 10.5, t.ink, bold=True, align=PP_ALIGN.CENTER)
        text(s, x + 0.18, 2.66, 3.50, 0.40, name, 19.5, t.ink, bold=True)
        label(s, x + 0.18, 3.09, 3.50, role, t.muted)
        text(s, x + 0.18, 3.46, 3.50, 0.52, desc, 12.4, t.muted)

    for i, (tag, status, detail) in enumerate((
        ("КТ-1", "Выполнено", "Автономный интерфейс, сценарии и контракт API."),
        ("КТ-2", "Готово к защите", "RAG и FastAPI в чате; отдельный стенд и бенчмарк."),
        ("КТ-3", "План", "Проверить интеграцию с магазином: каталог, импорт покупок и рекомендации."),
    )):
        y = 4.49 + i * 0.72
        if i == 1:
            box(s, LEFT, y, RIGHT - LEFT, 0.69, t.fill)
        box(s, LEFT, y, RIGHT - LEFT, 0.012, t.edge)
        label(s, LEFT + 0.15, y + 0.22, 0.83, tag, t.muted)
        text(s, LEFT + 1.15, y, 2.66, 0.69, status, 15.5, t.ink, bold=True)
        text(s, LEFT + 4.07, y, RIGHT - LEFT - 4.22, 0.69, detail, 14.3, t.muted)
    box(s, LEFT, 6.65, RIGHT - LEFT, 0.012, t.edge)
    notes(s, "Роли соответствуют README и распределению работы по контрольным точкам. КТ-1: автономный фронтенд, история сессий и спецификация. КТ-2: серверная интеграция, модуль поиска и измеримый автономный стенд. КТ-3 — гипотезы, а не готовые возможности: интеграция каталога, импорт истории покупок, рекомендации дополнений, экспорт и проверка продуктовых гипотез.")


def slide_demo(prs, capture):
    t = NIGHT
    s = new_slide(prs, 8, "ЖИВАЯ ДЕМОНСТРАЦИЯ", t)
    heading(s, t, "Два сценария на одной капсуле", "В чате проверяем состав образа. На стенде — ответы со ссылками и корректный отказ.")
    x, y, w = LEFT, 2.21, 4.27
    box(s, x, y, w, 4.37, t.panel, t.edge)
    label(s, x + 0.19, y + 0.20, w - 0.38, "01  /  ОСНОВНОЙ ЧАТ", t.accent)
    text(s, x + 0.19, y + 0.55, w - 0.38, 0.53, "Собрать и поправить", 24, t.ink, bold=True)
    text(s, x + 0.19, y + 1.26, w - 0.38, 0.69, "Войти гостем. В Гардеробе добавить базовую капсулу.", 16, t.ink)
    text(s, x + 0.19, y + 2.04, w - 0.38, 0.79, "Попросить офисный образ, затем: «Замени обувь, остальное оставь».", 16, t.ink)
    text(s, x + 0.19, y + 2.98, w - 0.38, 0.53, "Сверить: верх и низ не изменились.", 14.5, t.muted)
    button(s, x + 0.19, y + 3.75, 2.26, "localhost:5173 ↗", t.accent, t.on_accent, link="http://localhost:5173/")

    x, w = 5.08, RIGHT - 5.08
    box(s, x, y, w, 4.37, t.panel, t.edge)
    label(s, x + 0.19, y + 0.20, w - 0.38, "02  /  СТЕНД КТ-2", STAND_LINK)
    text(s, x + 0.19, y + 0.55, w - 0.38, 0.53, "Сравнить и проверить отказ", 24, t.ink, bold=True)
    sw = 4.7
    if capture:
        shot = picture(s, capture, KT2_CAPTURE, "Снимок стенда: ответ Qwen со ссылками D02, D16 и D04", x + 0.19, y + 1.21, sw)
        shot_h = shot.height / Inches(1)
        if shot_h > 1.53:
            shot.height = Inches(1.53)
            shot.crop_bottom = 1 - 1.53 / shot_h
        label(s, x + 0.19, y + 2.73, sw, "СНИМОК СТЕНДА  /  Q06", t.muted)
    else:
        box(s, x + 0.19, y + 1.21, sw, 1.35, STAND_PANEL, t.edge)
        text(s, x + 0.33, y + 1.30, sw - 0.28, 1.12,
             "Высокая посадка — тёмно-синие джинсы [D02]\nШирокие штанины — светло-голубые [D16]\nСерые палаццо — костюмная шерсть [D04]", 12, t.ink)
        label(s, x + 0.19, y + 2.73, sw, "ФРАГМЕНТ СОХРАНЁННОГО ОТВЕТА  /  Q06", t.muted)
    text(s, x + 5.13, y + 1.21, w - 5.33, 1.38,
         "Сравнить два вида джинсов и палаццо. Показать ссылки и отдельно выдачу BM25.", 14, t.muted)
    text(s, x + 0.19, y + 3.06, w - 0.38, 0.51,
         "Ловушка: точная высота каблука дерби? Карточка есть в выдаче, но числа в ней нет.", 14.3, t.ink)
    button(s, x + 0.19, y + 3.75, 2.45, "localhost:8012/kt2 ↗", STAND_ACCENT, STAND_PANEL, link="http://localhost:8012/kt2")
    notes(s, "Перед живым показом прогреть оба режима. Для чата установить VITE_USE_REAL_BACKEND=true и проверить на первом подборе финальное событие SSE: source=llm, meta.retriever=wardrobe_rag.\n\nЛукбук: «Подбери лаконичный образ для деловой встречи в офисе», затем «Замени обувь, остальное оставь». Сравнить две карточки.\n\nСтенд: «Для замены шорт сравни два варианта джинсов из капсулы и серые палаццо. Какие джинсы с высокой посадкой, у каких широкие штанины и из чего сшиты палаццо?» Показать ссылки D02, D16 и D04; ранжирование BM25 показывается отдельно. Затем: «Какая точная высота каблука в сантиметрах у бордовых дерби на низком каблуке?» Корректный отказ при найденной карточке D24: «В документах нет этой информации». При сбое живого стенда использовать сохранённые responses из backend/kt2_data/capsule_generation_run/per_query.json. Завершить слайдом 6: четыре метрики, k=3 и Q01.")


def existing_captures(path):
    if not path.is_file():
        return {}
    names = {WARDROBE_CAPTURE, KT2_CAPTURE}
    return {shape.name: shape.image.blob for slide in Presentation(path).slides for shape in slide.shapes
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE and shape.name in names}


def create_deck(output=DEFAULT_DECK, wardrobe_screen=None, kt2_screen=None):
    captures = existing_captures(output)
    for name, path in ((WARDROBE_CAPTURE, wardrobe_screen), (KT2_CAPTURE, kt2_screen)):
        if path:
            captures[name] = path.read_bytes()
    assets = garment_assets()
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(WIDTH), Inches(HEIGHT)
    prs.core_properties.title = "12 STOREEZ | AI LOOKBOOK — защита КТ-2"
    prs.core_properties.author = "Александра Ходина, Матвей Рыбин, Егор Баринов"
    prs.core_properties.subject = "НИРС 2026: AI-стилист и бенчмарк RAG по капсуле Лукбука"
    slide_cover(prs, assets)
    slide_product(prs)
    slide_interface(prs, captures.get(WARDROBE_CAPTURE), assets)
    slide_architecture(prs)
    slide_edit(prs, assets)
    slide_benchmark(prs)
    slide_team(prs)
    slide_demo(prs, captures.get(KT2_CAPTURE))
    prs.save(output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DECK)
    parser.add_argument("--wardrobe-screen", type=Path, help="Live wardrobe capture (PNG/JPG)")
    parser.add_argument("--kt2-screen", type=Path, help="Live KT-2 answer panel capture (PNG/JPG)")
    args = parser.parse_args()
    print(f"Generated {create_deck(args.output, args.wardrobe_screen, args.kt2_screen)}")
