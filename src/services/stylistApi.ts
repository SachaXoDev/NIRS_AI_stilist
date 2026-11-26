import type { WardrobeItem, OutfitLook, ClothingCategory, RetrievalResult, StylistHistoryMessage } from '../types';
import { INITIAL_WARDROBE } from '../data/initialWardrobe';
import { getCurrentUser } from './authService';
import { BACKEND_URL, USE_REAL_BACKEND } from './backendConfig';

/**
 * Service representing the AI Stylist API.
 *
 * По умолчанию работает клиентский симулятор (проект запускается без бэкенда).
 * Чтобы ходить в настоящий FastAPI-бэкенд (каталог backend/), создайте .env.local:
 *
 *   VITE_USE_REAL_BACKEND=true
 *   VITE_BACKEND_URL=http://localhost:8000
 */

// Первый подбор индексирует гардероб: на локальной машине это может занять больше минуты.
const BACKEND_TIMEOUT_MS = 180_000;

// Видимая пометка: ответ собран не сервером, а локальным симулятором.
const OFFLINE_NOTE =
  ' (Сервер стилиста сейчас недоступен — этот образ собран локальным демо-симулятором.)';

interface StylistResponse {
  text: string;
  suggestedOutfit?: OutfitLook;
  referencedItemIds?: string[];
  // Необязательная диагностика бэкенда (см. spec/tech/architecture.md)
  source?: 'llm' | 'mock' | 'fallback' | 'rules' | 'none' | 'client-mock';
  missingSlots?: ClothingCategory[];
  warnings?: string[];
  timings?: Record<string, number>;
  retrieval?: RetrievalResult;
}

interface StylistRequestOptions {
  signal?: AbortSignal;
  userId?: string;
  history?: StylistHistoryMessage[];
  onText?: (text: string) => void;
}

async function readStylistStream(res: Response, onText?: StylistRequestOptions['onText']): Promise<StylistResponse> {
  if (!res.ok || !res.body || !res.headers.get('Content-Type')?.includes('text/event-stream')) {
    throw new Error(`Invalid stylist stream (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let text = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) throw new Error('Stylist stream ended before result');
      buffer += decoder.decode(value, { stream: true });

      // Network chunks need not end on an SSE frame or on a UTF-8 character.
      let boundary = /\r?\n\r?\n/.exec(buffer);
      while (boundary) {
        const lines = buffer.slice(0, boundary.index).split(/\r?\n/);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
        if (event === 'delta' || event === 'result' || event === 'error') {
          const data = JSON.parse(lines.filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).replace(/^ /, '')).join('\n'));
          if (event === 'error') throw new Error(data.message || 'Stylist stream failed');
          if (typeof data?.text !== 'string') throw new Error(`Invalid stylist ${event}`);
          if (event === 'result') return data as StylistResponse;
          text += data.text;
          onText?.(text);
        }
        boundary = /\r?\n\r?\n/.exec(buffer);
      }
    }
  } finally {
    void reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export async function askStylist(
  userQuery: string,
  wardrobe: WardrobeItem[],
  context?: { occasion?: string; weather?: string; vibe?: string },
  options: StylistRequestOptions = {},
): Promise<StylistResponse> {
  let backendFailed = false;

  if (USE_REAL_BACKEND) {
    const timeout = AbortSignal.timeout(BACKEND_TIMEOUT_MS);
    const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
    try {
      const res = await fetch(`${BACKEND_URL}/api/recommend-outfit/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        signal,
        body: JSON.stringify({
          query: userQuery,
          // Гардероб живёт в localStorage, поэтому серверу нужен полный снимок вещей:
          // он синхронизирует его с индексом поиска и подбирает образ только из него.
          wardrobe,
          wardrobe_ids: wardrobe.map((i) => i.id),
          // Демо-идентификатор, не защищённая сессия: разделяет гардеробы пользователей.
          user_id: options.userId ?? getCurrentUser()?.id ?? 'anonymous',
          context,
          history: options.history,
        }),
      });
      return await readStylistStream(res, options.onText);
    } catch (err) {
      options.signal?.throwIfAborted();
      options.onText?.('');
      backendFailed = true;
      console.warn('Real backend unavailable, falling back to client-side RAG simulator:', err);
    }
  }

  // Client-side RAG Simulation with semantic keyword matching & outfit synthesis
  await new Promise((r) => setTimeout(r, 1000 + Math.random() * 600));
  options.signal?.throwIfAborted();

  const queryLower = userQuery.toLowerCase();
  const occasion = context?.occasion?.toLowerCase() || '';
  // Демо не проверяет температурную разметку: в сильный мороз не выдаём случайную карточку.
  const frost = (context?.weather ?? '').match(/(?<!\w)(?:[-−–]\s*|минус\s+)(\d{1,2})(?!\d)/i)
    ?? queryLower.match(/(?<!\w)(?:[-−–]\s*|минус\s+)(\d{1,2})(?!\d)/i);
  if (frost && Number(frost[1]) >= 15 && Number(frost[1]) <= 80) {
    return {
      text: `При −${frost[1]} °C нужны зимние ботинки и тёплая верхняя одежда с подходящим температурным диапазоном. Демо-режим не может это проверить, поэтому образ не предлагаю.`,
      source: 'client-mock',
    };
  }

  // Classify intent
  const isWorkOrBusiness =
    queryLower.includes('работ') ||
    queryLower.includes('офис') ||
    queryLower.includes('делов') ||
    queryLower.includes('встреч') ||
    queryLower.includes('презентац') ||
    occasion.includes('работ');

  const weatherText = `${context?.weather ?? ''} ${queryLower}`;
  const degrees = weatherText.match(/(?<![\w.,])([+\-−]?\s*\d{1,2})\s*°\s*[cс]?/i);
  const temperature = degrees ? Number(degrees[1].replace(/\s/g, '').replace('−', '-')) : undefined;
  const isRainOrCold =
    (temperature !== undefined && temperature >= -80 && temperature <= 12) ||
    weatherText.includes('дожд') ||
    weatherText.includes('снег') ||
    weatherText.includes('холод') ||
    weatherText.includes('прохлад') ||
    weatherText.includes('ветр') ||
    weatherText.includes('осень') ||
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
    text: backendFailed ? stylistText + OFFLINE_NOTE : stylistText,
    suggestedOutfit: outfit,
    referencedItemIds: selectedItems.map((i) => i.id),
    source: 'client-mock',
  };
}
