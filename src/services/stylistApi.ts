import type { WardrobeItem, OutfitLook } from '../types';
import { INITIAL_WARDROBE } from '../data/initialWardrobe';

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
      'Собрал образ по принципу умной многослойности: тренч защитит от сырости и ветра, а кашемировый джемпер сохранит тепло.';
    reason =
      'Благородный монохром светлого тренча и кашемира с акцентом на шоколадный тоут.';
    tips = [
      'Слегка подверните рукава тренча, приоткрыв манжет джемпера.',
      'Шоколадная сумка гармонично перекликается с пуговицами тренча.',
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
      'Лаконичный деловой образ в эстетике 12 STOREEZ: структурированный блейзер, свободные брюки палаццо и хлопковая сорочка.';
    reason =
      'Классический графичный контраст со смягчающим серым оттенком брюк.';
    tips = [
      'Расстегните верхние пуговицы сорочки для легкой непринужденности.',
      'Тоут держите в руке, чтобы силуэт оставался чистым.',
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
      'Сдержанный вечерний силуэт: строгий блейзер, струящиеся брюки и шелковый платок как изящный акцент в портретной зоне.';
    reason =
      'Шелковый принт оживляет монохромную классику и придает кинематографичность.';
    tips = [
      'Повяжите платок аккуратным узлом набок.',
      'Накиньте блейзер на плечи для расслабленной подачи.',
    ];
  } else {
    outfitTitle = 'Комфортный городской минимализм';
    const shirt = tops.find((i) => i.tags.includes('рубашка')) || tops[0];
    const sweater = tops.find((i) => i.tags.includes('свитер')) || tops[1];
    const jeans = bottoms.find((i) => i.tags.includes('джинсы')) || bottoms[0];
    const sneakers = shoes.find((i) => i.tags.includes('кеды')) || shoes[0];
    const bag = accessories.find((i) => i.tags.includes('сумка')) || accessories[0];

    selectedItems = [shirt, sweater, jeans, sneakers, bag].filter(Boolean) as WardrobeItem[];
    stylistText =
      'Универсальный городской образ: прямой деним, белая рубашка и наброшенный на плечи мягкий джемпер.';
    reason =
      'Контраст фактур гладкого хлопка, плотного денима и кашемира.';
    tips = [
      'Набросьте джемпер на плечи и слегка перехватите рукава.',
      'Белые минималистичные кеды завершают чистую геометрию.',
    ];
  }

  // Если в кастомном гардеробе меньше позиций — используем добавленные вещи
  if (selectedItems.length === 0) {
    selectedItems = wardrobe.slice(0, 4);
    if (selectedItems.length === 0) {
      selectedItems = INITIAL_WARDROBE.slice(0, 3);
    }
  }

  // Гарантируем, что у каждой вещи есть корректный URL картинки (fallback на svg-силуэт)
  selectedItems = selectedItems.map((item) => {
    let fallbackImg = '/clothes/shirt.svg';
    if (item.category === 'bottoms') fallbackImg = '/clothes/palazzo.svg';
    if (item.category === 'outerwear') fallbackImg = '/clothes/blazer.svg';
    if (item.category === 'shoes') fallbackImg = '/clothes/loafers.svg';
    if (item.category === 'accessories') fallbackImg = '/clothes/tote.svg';

    return {
      ...item,
      imageUrl: item.imageUrl && item.imageUrl.trim() ? item.imageUrl : fallbackImg,
    };
  });

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
