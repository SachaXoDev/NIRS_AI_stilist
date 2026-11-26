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
    p.text = "Интеллектуальная система подбора капсульных образов на базе RAG и мультимодального поиска. Раскрывает ценность личного гардероба клиента и многократно повышает LTV премиального fashion-ритейла."
    p.font.name = FONT_SANS
    p.font.size = Pt(15.5)
    p.font.color.rgb = TEXT_LIGHT_MUTED

    badges = [
        ("ТЕХНОЛОГИЯ", "RAG + Fashion CLIP + LLM"),
        ("ФОКУС", "Личный гардероб + Cross-sell"),
        ("РЕЗУЛЬТАТ", "Готовый образ за < 3 секунды"),
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
        ("70%", "вещей висят без дела в гардеробе", 
         "В среднем до 70% гардероба человека простаивает годами.",
         ["О вещах забывают на дальних полках", "Сложно подобрать сочетания фактур и цветов", "Непонятно, с чем носить акцентные вещи"]),
        ("20 мин", "ежедневного стресса утреннего выбора", 
         "Ежедневная потеря времени и эмоциональное утомление.",
         ["Долгие примерки перед зеркалом перед работой", "В спешке выбираются одни и те же 2-3 комплекта", "Ощущение неудовлетворенности своим внешним видом"]),
        ("1.8x", "импульсивных покупок-однодневок", 
         "E-commerce навязывает вещи, не зная шкафа клиента.",
         ["Новая вещь не сочетается ни с чем в шкафу", "Деньги потрачены, а проблема выбора не решена", "Высокий процент возвратов и выгорание от шопинга"])
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
        ("Оцифровка шкафа за 2 минуты", 
         "Личный гардероб структурируется по тканям (шелк, кашемир, лен), оттенкам, теплоте и крою.",
         "Клиент видит вещи в чистом цифровом лукбуке высокой эстетики."),
        ("Интеллектуальный RAG-подбор под повод", 
         "ИИ комбинирует только РЕАЛЬНЫЕ вещи пользователя с учетом текущей погоды (+6°C, пасмурно) и повода.",
         "Никаких абстрактных картинок — только носибельные комплекты."),
        ("Профессиональное fashion-обоснование", 
         "Стилист не просто выдает вещи, а учит: объясняет баланс фактур (кашемир + шелк) и вертикаль силуэта.",
         "Клиент получает персональные лайфхаки по стайлингу и посадке."),
        ("Деликатный и точный Upsell бренда", 
         "ИИ вычисляет, какой единой вещи не хватает для открытия 5 новых свежих комбинаций.",
         "Предлагает органичную покупку у бренда-партнера с аргументацией пользы.")
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
            "Оптимистичный UI & Streaming",
            "Автономная работа без зависаний"
        ]),
        ("02. Гибридный поиск", "BM25 + Fashion-CLIP", [
            "Семантический и точный поиск",
            "Эмбеддинги фактур и фасонов",
            "Фильтрация по категориям вещей",
            "Быстрый скоринг совпадения"
        ]),
        ("03. Стилистический RAG", "Qdrant / База правил", [
            "Правило 60-30-10 в колористике",
            "Температурный фильтр слоев",
            "Баланс пропорций (объем / прилегание)",
            "Исключение стилевых конфликтов"
        ]),
        ("04. Генерация образа", "LLM Reasoning (JSON)", [
            "Формирование капсулы из шкафа",
            "Коэффициент совпадения (97%)",
            "Модное объяснение и лайфхаки",
            "Cross-sell рекомендация вещи бренда"
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
        ("Чат-ассистент как личный консьерж", "Мгновенные сценарии («Москва сегодня», «Деловая встреча»), история диалогов с умными названиями, индикация размышления стилиста."),
        ("Интерактивный лукбук гардероба", "Сетка оцифрованных вещей, фильтры по тканям (шелк, шерсть, лен), быстрый анализ «С чем носить в моем шкафу?»."),
        ("Карточки образов с высокой конверсией", "Показ сочетаемости в процентах, объяснение драпировки и посадки, кнопка сохранения в лукбук."),
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
    sp0.text = "РЕЗУЛЬТАТ РАБОТЫ АЛГОРИТМА"
    sp0.font.name = FONT_SANS
    sp0.font.size = Pt(10)
    sp0.font.bold = True
    sp0.font.color.rgb = ACCENT_GOLD

    sp1 = stf.add_paragraph()
    sp1.space_before = Pt(6)
    sp1.text = "Образ: «Деловой Минимализм»"
    sp1.font.name = FONT_FAMILY
    sp1.font.size = Pt(19)
    sp1.font.bold = True
    sp1.font.color.rgb = TEXT_LIGHT

    sp2 = stf.add_paragraph()
    sp2.space_before = Pt(4)
    sp2.text = "Совпадение со стилем: 97%  |  Повод: Переговоры"
    sp2.font.name = FONT_SANS
    sp2.font.size = Pt(11.5)
    sp2.font.bold = True
    sp2.font.color.rgb = ACCENT_ROSE

    sp3 = stf.add_paragraph()
    sp3.space_before = Pt(12)
    sp3.text = "Вещи из гардероба пользователя:\n• Двубортный шерстяной блейзер (эспрессо)\n• Шелковая рубашка прямого кроя (молочный)\n• Брюки палаццо из тонкой шерсти\n• Кожаные лоферы на тонкой подошве"
    sp3.font.name = FONT_SANS
    sp3.font.size = Pt(11.5)
    sp3.font.color.rgb = TEXT_LIGHT

    sp4 = stf.add_paragraph()
    sp4.space_before = Pt(12)
    sp4.text = "Модное обоснование стилиста:\n«Вертикаль светлой шелковой рубашки визуально вытягивает силуэт, а плотная шерсть блейзера держит четкую линию плеча.»"
    sp4.font.name = FONT_FAMILY
    sp4.font.size = Pt(11)
    sp4.font.italic = True
    sp4.font.color.rgb = TEXT_LIGHT_MUTED

    # ==========================================
    # SLIDE 6: ПОЧЕМУ КЛИЕНТЫ И РИТЕЙЛ ВЫБИРАЮТ НАС (Why Us / B2B & B2C)
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6, BG_CREAM)
    add_header(s6, "Ценность для бизнеса & Клиента", "Win-Win модель: лояльность покупателя и рост выручки")

    # Column 1: For Customer
    add_card(s6, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.8), CARD_BG, LINE_COLOR)
    c1_box = s6.shapes.add_textbox(Inches(1.15), Inches(2.15), Inches(4.95), Inches(4.3))
    c1_tf = c1_box.text_frame
    c1_tf.word_wrap = True

    cp0 = c1_tf.paragraphs[0]
    cp0.text = "ДЛЯ КЛИЕНТА (B2C)"
    cp0.font.name = FONT_SANS
    cp0.font.size = Pt(11)
    cp0.font.bold = True
    cp0.font.color.rgb = ACCENT_ROSE

    cp1 = c1_tf.add_paragraph()
    cp1.space_before = Pt(6)
    cp1.text = "Уверенность в каждом выходе"
    cp1.font.name = FONT_FAMILY
    cp1.font.size = Pt(20)
    cp1.font.bold = True
    cp1.font.color.rgb = TEXT_DARK

    b2c_items = [
        ("Экономия 20 минут каждое утро", "Без сомнений и переодеваний перед выходом из дома."),
        ("Утилизация гардероба с 30% до 80%", "Второе дыхание забытых вещей на дальних полках."),
        ("Персональный стилист 24/7", "Советы экспертного уровня по колористике и фактурам бесплатно."),
        ("Осознанное потребление", "Понимание, какие именно вещи действительно нужны гардеробу.")
    ]
    for b_title, b_sub in b2c_items:
        p = c1_tf.add_paragraph()
        p.space_before = Pt(10)
        p.text = "✔  " + b_title
        p.font.name = FONT_SANS
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        p_sub = c1_tf.add_paragraph()
        p_sub.text = "     " + b_sub
        p_sub.font.name = FONT_SANS
        p_sub.font.size = Pt(11.5)
        p_sub.font.color.rgb = TEXT_MUTED

    # Column 2: For Retailers
    add_card(s6, Inches(6.85), Inches(1.9), Inches(5.65), Inches(4.8), CARD_BG, LINE_COLOR)
    c2_box = s6.shapes.add_textbox(Inches(7.2), Inches(2.15), Inches(4.95), Inches(4.3))
    c2_tf = c2_box.text_frame
    c2_tf.word_wrap = True

    bp0 = c2_tf.paragraphs[0]
    bp0.text = "ДЛЯ БРЕНДА И РИТЕЙЛА (B2B)"
    bp0.font.name = FONT_SANS
    bp0.font.size = Pt(11)
    bp0.font.bold = True
    bp0.font.color.rgb = ACCENT_GOLD

    bp1 = c2_tf.add_paragraph()
    bp1.space_before = Pt(6)
    bp1.text = "Рост LTV и точечный Cross-Sell"
    bp1.font.name = FONT_FAMILY
    bp1.font.size = Pt(20)
    bp1.font.bold = True
    bp1.font.color.rgb = TEXT_DARK

    b2b_items = [
        ("+35% к конверсии повторных покупок", "Рекомендация именно той вещи, которая дополнит шкаф."),
        ("Снижение возвратов на 28%", "Покупатель заранее понимает, с чем и куда будет носить вещь."),
        ("Глубокая аналитика гардеробов", "Бренд видит реальные потребности и дефициты в гардеробах ЦА."),
        ("Рост эмоциональной лояльности", "Бренд выступает заботливым советчиком, а не просто витриной.")
    ]
    for b_title, b_sub in b2b_items:
        p = c2_tf.add_paragraph()
        p.space_before = Pt(10)
        p.text = "★  " + b_title
        p.font.name = FONT_SANS
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        
        p_sub = c2_tf.add_paragraph()
        p_sub.text = "     " + b_sub
        p_sub.font.name = FONT_SANS
        p_sub.font.size = Pt(11.5)
        p_sub.font.color.rgb = TEXT_MUTED

    # ==========================================
    # SLIDE 7: ДОРОЖНАЯ КАРТА И СТАТУС (Roadmap)
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7, BG_CREAM)
    add_header(s7, "План реализации & Текущий прогресс", "От автономного прототипа к enterprise-платформе")

    stages = [
        ("КТ-1 (ВЫПОЛНЕНО)", "Фронтенд & Спецификация", [
            "Полный React 19 интерфейс",
            "Дизайн-система Quiet Luxury",
            "Модельный контракт API",
            "Локальный лукбук и SVG-вещи",
            "История диалогов и сессий"
        ], True),
        ("КТ-2 (В РАЗРАБОТКЕ)", "RAG & Серверный конвейер", [
            "FastAPI микросервис инференса",
            "Векторная база данных Qdrant",
            "Мультимодальный Fashion-CLIP",
            "Стилистический LLM промптинг",
            "Streaming SSE генерации лука"
        ], False),
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
    p.text = "Будущее персонального ритейла уже работает в вашем браузере"
    p.font.name = FONT_FAMILY
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = TEXT_LIGHT

    pitch_pillars = [
        ("Продукт готов к пилоту", "Работающий фронтенд, валидированные сценарии и архитектурный контракт с бэкендом."),
        ("Высокая маржинальность", "Низкая себестоимость инференса благодаря гибридному BM25/Vector ретриверу."),
        ("Безупречный бренд-fit", "Эстетика 12 STOREEZ: забота о клиенте, премиальность и устойчивое потребление.")
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
    dp.text = "⚡ Демонстрация прямо сейчас: http://localhost:5173/   |   Команда проекта: Ходина А. • Рыбин М. • Баринов Е."
    dp.font.name = FONT_SANS
    dp.font.size = Pt(12.5)
    dp.font.bold = True
    dp.font.color.rgb = ACCENT_GOLD

    output_path = "AI_Stylist_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation updated at {output_path}")

if __name__ == "__main__":
    create_deck()
