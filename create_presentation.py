import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    # 16:9 widescreen layout
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette: Premium 12 STOREEZ "Quiet Luxury" aesthetic
    BG_CREAM = RGBColor(246, 244, 240)       # #F6F4F0 linen
    CARD_BG = RGBColor(255, 255, 255)        # Pure crisp card
    CARD_BG_ALT = RGBColor(240, 236, 230)    # Soft cashmere tint
    DARK_CARD = RGBColor(26, 24, 22)         # #1A1816 Deep rich espresso
    DARK_CARD_ALT = RGBColor(38, 34, 30)
    ACCENT_ROSE = RGBColor(185, 75, 75)      # Terracotta / berry rose
    ACCENT_GOLD = RGBColor(190, 146, 85)     # Warm brass / gold
    TEXT_DARK = RGBColor(28, 25, 23)         # Primary espresso
    TEXT_MUTED = RGBColor(115, 110, 103)     # Slate taupe
    TEXT_LIGHT = RGBColor(246, 244, 240)     # Warm linen white
    TEXT_LIGHT_MUTED = RGBColor(185, 180, 172)
    LINE_COLOR = RGBColor(226, 222, 215)
    ACCENT_GREEN = RGBColor(76, 130, 95)     # Sage green for success

    FONT_FAMILY = "Georgia"
    FONT_SANS = "Helvetica Neue"

    def set_bg(slide, color):
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = color
        bg_shape.line.fill.background()
        return bg_shape

    def add_header(slide, tag, title, dark=False):
        # Category / Tracker tag
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(0.35))
        tf = tag_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = tag.upper()
        p.font.name = FONT_SANS
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = ACCENT_GOLD if dark else ACCENT_ROSE

        # Slide Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.9), Inches(11.7), Inches(0.85))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
        p_t = tf_t.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_FAMILY
        p_t.font.size = Pt(28)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_LIGHT if dark else TEXT_DARK

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=LINE_COLOR):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    # ==========================================
    # SLIDE 1: ТИТУЛЬНЫЙ СЛАЙД (Hero Cover)
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, DARK_CARD)

    top_line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.0), Inches(1.5), Inches(0.04))
    top_line.fill.solid()
    top_line.fill.fore_color.rgb = ACCENT_GOLD
    top_line.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(10), Inches(0.4))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "12 STOREEZ  ×  CLOSET.AI"
    p.font.name = FONT_SANS
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GOLD

    tb = s1.shapes.add_textbox(Inches(0.8), Inches(1.75), Inches(11.5), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Персональный AI-Стилист\nнового поколения"
    p.font.name = FONT_FAMILY
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = TEXT_LIGHT

    tb = s1.shapes.add_textbox(Inches(0.8), Inches(4.2), Inches(11.5), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Учебный проект: стилист собирает и редактирует образы из вещей пользователя. КТ-2 проверяет поиск и ответы по карточкам демо-капсулы."
    p.font.name = FONT_SANS
    p.font.size = Pt(15.5)
    p.font.color.rgb = TEXT_LIGHT_MUTED

    badges = [
        ("ТЕХНОЛОГИЯ", "RAG + Chroma + Qwen"),
        ("ФОКУС", "Личный гардероб"),
        ("ДЕМО-КАПСУЛА", "50 вещей"),
        ("ПРИМЕР ЭСТЕТИКИ", "12 STOREEZ Capsule")
    ]
    card_w = Inches(2.7)
    card_gap = Inches(0.3)
    for i, (b_title, b_sub) in enumerate(badges):
        bx = Inches(0.8) + i * (card_w + card_gap)
        by = Inches(5.8)
        add_card(s1, bx, by, card_w, Inches(1.05), DARK_CARD_ALT, ACCENT_GOLD)
        
        t_box = s1.shapes.add_textbox(bx + Inches(0.18), by + Inches(0.16), card_w - Inches(0.36), Inches(0.75))
        t_frame = t_box.text_frame
        t_frame.word_wrap = True
        p1 = t_frame.paragraphs[0]
        p1.text = b_title
        p1.font.name = FONT_SANS
        p1.font.size = Pt(9)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_GOLD
        
        p2 = t_frame.add_paragraph()
        p2.text = b_sub
        p2.font.name = FONT_FAMILY
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_LIGHT

    # ==========================================
    # SLIDE 2: ПРОБЛЕМАТИКА РЫНКА (The Problem)
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2, BG_CREAM)
    add_header(s2, "Контекст & Боль клиента", "Парадокс гардероба: «Полный шкаф, а надеть нечего»")

    prob_data = [
        ("Шкаф", "вещи теряются из виду",
         "В большом гардеробе легко забыть о части вещей.",
         ["О вещах забывают на дальних полках", "Сложно подобрать сочетания фактур и цветов", "Непонятно, с чем носить акцентные вещи"]),
        ("Выбор", "сложно собирать новые образы",
         "Повод и погода меняются, а выбор приходится делать заново.",
         ["Долгие примерки перед выходом", "В спешке выбираются привычные комплекты", "Сложно сохранить удачное сочетание"]),
        ("Покупки", "новые вещи не всегда дополняют шкаф",
         "Каталог магазина не знает, что уже есть у пользователя.",
         ["Новая вещь не сочетается с имеющимися", "Покупка не решает задачу выбора образа", "Полезно сначала увидеть сочетания из своих вещей"])
    ]

    card_w = Inches(3.7)
    card_gap = Inches(0.3)
    for i, (stat, title, subtitle, bullets) in enumerate(prob_data):
        cx = Inches(0.8) + i * (card_w + card_gap)
        cy = Inches(1.9)
        add_card(s2, cx, cy, card_w, Inches(4.8), CARD_BG, LINE_COLOR)
        
        tbox = s2.shapes.add_textbox(cx + Inches(0.3), cy + Inches(0.3), card_w - Inches(0.6), Inches(4.2))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = stat
        p.font.name = FONT_FAMILY
        p.font.size = Pt(40)
        p.font.bold = True
        p.font.color.rgb = ACCENT_ROSE
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(8)
        p2.text = title
        p2.font.name = FONT_SANS
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        
        p3 = tf.add_paragraph()
        p3.space_before = Pt(10)
        p3.text = subtitle
        p3.font.name = FONT_SANS
        p3.font.size = Pt(12)
        p3.font.color.rgb = TEXT_MUTED

        for b in bullets:
            pb = tf.add_paragraph()
            pb.space_before = Pt(8)
            pb.text = "• " + b
            pb.font.name = FONT_SANS
            pb.font.size = Pt(11.5)
            pb.font.color.rgb = TEXT_DARK

    # ==========================================
    # SLIDE 3: НАШЕ РЕШЕНИЕ (Value Proposition)
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3, BG_CREAM)
    add_header(s3, "Продуктовое решение", "CLOSET.AI — карманный куратор личного стиля")

    sol_cards = [
        ("Цифровой гардероб",
         "Личный гардероб структурируется по тканям (шелк, кашемир, лен), оттенкам, теплоте и крою.",
         "Клиент видит вещи в чистом цифровом лукбуке высокой эстетики."),
        ("Интеллектуальный RAG-подбор под повод", 
         "ИИ комбинирует только РЕАЛЬНЫЕ вещи пользователя с учетом текущей погоды (+6°C, пасмурно) и повода.",
         "Никаких абстрактных картинок — только носибельные комплекты."),
        ("Профессиональное fashion-обоснование", 
         "Стилист не просто выдает вещи, а учит: объясняет баланс фактур (кашемир + шелк) и вертикаль силуэта.",
         "Клиент получает персональные лайфхаки по стайлингу и посадке."),
        ("Точечная правка образа",
         "Пользователь просит заменить одну вещь и видит обновлённую карточку.",
         "Остальные вещи сохраняются, если их не просили менять.")
    ]

    for i, (title, line1, line2) in enumerate(sol_cards):
        row = i // 2
        col = i % 2
        cx = Inches(0.8) + col * Inches(5.95)
        cy = Inches(1.9) + row * Inches(2.45)
        add_card(s3, cx, cy, Inches(5.65), Inches(2.25), CARD_BG, LINE_COLOR)
        
        tbox = s3.shapes.add_textbox(cx + Inches(0.35), cy + Inches(0.25), Inches(4.95), Inches(1.8))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p0 = tf.paragraphs[0]
        p0.text = f"ПРЕИМУЩЕСТВО 0{i+1}"
        p0.font.name = FONT_SANS
        p0.font.size = Pt(10)
        p0.font.bold = True
        p0.font.color.rgb = ACCENT_GOLD
        
        p1 = tf.add_paragraph()
        p1.space_before = Pt(4)
        p1.text = title
        p1.font.name = FONT_FAMILY
        p1.font.size = Pt(18)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_DARK
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(6)
        p2.text = "• " + line1
        p2.font.name = FONT_SANS
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_MUTED

        p3 = tf.add_paragraph()
        p3.space_before = Pt(4)
        p3.text = "• " + line2
        p3.font.name = FONT_SANS
        p3.font.size = Pt(12)
        p3.font.color.rgb = TEXT_MUTED

    # ==========================================
    # SLIDE 4: АРХИТЕКТУРА И ТЕХНОЛОГИИ (Tech & RAG)
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4, DARK_CARD)
    add_header(s4, "Технологический стек & Архитектура", "Гибридный RAG: от векторов до модного рассуждения", dark=True)

    tech_steps = [
        ("01. Клиентский ввод", "React 19 + Vite 8", [
            "Запрос на естественном языке",
            "Учет контекста погоды и повода",
            "Потоковый вывод в чате",
            "История диалогов"
        ]),
        ("02. Гибридный поиск", "BM25 + Dense / Chroma", [
            "Текстовый поиск и эмбеддинги",
            "CLIP для визуального поиска",
            "Кандидаты по категориям",
            "Фильтры по поводу и погоде"
        ]),
        ("03. Выбор вещей", "FastAPI + локальная Qwen", [
            "Модель выбирает ID кандидатов",
            "Сервер проверяет состав образа",
            "Неполный комплект не показывается",
            "Потоковый ответ SSE"
        ]),
        ("04. Карточка образа", "React + история чата", [
            "Комплект из вещей гардероба",
            "Объяснение выбора",
            "Сохранение в Лукбук",
            "Точечная замена вещей"
        ])
    ]

    for i, (step_num, badge, points) in enumerate(tech_steps):
        cx = Inches(0.8) + i * Inches(2.95)
        cy = Inches(1.9)
        add_card(s4, cx, cy, Inches(2.75), Inches(4.8), DARK_CARD_ALT, ACCENT_GOLD)
        
        tbox = s4.shapes.add_textbox(cx + Inches(0.22), cy + Inches(0.3), Inches(2.3), Inches(4.2))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = step_num
        p.font.name = FONT_FAMILY
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_GOLD
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(8)
        p2.text = badge
        p2.font.name = FONT_SANS
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_LIGHT
        
        for pt in points:
            pb = tf.add_paragraph()
            pb.space_before = Pt(10)
            pb.text = "• " + pt
            pb.font.name = FONT_SANS
            pb.font.size = Pt(11.5)
            pb.font.color.rgb = TEXT_LIGHT_MUTED

    # ==========================================
    # SLIDE 5: ИНТЕРФЕЙС И ПОЛЬЗОВАТЕЛЬСКИЙ ОПЫТ (UI/UX)
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5, BG_CREAM)
    add_header(s5, "Интерфейс и пользовательский опыт", "Премиальная эстетика тихой роскоши (Quiet Luxury)")

    features = [
        ("Чат со стилистом", "Подбор под повод и погоду, история диалогов и подсказки для правки последней карточки."),
        ("Гардероб", "Свои вещи и демо-капсула из 50 позиций. Фильтры по категориям, подкатегориям и стилю."),
        ("Карточки образов", "Проверенный состав комплекта, комментарий стилиста и сохранение в Лукбук."),
        ("Адаптивность и мобильный комфорт", "Полноценный адаптив под смартфоны (100dvh), поддержка темной и светлой темы, плавные микроанимации.")
    ]

    for i, (ft, fd) in enumerate(features):
        cy = Inches(1.9) + i * Inches(1.25)
        add_card(s5, Inches(0.8), cy, Inches(6.6), Inches(1.12), CARD_BG, LINE_COLOR)
        
        tbox = s5.shapes.add_textbox(Inches(1.05), cy + Inches(0.12), Inches(6.15), Inches(0.9))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p1 = tf.paragraphs[0]
        p1.text = ft
        p1.font.name = FONT_FAMILY
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_DARK
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(3)
        p2.text = fd
        p2.font.name = FONT_SANS
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_MUTED

    # Right Card: Demo of the actual Look Card inside the app
    right_cx = Inches(7.7)
    right_cy = Inches(1.9)
    add_card(s5, right_cx, right_cy, Inches(4.8), Inches(4.9), DARK_CARD, None)

    sim_box = s5.shapes.add_textbox(right_cx + Inches(0.35), right_cy + Inches(0.35), Inches(4.1), Inches(4.3))
    stf = sim_box.text_frame
    stf.word_wrap = True

    sp0 = stf.paragraphs[0]
    sp0.text = "ПРИМЕР ИЗ ПРОВЕРКИ В БРАУЗЕРЕ"
    sp0.font.name = FONT_SANS
    sp0.font.size = Pt(10)
    sp0.font.bold = True
    sp0.font.color.rgb = ACCENT_GOLD

    sp1 = stf.add_paragraph()
    sp1.space_before = Pt(6)
    sp1.text = "Образ · Деловой выход"
    sp1.font.name = FONT_FAMILY
    sp1.font.size = Pt(19)
    sp1.font.bold = True
    sp1.font.color.rgb = TEXT_LIGHT

    sp2 = stf.add_paragraph()
    sp2.space_before = Pt(4)
    sp2.text = "Повод: деловая встреча в офисе"
    sp2.font.name = FONT_SANS
    sp2.font.size = Pt(11.5)
    sp2.font.bold = True
    sp2.font.color.rgb = ACCENT_ROSE

    sp3 = stf.add_paragraph()
    sp3.space_before = Pt(12)
    sp3.text = "Карточка из демо-капсулы:\n• Молочная блуза с воротником-бантом\n• Графитовая юбка-карандаш\n• Бордовые дерби на низком каблуке"
    sp3.font.name = FONT_SANS
    sp3.font.size = Pt(11.5)
    sp3.font.color.rgb = TEXT_LIGHT

    sp4 = stf.add_paragraph()
    sp4.space_before = Pt(12)
    sp4.text = "После «Замени обувь, остальное оставь»:\nдерби сменились на чёрные лодочки, блуза и юбка остались."
    sp4.font.name = FONT_FAMILY
    sp4.font.size = Pt(11)
    sp4.font.italic = True
    sp4.font.color.rgb = TEXT_LIGHT_MUTED

    # Slide 6: КТ-2 benchmark. Figures are from capsule_generation_run/summary.json.
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6, BG_CREAM)
    add_header(s6, "КТ-2 · Бенчмарк при k=3", "Поиск и ответы по капсуле Лукбука")

    def metric_text(x, y, w, h, text, size, color=TEXT_DARK, bold=False):
        box = s6.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        p = frame.paragraphs[0]
        p.text = text
        p.font.name = FONT_SANS
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color

    metric_text(0.8, 1.65, 11.7, 0.5, "30 карточек из капсулы · 10 обычных вопросов · 5 ловушек", 16, TEXT_MUTED)
    for i, (label, value, detail) in enumerate([
        ("Recall@3", "100%", "30 из 30 релевантных карточек"),
        ("MRR@3", "1,00", "Первый нужный результат — №1"),
        ("Автозачёт", "9/10", "Эвристическая проверка ответов"),
        ("Корректные отказы", "5/5", "Модель не угадывает свойства"),
    ]):
        x = 0.8 + i * 2.95
        add_card(s6, Inches(x), Inches(2.35), Inches(2.75), Inches(1.8))
        metric_text(x + 0.2, 2.53, 2.35, 0.32, label, 13, TEXT_MUTED, True)
        metric_text(x + 0.2, 2.91, 2.35, 0.55, value, 30, ACCENT_ROSE, True)
        metric_text(x + 0.2, 3.56, 2.35, 0.48, detail, 11)

    metric_text(0.8, 4.5, 11.7, 0.5, "Вопрос → собственный индекс BM25 → до 3 карточек → Qwen → ответ со ссылками или отказ", 16, TEXT_DARK, True)
    metric_text(0.8, 5.14, 11.7, 0.7, "Пример ошибки Q01: автооценка не засчитала «лён и хлопок» вместо «льна с хлопком». По смыслу ответ верен.", 14, TEXT_MUTED)
    metric_text(0.8, 6.12, 11.7, 0.55, "Метрики относятся к стенду /kt2. Сборку и правку образа в основном чате проверяем отдельно.", 13, TEXT_MUTED)

    # ==========================================
    # SLIDE 7: ДОРОЖНАЯ КАРТА И СТАТУС (Roadmap)
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7, BG_CREAM)
    add_header(s7, "Текущий прогресс", "От автономного интерфейса к работающему стилисту")

    stages = [
        ("КТ-1 (ВЫПОЛНЕНО)", "Фронтенд & Спецификация", [
            "Полный React 19 интерфейс",
            "Дизайн-система Quiet Luxury",
            "Модельный контракт API",
            "Локальный лукбук и SVG-вещи",
            "История диалогов и сессий"
        ], True),
        ("КТ-2 (ГОТОВО К ПОКАЗУ)", "RAG и серверная интеграция", [
            "FastAPI и потоковые ответы SSE",
            "Chroma, BM25, Dense и CLIP",
            "Локальная Qwen в Лукбуке",
            "Свой BM25-индекс на стенде",
            "Бенчмарк на карточках капсулы"
        ], True),
        ("КТ-3 (ПЛАН ЗАПУСКА)", "Бизнес-интеграция & Upsell", [
            "1-Click дополнение корзины",
            "Интеграция с каталогом магазина",
            "Импорт чеков из истории заказов",
            "Экспорт готового лука в PDF/TG",
            "A/B тестирование рекомендаций"
        ], False)
    ]

    card_w = Inches(3.7)
    card_gap = Inches(0.3)
    for i, (status, title, bullets, is_done) in enumerate(stages):
        cx = Inches(0.8) + i * (card_w + card_gap)
        cy = Inches(1.9)
        bg_col = CARD_BG if not is_done else CARD_BG_ALT
        bdr_col = ACCENT_GOLD if is_done else LINE_COLOR
        add_card(s7, cx, cy, card_w, Inches(4.8), bg_col, bdr_col)
        
        tbox = s7.shapes.add_textbox(cx + Inches(0.25), cy + Inches(0.3), card_w - Inches(0.5), Inches(4.2))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = status
        p.font.name = FONT_SANS
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_GREEN if is_done else ACCENT_GOLD
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(8)
        p2.text = title
        p2.font.name = FONT_FAMILY
        p2.font.size = Pt(17)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        
        for b in bullets:
            pb = tf.add_paragraph()
            pb.space_before = Pt(10)
            prefix = "✔  " if is_done else "•  "
            pb.text = prefix + b
            pb.font.name = FONT_SANS
            pb.font.size = Pt(12)
            pb.font.color.rgb = TEXT_DARK if is_done else TEXT_MUTED

    # ==========================================
    # SLIDE 8: ФИНАЛЬНЫЙ СЛАЙД / ПРИЗЫВ К ДЕЙСТВИЮ (Call to Action / Pitch)
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8, DARK_CARD)

    top_line = s8.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.0), Inches(1.5), Inches(0.04))
    top_line.fill.solid()
    top_line.fill.fore_color.rgb = ACCENT_GOLD
    top_line.line.fill.background()

    tb = s8.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(10), Inches(0.4))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "РЕЗЮМЕ & ДЕМОНСТРАЦИЯ"
    p.font.name = FONT_SANS
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GOLD

    tb = s8.shapes.add_textbox(Inches(0.8), Inches(1.7), Inches(11.5), Inches(1.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Два сценария на одной капсуле"
    p.font.name = FONT_FAMILY
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = TEXT_LIGHT

    pitch_pillars = [
        ("Лукбук", "Собрать офисный образ. Заменить только обувь, сохранив верх и низ."),
        ("Стенд КТ-2", "Сравнить джинсы и палаццо. Показать карточки и ссылки в ответе."),
        ("Честный отказ", "Спросить точную высоту каблука. Карточка есть, точного числа нет.")
    ]

    for i, (head, sub) in enumerate(pitch_pillars):
        px = Inches(0.8) + i * Inches(3.9)
        py = Inches(3.8)
        add_card(s8, px, py, Inches(3.6), Inches(1.8), DARK_CARD_ALT, ACCENT_GOLD)
        
        tbox = s8.shapes.add_textbox(px + Inches(0.2), py + Inches(0.2), Inches(3.2), Inches(1.4))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p1 = tf.paragraphs[0]
        p1.text = head
        p1.font.name = FONT_FAMILY
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_LIGHT
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(8)
        p2.text = sub
        p2.font.name = FONT_SANS
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_LIGHT_MUTED

    # Bottom Contact & Demo Bar
    add_card(s8, Inches(0.8), Inches(5.9), Inches(11.7), Inches(0.9), RGBColor(45, 40, 36), None)
    demo_tb = s8.shapes.add_textbox(Inches(1.1), Inches(6.05), Inches(11.1), Inches(0.6))
    dtf = demo_tb.text_frame
    dp = dtf.paragraphs[0]
    dp.text = "Лукбук: localhost:5173  ·  КТ-2: localhost:8012/kt2  ·  Ходина А. · Рыбин М. · Баринов Е."
    dp.font.name = FONT_SANS
    dp.font.size = Pt(12.5)
    dp.font.bold = True
    dp.font.color.rgb = ACCENT_GOLD

    output_path = "AI_Stylist_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation updated at {output_path}")

if __name__ == "__main__":
    create_deck()
