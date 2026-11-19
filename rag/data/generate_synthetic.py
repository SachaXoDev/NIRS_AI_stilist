"""Rebuild transparent synthetic fixtures without model access or retrieval results.

The original frontend ten items are copied unchanged from wardrobe_seed.json.
Extra items are imaginary annotations; SVGs are category illustration surrogates.
Relevance labels were declared from the item descriptions, never model rankings.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def dump(name: str, value: object) -> None:
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def item(identifier: str, title: str, category: str, color: str, material: str,
         tags: list[str], style: list[str], image: str, season: str = 'all',
         weather: dict | None = None) -> dict:
    result = dict(id=identifier, title=title, category=category, color=color,
                  material=material, season=season, tags=tags, style=style,
                  imageUrl=f'/clothes/{image}.svg', brand='Synthetic Study',
                  uploadedAt='2026-11-19',
                  embeddingSnippet=f'{title}. Материал: {material}. ' + ', '.join(tags) + '.')
    if weather is not None:
        result['weather'] = weather
    return result


def query(identifier: str, text: str, tops: list[str], bottoms: list[str], shoes: list[str],
          rationale: str, **extra: object) -> dict:
    return dict(id=identifier, query=text,
                relevant_by_slot=dict(tops=tops, bottoms=bottoms, shoes=shoes),
                rationale=rationale, **extra)


def main() -> None:
    seed = json.loads((HERE / 'wardrobe_seed.json').read_text(encoding='utf-8'))
    extra = [
        item('t01', 'Черный шелковый топ на тонких бретелях', 'tops', 'Черный', '100% шелк', ['топ', 'вечер', 'шелк', 'струящийся'], ['evening', 'chic'], 'shirt'),
        item('t02', 'Темно-синяя приталенная рубашка из поплина', 'tops', 'Темно-синий', '100% хлопок поплин', ['рубашка', 'офис', 'деловая', 'приталенная'], ['business'], 'shirt'),
        item('t03', 'Бордовая водолазка из мериносовой шерсти', 'tops', 'Бордовый', '100% мериносовая шерсть', ['водолазка', 'теплый', 'офис', 'тонкий трикотаж'], ['business', 'cozy'], 'sweater', 'autumn/winter', {'temperature_min': -5, 'temperature_max': 15}),
        item('t04', 'Серый объемный свитер крупной вязки', 'tops', 'Серый', 'Плотная овечья шерсть', ['свитер', 'теплый', 'прогулка', 'объемный'], ['casual', 'cozy'], 'sweater', 'autumn/winter', {'temperature_min': -10, 'temperature_max': 12}),
        item('t05', 'Бежевая свободная льняная рубашка', 'tops', 'Бежевый', '100% лен', ['рубашка', 'лето', 'жара', 'дышащая'], ['casual', 'minimalism'], 'shirt', 'spring/summer', {'temperature_min': 18, 'temperature_max': 35}),
        item('t06', 'Белая базовая хлопковая футболка', 'tops', 'Белый', '100% хлопок', ['футболка', 'лето', 'повседневная', 'базовая'], ['casual', 'minimalism'], 'shirt', 'spring/summer'),
        item('t07', 'Оливковая функциональная флисовая кофта', 'tops', 'Оливковый', 'Технический флис', ['флис', 'поход', 'трекинг', 'теплый', 'быстросохнущий'], ['outdoor', 'sport'], 'sweater', 'autumn/winter'),
        item('t08', 'Красный шерстяной свитер крупной вязки', 'tops', 'Красный', '100% шерсть', ['свитер', 'акцент', 'яркий', 'мороз', 'теплый'], ['casual', 'accent'], 'sweater', 'autumn/winter', {'temperature_min': -10, 'temperature_max': 10}),
        item('t09', 'Голубая хлопковая рубашка в белую полоску', 'tops', 'Голубой / Белый', 'Хлопок', ['рубашка', 'полоска', 'расслабленная', 'офис'], ['smart-casual', 'casual'], 'shirt'),
        item('t10', 'Пудрово-розовая сатиновая блуза', 'tops', 'Пудрово-розовый', 'Вискозный сатин', ['блуза', 'сатин', 'вечер', 'свидание', 'мягкий блеск'], ['evening', 'chic'], 'shirt'),
        item('t11', 'Черная спортивная футболка для бега', 'tops', 'Черный', 'Быстросохнущий полиэстер', ['футболка', 'бег', 'тренировка', 'спорт', 'влагоотведение'], ['sport'], 'shirt'),
        item('t12', 'Кремовый фактурный вязаный кардиган', 'tops', 'Кремовый', 'Шерсть с хлопком', ['кардиган', 'уютный', 'фактурный', 'кофейня', 'поездка'], ['cozy', 'minimalism'], 'sweater'),
        item('t13', 'Изумрудная шелковая блуза со свободным рукавом', 'tops', 'Изумрудный', '100% шелк', ['блуза', 'вечер', 'галерея', 'акцент', 'шелк'], ['evening', 'chic'], 'shirt'),
        item('b01', 'Черные прямые костюмные брюки из шерсти', 'bottoms', 'Черный', 'Костюмная шерсть', ['брюки', 'офис', 'деловые', 'прямые'], ['business', 'minimalism'], 'palazzo'),
        item('b02', 'Бежевые широкие льняные брюки', 'bottoms', 'Бежевый', '100% лен', ['брюки', 'лето', 'жара', 'широкие', 'дышащие'], ['casual', 'minimalism'], 'palazzo', 'spring/summer', {'temperature_min': 18, 'temperature_max': 35}),
        item('b03', 'Черная шелковая юбка миди по косой', 'bottoms', 'Черный', '100% шелк', ['юбка', 'миди', 'вечер', 'струящаяся', 'свидание'], ['evening', 'chic'], 'palazzo'),
        item('b04', 'Оливковые хлопковые брюки карго для похода', 'bottoms', 'Оливковый', 'Плотный хлопок рипстоп', ['карго', 'поход', 'трекинг', 'карманы', 'прочные'], ['outdoor'], 'jeans'),
        item('b05', 'Узкие джинсы цвета индиго', 'bottoms', 'Индиго', 'Деним с эластаном', ['джинсы', 'деним', 'узкие', 'повседневные'], ['casual'], 'jeans'),
        item('b06', 'Темно-синие костюмные брюки со стрелками', 'bottoms', 'Темно-синий', 'Тонкая шерсть', ['брюки', 'стрелки', 'деловые', 'офис', 'костюм'], ['business'], 'palazzo'),
        item('b07', 'Серые теплые шерстяные брюки на подкладке', 'bottoms', 'Серый', 'Плотная шерсть на подкладке', ['брюки', 'теплый', 'зима', 'мороз', 'офис'], ['business', 'cozy'], 'palazzo', 'autumn/winter', {'temperature_min': -15, 'temperature_max': 12}),
        item('b08', 'Песочные хлопковые чиносы свободной посадки', 'bottoms', 'Песочный', 'Хлопковый твил', ['чиносы', 'брюки', 'поездка', 'комфорт', 'повседневные'], ['smart-casual', 'casual'], 'palazzo'),
        item('b09', 'Черные эластичные легинсы для бега', 'bottoms', 'Черный', 'Технический полиамид с эластаном', ['легинсы', 'бег', 'спорт', 'тренировка'], ['sport'], 'jeans'),
        item('b10', 'Белые хлопковые шорты до колена', 'bottoms', 'Белый', 'Хлопок', ['шорты', 'лето', 'жара', 'отпуск'], ['casual'], 'palazzo', 'spring/summer', {'temperature_min': 22, 'temperature_max': 38}),
        item('b11', 'Бордовые бархатные широкие брюки', 'bottoms', 'Бордовый', 'Хлопковый бархат', ['брюки', 'бархат', 'вечер', 'театр', 'праздник'], ['evening', 'chic'], 'palazzo'),
        item('b12', 'Светло-голубые широкие расслабленные джинсы', 'bottoms', 'Светло-голубой', 'Мягкий хлопковый деним', ['джинсы', 'широкие', 'светлые', 'комфорт', 'поездка'], ['casual', 'minimalism'], 'jeans'),
        item('b13', 'Коричневые вельветовые брюки прямого кроя', 'bottoms', 'Коричневый', 'Хлопковый вельвет', ['брюки', 'вельвет', 'осень', 'теплый', 'кофейня'], ['casual', 'cozy'], 'palazzo', 'autumn/winter'),
        item('s01', 'Черные кожаные ботильоны на устойчивом каблуке', 'shoes', 'Черный', 'Кожа с теплой подкладкой', ['ботильоны', 'закрытые', 'офис', 'прохлада', 'деловые'], ['business', 'chic'], 'loafers', 'autumn/winter', {'temperature_min': -3, 'temperature_max': 15, 'open_shoes': False}),
        item('s02', 'Черные замшевые лодочки на каблуке', 'shoes', 'Черный', 'Натуральная замша', ['лодочки', 'каблук', 'вечер', 'свидание', 'закрытые'], ['evening', 'chic'], 'loafers', weather={'waterproof': False, 'open_shoes': False}),
        item('s03', 'Бежевые кожаные сандалии на плоской подошве', 'shoes', 'Бежевый', 'Натуральная кожа', ['сандалии', 'открытые', 'лето', 'жара', 'комфорт'], ['casual'], 'loafers', 'spring/summer', {'temperature_min': 20, 'temperature_max': 38, 'open_shoes': True}),
        item('s04', 'Коричневые непромокаемые трекинговые ботинки', 'shoes', 'Коричневый', 'Мембрана и нубук', ['ботинки', 'поход', 'трекинг', 'дождь', 'водонепроницаемые'], ['outdoor'], 'loafers', weather={'temperature_min': -5, 'temperature_max': 20, 'waterproof': True, 'open_shoes': False}),
        item('s05', 'Черные амортизирующие кроссовки для бега', 'shoes', 'Черный', 'Дышащая техническая сетка', ['кроссовки', 'бег', 'спорт', 'тренировка', 'амортизация'], ['sport'], 'sneakers', weather={'open_shoes': False}),
        item('s06', 'Кремовые кожаные балетки с мягким носком', 'shoes', 'Кремовый', 'Мягкая кожа', ['балетки', 'элегантные', 'город', 'вечер', 'плоская подошва'], ['chic', 'minimalism'], 'loafers', weather={'temperature_min': 12, 'temperature_max': 28, 'open_shoes': False}),
        item('s07', 'Темно-синие текстильные кеды', 'shoes', 'Темно-синий', 'Хлопковый канвас', ['кеды', 'деним', 'город', 'повседневные', 'поездка'], ['casual'], 'sneakers', weather={'waterproof': False, 'open_shoes': False}),
        item('s08', 'Коричневые замшевые дезерты на низком ходу', 'shoes', 'Коричневый', 'Натуральная замша', ['дезерты', 'ботинки', 'осень', 'комфорт', 'кофейня'], ['smart-casual', 'cozy'], 'loafers', 'autumn/winter', {'waterproof': False, 'open_shoes': False}),
        item('s09', 'Черные утепленные зимние ботинки', 'shoes', 'Черный', 'Кожа с шерстяной подкладкой', ['ботинки', 'зима', 'мороз', 'теплый', 'снег'], ['casual'], 'loafers', 'autumn/winter', {'temperature_min': -25, 'temperature_max': 5, 'waterproof': True, 'open_shoes': False}),
        item('s10', 'Золотистые вечерние босоножки на тонких ремешках', 'shoes', 'Золотистый', 'Металлизированная кожа', ['босоножки', 'вечер', 'каблук', 'праздник', 'открытые'], ['evening', 'accent'], 'loafers', 'spring/summer', {'temperature_min': 20, 'temperature_max': 35, 'open_shoes': True}),
        item('s11', 'Черные кожаные дерби для деловых встреч', 'shoes', 'Черный', 'Гладкая натуральная кожа', ['дерби', 'туфли', 'офис', 'деловые', 'закрытые'], ['business', 'minimalism'], 'loafers', weather={'open_shoes': False}),
        item('s12', 'Бежевые льняные эспадрильи', 'shoes', 'Бежевый', 'Лен и джут', ['эспадрильи', 'лето', 'отпуск', 'дышащие'], ['casual'], 'sneakers', 'spring/summer', {'temperature_min': 18, 'temperature_max': 35, 'waterproof': False, 'open_shoes': False}),
        item('s13', 'Бордовые кожаные лоферы с кисточками', 'shoes', 'Бордовый', 'Гладкая кожа', ['лоферы', 'акцент', 'офис', 'город', 'преппи'], ['smart-casual', 'preppy'], 'loafers', weather={'open_shoes': False}),
        item('o01', 'Темно-синее длинное шерстяное пальто', 'outerwear', 'Темно-синий', 'Плотная шерсть', ['пальто', 'зима', 'офис', 'теплый'], ['business'], 'trench', 'autumn/winter', {'temperature_min': -10, 'temperature_max': 10, 'windproof': True}),
        item('o02', 'Оливковый непромокаемый плащ с капюшоном', 'outerwear', 'Оливковый', 'Водонепроницаемая мембрана', ['плащ', 'дождь', 'капюшон', 'поход', 'ветер'], ['outdoor'], 'trench', weather={'temperature_min': 5, 'temperature_max': 20, 'waterproof': True, 'windproof': True}),
        item('o03', 'Кремовый укороченный твидовый жакет', 'outerwear', 'Кремовый', 'Шерстяной твид', ['жакет', 'вечер', 'элегантный', 'фактурный'], ['chic'], 'blazer'),
        item('o04', 'Бежевый льняной блейзер без подкладки', 'outerwear', 'Бежевый', '100% лен', ['блейзер', 'лето', 'офис', 'легкий'], ['business', 'minimalism'], 'blazer', 'spring/summer', {'temperature_min': 18, 'temperature_max': 32}),
        item('o05', 'Черный объемный пуховик для мороза', 'outerwear', 'Черный', 'Пух и водостойкий нейлон', ['пуховик', 'мороз', 'зима', 'теплый'], ['casual'], 'trench', 'autumn/winter', {'temperature_min': -25, 'temperature_max': 3, 'waterproof': True, 'windproof': True}),
        item('o06', 'Коричневая кожаная куртка прямого кроя', 'outerwear', 'Коричневый', 'Натуральная кожа', ['куртка', 'осень', 'город', 'ветер'], ['casual'], 'blazer', 'autumn/winter', {'temperature_min': 5, 'temperature_max': 18, 'windproof': True}),
        item('o07', 'Красное шерстяное пальто с поясом', 'outerwear', 'Красный', 'Шерсть с кашемиром', ['пальто', 'акцент', 'зима', 'теплый'], ['chic', 'accent'], 'trench', 'autumn/winter', {'temperature_min': -10, 'temperature_max': 10}),
        item('o08', 'Серая легкая спортивная ветровка', 'outerwear', 'Серый', 'Технический нейлон', ['ветровка', 'бег', 'спорт', 'ветер'], ['sport'], 'blazer', weather={'temperature_min': 8, 'temperature_max': 22, 'windproof': True}),
        item('a01', 'Маленькая черная вечерняя сумка', 'accessories', 'Черный', 'Гладкая кожа', ['сумка', 'вечер', 'компактная'], ['evening'], 'tote'),
        item('a02', 'Серый объемный шерстяной шарф', 'accessories', 'Серый', '100% шерсть', ['шарф', 'зима', 'теплый'], ['cozy'], 'scarf', 'autumn/winter'),
        item('a03', 'Бежевая плетеная соломенная сумка', 'accessories', 'Бежевый', 'Натуральная солома', ['сумка', 'лето', 'отпуск'], ['casual'], 'tote', 'spring/summer'),
    ]
    corpus = seed + extra
    dump('wardrobe_eval.json', corpus)
    provenance = dict(kind='synthetic_pilot', annotation_status='assistant_draft_requires_independent_team_review',
                      created='2026-11-19', corpus='wardrobe_eval.json', corpus_items=len(corpus),
                      source_seed='wardrobe_seed.json (10 frontend items unchanged)',
                      synthetic_extra_items=len(extra), images='Existing category SVG surrogates; text-only benchmark, not photographic evidence.',
                      label_policy='Declared from descriptions before observing rankings. Several compatible IDs per required slot.',
                      alpha_policy='Predeclared 0.65. Test labels must not be used to choose alpha.',
                      independence='Draft scenarios are not an independently annotated external benchmark.')
    tests = [
        query('q01', 'Москва: +6°C, ветрено, деловая встреча. Нужен теплый аккуратный многослойный образ.', ['item-5', 't03'], ['item-4', 'b01', 'b06', 'b07'], ['item-8', 's01', 's11'], 'Теплый трикотаж, деловой низ и закрытая деловая обувь.', context={'temperature_c': 6, 'wind': True, 'occasion': 'business'}),
        query('q02', 'Вечернее открытие выставки в галерее: выразительная фактура и элегантность.', ['t01', 't10', 't13'], ['b03', 'b11', 'item-4'], ['s02', 's06', 'item-8'], 'Вечерние ткани и элегантные силуэты допускают несколько сочетаний.'),
        query('q03', 'На улице +28°C. Собери легкий летний образ из льна в бежевых тонах.', ['t05'], ['b02'], ['s03', 's12'], 'Точный материал и бежевый цвет; открытая летняя обувь допустима.', context={'temperature_c': 28}),
        query('q04', 'Дождливая прогулка по городу, прохладно. Хочу непромокаемую обувь и уютный верх.', ['item-5', 't04', 't12'], ['item-3', 'b13'], ['s04'], 'Требование непромокаемой обуви подтверждено синтетической разметкой ботинок.', context={'rain': True, 'temperature_c': 10}),
        query('q05', 'Собери комплект для утренней пробежки: футболка, легинсы и амортизирующая обувь.', ['t11'], ['b09'], ['s05'], 'Специализированные спортивные предметы во всех трех слотах.'),
        query('q06', 'Черный вечерний образ с шелковым топом, юбкой миди и закрытыми туфлями.', ['t01'], ['b03'], ['s02'], 'Точные типы вещей, черный цвет и закрытые лодочки.'),
        query('q07', 'Деловые переговоры: белая хлопковая рубашка, строгие брюки и кожаные туфли.', ['item-1'], ['item-4', 'b01', 'b06'], ['item-8', 's11'], 'Классический деловой набор; серые, черные и синие брюки допустимы.'),
        query('q08', 'Расслабленный выходной с денимом и кедами, без нарядности.', ['t06', 't09', 'item-1'], ['item-3', 'b05', 'b12'], ['item-7', 's07'], 'Повседневные хлопковые верхи, джинсы, кеды.'),
        query('q09', 'Уютная встреча в кофейне: мягкий кремовый трикотаж и теплые тактильные ткани.', ['item-5', 't12'], ['b13', 'b07', 'item-3'], ['s08', 's13', 'item-8'], 'Кремовый трикотаж с вельветом, шерстью или плотным денимом.'),
        query('q10', 'Поход по лесной тропе: оливковый флис, карго и надежные трекинговые ботинки.', ['t07'], ['b04'], ['s04'], 'Точные outdoor-типы вместо городских замен.'),
        query('q11', 'Светлый городской образ без черного цвета: спокойные оттенки и удобная обувь.', ['t05', 't06', 'item-5', 't12', 't09'], ['b08', 'b02', 'b12'], ['item-7', 's06', 's12'], 'Светлые нейтральные вещи; черные исключены явным фильтром.', exclude_colors=['черный']),
        query('q12', 'Хочу темно-синий деловой комплект с приталенной рубашкой и брюками со стрелками.', ['t02'], ['b06'], ['s11', 'item-8'], 'Точные цвет, тип рубашки и костюмный низ.'),
        query('q13', 'Холодный зимний день: яркий красный свитер как акцент, теплые брюки и ботинки.', ['t08'], ['b07', 'b13'], ['s09', 's01'], 'Явно красный шерстяной верх и зимние фактуры.', context={'temperature_c': 0}),
        query('q14', 'Для свидания хочу пудровую сатиновую блузу и мягкий вечерний силуэт.', ['t10'], ['b03', 'b11'], ['s02', 's06', 's10'], 'Пудровый сатин с вечерним низом и элегантной обувью.'),
        query('q15', 'В галерею: изумрудный шелк как цветовой акцент, сдержанный низ.', ['t13'], ['b03', 'b01', 'item-4'], ['s02', 'item-8', 's06'], 'Изумрудная блуза с нейтральным черным или серым низом.'),
        query('q16', 'Неформальное свидание после офиса: синяя рубашка, чиносы или темный деним.', ['t02', 't09'], ['b08', 'b06', 'b05'], ['s08', 's13', 'item-8'], 'Smart casual без спортивных и подчеркнуто праздничных предметов.'),
        query('q17', 'Собери минималистичный образ с широкими светло-голубыми джинсами.', ['t06', 'item-1', 't12'], ['b12'], ['item-7', 's07'], 'Светлый свободный деним с простым верхом и кедами.'),
        query('q18', 'Спокойная эстетика old money: сорочка или кардиган, свободные брюки, лоферы.', ['item-1', 't02', 't12'], ['item-4', 'b08', 'b06'], ['item-8', 's13'], 'Точное требование лоферов и нейтральные smart-casual вещи.'),
        query('q19', 'На улице около нуля: теплый шерстяной верх под пальто, плотные брюки и зимняя обувь.', ['t03', 't04', 't08'], ['b07', 'b13'], ['s09', 's01'], 'Шерсть и закрытая утепленная обувь; летние вещи исключаются известными диапазонами.', context={'temperature_c': 0, 'wind': True}),
        query('q20', 'Долгая поездка и аэропорт: мягкий удобный верх, свободный низ и кеды.', ['item-5', 't12', 't06'], ['b08', 'b12', 'item-3'], ['item-7', 's07'], 'Комфортный трикотаж/хлопок, свободные брюки или деним, кеды.'),
    ]
    dev = [
        query('d01', 'Оливковая одежда для трекинга по сырому лесу.', ['t07'], ['b04'], ['s04'], 'Проверка outdoor-лексики.'),
        query('d02', 'На премьеру в театр: шелковый верх и бордовый бархат.', ['t01', 't13'], ['b11'], ['s02', 's06'], 'Вечерние фактуры.'),
        query('d03', 'Отпуск у моря: дышащая рубашка и светлые летние брюки.', ['t05'], ['b02', 'b10'], ['s03', 's12'], 'Летний льняной набор.', context={'temperature_c': 27}),
        query('d04', 'Нужна строгая сорочка Arket для офиса.', ['item-1'], ['b01', 'b06', 'item-4'], ['s11', 'item-8'], 'Точное название бренда.'),
        query('d05', 'После тренировки хочу только спортивный комплект для бега.', ['t11'], ['b09'], ['s05'], 'Спортивные предметы.'),
        query('d06', 'Прогулка зимой в мягкой шерсти, без открытой обуви.', ['t03', 't04', 't08'], ['b07', 'b13'], ['s09', 's01'], 'Теплые известные диапазоны.', context={'temperature_c': -1}),
    ]
    base = dict(schema_version=1, user_id='evaluation-user', corpus='wardrobe_eval.json',
                alpha=0.65, mrr_k=3, required_slots=['tops', 'bottoms', 'shoes'],
                provenance=provenance)
    dump('queries_test.json', dict(base, split='test', queries=tests))
    dump('queries_dev.json', dict(base, split='dev', queries=dev))
    visual_text = {
        'item-1': 'Белая рубашка с длинными рукавами и воротником',
        'item-2': 'Черный строгий блейзер с лацканами',
        'item-3': 'Прямые синие джинсы',
        'item-4': 'Серые широкие брюки палаццо',
        'item-5': 'Светлый кремовый вязаный джемпер',
        'item-6': 'Длинный бежевый двубортный тренч с поясом',
        'item-7': 'Белые низкие кеды',
        'item-8': 'Черные кожаные лоферы',
        'item-9': 'Коричневая структурированная сумка с ручками',
        'item-10': 'Шелковый платок с геометрическим рисунком',
    }
    visual_queries = []
    for original in seed:
        identifier, slot = original['id'], original['category']
        visual_queries.append(dict(id=f'text-{identifier}', query=visual_text[identifier],
                                   relevant_by_slot={slot: [identifier]},
                                   rationale='Иллюстративная текст→изображение проверка по 10 исходным SVG.'))
    dump('queries_visual_text.json', dict(schema_version=1, split='visual_smoke', user_id='visual-evaluation-user',
         corpus='wardrobe_seed.json', alpha=0.65, mrr_k=3, required_slots=[],
         provenance=dict(kind='illustration_smoke', annotation_status='assistant_draft_requires_independent_team_review',
                         images='10 supplied SVG illustrations, some contain printed labels; not a clothing photo benchmark.',
                         limitations='Text-to-image category ranks have only 2 candidates. Use a global image collection if reporting nontrivial image retrieval.'),
         queries=visual_queries))
    dump('queries_visual_image.json', dict(schema_version=1, split='visual_instance_smoke', user_id='visual-evaluation-user',
         corpus='wardrobe_seed.json', alpha=0.65, mrr_k=3, required_slots=[],
         provenance=dict(kind='near_duplicate_instance_smoke', annotation_status='identity_labels',
                         images='Transformed rasterizations of original SVGs, prepared by the image pipeline.',
                         limitations='Same source item exists in the index; measures instance robustness, not unseen-photo semantic generalization.'),
         queries=[dict(id=f'image-{original["id"]}', query='', query_image=f'data/visual_queries/{original["id"]}.png',
                       relevant_by_slot={original['category']: [original['id']]},
                       rationale='Измененная растеризация того же предмета: проверка image→image.') for original in seed]))
    print(f'Wrote {len(corpus)} items, {len(tests)} test queries, {len(dev)} dev queries and visual smoke manifests.')


if __name__ == '__main__':
    main()
