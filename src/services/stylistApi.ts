import type { WardrobeItem, OutfitLook } from '../types';

/**
 * Service representing the AI Stylist API.
 * Currently runs with intelligent mock RAG heuristics matching user requests to the wardrobe items.
 * When the backend integrator prepares the Python/FastAPI RAG service,
 * simply change USE_REAL_BACKEND to true and configure the endpoint!
 */

const USE_REAL_BACKEND = false;
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

interface StylistResponse {
  text: string;
  suggestedOutfit?: OutfitLook;
  referencedItemIds?: string[];
}

export async function askStylist(
  userQuery: string,
  wardrobe: WardrobeItem[],
  context?: { occasion?: string; weather?: string; vibe?: string }
): Promise<StylistResponse> {
  if (USE_REAL_BACKEND) {
    try {
      const res = await fetch(`${BACKEND_URL}/api/recommend-outfit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userQuery,
          wardrobe_ids: wardrobe.map((i) => i.id),
          context,
        }),
      });
      if (!res.ok) throw new Error('API error');
      return await res.json();
    } catch (err) {
      console.warn('Real backend unavailable, falling back to client-side RAG simulator:', err);
    }
  }

  // Client-side RAG Simulation with semantic keyword matching & outfit synthesis
  await new Promise((r) => setTimeout(r, 1000 + Math.random() * 600));

  const queryLower = userQuery.toLowerCase();
  const occasion = context?.occasion?.toLowerCase() || '';

  // Classify intent
  const isWorkOrBusiness =
    queryLower.includes('работ') ||
    queryLower.includes('офис') ||
    queryLower.includes('делов') ||
    queryLower.includes('встреч') ||
    queryLower.includes('презентац') ||
    occasion.includes('работ');

  const isRainOrCold =
    queryLower.includes('дожд') ||
    queryLower.includes('холод') ||
    queryLower.includes('прохлад') ||
    queryLower.includes('ветр') ||
    queryLower.includes('+12') ||
    queryLower.includes('осень') ||
    queryLower.includes('куртк');

  const isDateOrEvening =
    queryLower.includes('свидан') ||
    queryLower.includes('вечер') ||
    queryLower.includes('ресторан') ||
    queryLower.includes('ужин') ||
    queryLower.includes('элегант');

  // RAG Search simulation (retrieval by category & style tags)
  let selectedItems: WardrobeItem[] = [];
  let outfitTitle = 'Стильный сбалансированный образ';
  let stylistText = '';
  let reason = '';
  let tips: string[] = [];

  const tops = wardrobe.filter((i) => i.category === 'tops');
  const bottoms = wardrobe.filter((i) => i.category === 'bottoms');
  const outerwear = wardrobe.filter((i) => i.category === 'outerwear');
  const shoes = wardrobe.filter((i) => i.category === 'shoes');
  const accessories = wardrobe.filter((i) => i.category === 'accessories');

  if (isRainOrCold) {
    outfitTitle = 'Уютный многослойный образ для прохладной погоды';
    const trench = outerwear.find((i) => i.tags.includes('тренч')) || outerwear[0];
    const sweater = tops.find((i) => i.tags.includes('свитер')) || tops[0];
    const jeans = bottoms.find((i) => i.tags.includes('джинсы')) || bottoms[0];
    const boots = shoes.find((i) => i.tags.includes('лоферы')) || shoes[0];
    const bag = accessories.find((i) => i.tags.includes('сумка')) || accessories[0];

    selectedItems = [trench, sweater, jeans, boots, bag].filter(Boolean) as WardrobeItem[];
    stylistText =
      'Для прохладной или дождливой погоды я собрал образ по принципу **smart layering (умной многослойности)**. Тренчкот защитит от ветра и легкого дождя, а мягкий кашемировый джемпер сохранит тепло. Базовый деним добавит комфорта в движении.';
    reason =
      'Бежевый тренч + молочный кашемир создают благородную монохромную гамму в светлых тонах, а темный деним и шоколадный тоут служат гармоничными визуальными якорями.';
    tips = [
      'Закатайте рукава тренча на 1 оборот, чтобы слегка показать манжет свитера — это создаст трендовый расслабленный эффект.',
      'Шоколадная сумка идеально перекликается с теплыми пуговицами тренча.',
    ];
  } else if (isWorkOrBusiness) {
    outfitTitle = 'Smart-Casual для офиса и деловых встреч';
    const blazer = outerwear.find((i) => i.tags.includes('блейзер')) || outerwear[0];
    const shirt = tops.find((i) => i.tags.includes('рубашка')) || tops[0];
    const trousers = bottoms.find((i) => i.tags.includes('палаццо')) || bottoms[0];
    const loafers = shoes.find((i) => i.tags.includes('лоферы')) || shoes[0];
    const tote = accessories.find((i) => i.tags.includes('сумка')) || accessories[0];

    selectedItems = [blazer, shirt, trousers, loafers, tote].filter(Boolean) as WardrobeItem[];
    stylistText =
      'Собрал для вас безупречный бизнес-аутфит в эстетике современной классики. Черный структурированный блейзер в сочетании с белой рубашкой задает профессиональный тон, а свободные брюки палаццо делают образ современным и не сковывающим.';
    reason =
      'Классический контраст черного и белого сбалансирован мягким серым оттенком брюк со складками. Лоферы на умеренно массивной подошве добавляют авторитетности.';
    tips = [
      'Оставьте 2 верхние пуговицы рубашки расстегнутыми для легкой непринужденности.',
      'Тоут держите в руке, а не на плече, чтобы не деформировать плечевой шов блейзера.',
    ];
  } else if (isDateOrEvening) {
    outfitTitle = 'Элегантный вечерний образ с акцентом';
    const blazer = outerwear.find((i) => i.tags.includes('блейзер')) || outerwear[0];
    const shirt = tops.find((i) => i.tags.includes('рубашка')) || tops[0];
    const trousers = bottoms.find((i) => i.tags.includes('палаццо')) || bottoms[0];
    const scarf = accessories.find((i) => i.tags.includes('платок')) || accessories[0];
    const loafers = shoes.find((i) => i.tags.includes('лоферы')) || shoes[0];

    selectedItems = [blazer, shirt, trousers, scarf, loafers].filter(Boolean) as WardrobeItem[];
    stylistText =
      'Для особого вечера предлагаю утонченный образ: строгий блейзер, драпирующиеся струящиеся брюки палаццо и акцентный шелковый платок, который придает французский шарм.';
    reason =
      'Шелковый платок с геометрическим узором разбивает строгую монохромную палитру и притягивает взгляд к портретной зоне.';
    tips = [
      'Повяжите платок узлом набок или аккуратно заправьте концы под ворот рубашки.',
      'Накиньте блейзер на плечи, не просовывая руки в рукава — так силуэт смотрится расслабленно и богемно.',
    ];
  } else {
    outfitTitle = 'Комфортный городской минимализм (Casual)';
    const shirt = tops.find((i) => i.tags.includes('рубашка')) || tops[0];
    const sweater = tops.find((i) => i.tags.includes('свитер')) || tops[1];
    const jeans = bottoms.find((i) => i.tags.includes('джинсы')) || bottoms[0];
    const sneakers = shoes.find((i) => i.tags.includes('кеды')) || shoes[0];
    const bag = accessories.find((i) => i.tags.includes('сумка')) || accessories[0];

    selectedItems = [shirt, sweater, jeans, sneakers, bag].filter(Boolean) as WardrobeItem[];
    stylistText =
      'Для вашего запроса я подобрал универсальный городской аутфит. Прямой деним и белые кожаные кеды — основа комфорта, а рубашка с наброшенным на плечи джемпером добавляет образу продуманности.';
    reason =
      'Гармония текстур: гладкий хлопок соприкасается с фактурным кашемиром и денимом. Белый цвет кед и рубашки перекликается между собой, объединяя лук.';
    tips = [
      'Набросьте кашемировый джемпер на плечи и слегка завяжите рукава спереди для актуального стайлинга.',
      'Белые минималистичные кеды сохранят свежесть и легкую походку на весь день.',
    ];
  }

  const outfit: OutfitLook = {
    id: `outfit-${Date.now()}`,
    title: outfitTitle,
    description: stylistText,
    occasion: context?.occasion || 'Повседневный',
    items: selectedItems,
    stylistReasoning: reason,
    matchScore: 94 + Math.floor(Math.random() * 5),
    confidenceTips: tips,
  };

  return {
    text: stylistText,
    suggestedOutfit: outfit,
    referencedItemIds: selectedItems.map((i) => i.id),
  };
}
