import type { ChatMessage, ChatThread, ClothingCategory, WardrobeItem } from '../types';

interface ChatSuggestion {
  title: string;
  text: string;
}

const TOPICS = [
  {
    title: 'В офис',
    text: 'Подбери образ в офис из моего гардероба.',
    pattern: /(?:^|[^\p{L}])(?:офис|делов|переговор|на работу)/u,
  },
  {
    title: 'На каждый день',
    text: 'Собери повседневный образ из моего гардероба.',
    pattern: /(?:^|[^\p{L}])(?:повседнев|прогул|выходн|на каждый день)/u,
  },
  {
    title: 'На вечер',
    text: 'Подбери вечерний образ из моего гардероба.',
    pattern: /(?:^|[^\p{L}])(?:вечерн|ужин|ресторан|свидан|театр)/u,
  },
  {
    title: 'В поездку',
    text: 'Подбери удобный образ для поездки из моего гардероба.',
    pattern: /(?:^|[^\p{L}])(?:поездк|путешеств|перел[её]т|самол[её]т|аэропорт|поезд(?:\s|$|[,.!?]))/u,
  },
  {
    title: 'На праздник',
    text: 'Собери нарядный образ на праздник из моего гардероба.',
    pattern: /(?:^|[^\p{L}])(?:праздник|свадьб|вечеринк|д[её]нь рожден|дня рожден)/u,
  },
  {
    title: 'На пляж',
    text: 'Подбери образ для пляжа из моего гардероба.',
    pattern: /(?:^|[^\p{L}])пляж/u,
  },
];

const CARD_PROMPTS = {
  warmer: { title: 'Потеплее', text: 'А можно потеплее?' },
  alternative: { title: 'Другой вариант', text: 'А можно другой вариант?' },
  dressier: { title: 'Наряднее', text: 'А можно наряднее?' },
  comfort: { title: 'Будет удобно?', text: 'Будет ли мне удобно в этом образе?' },
};

const REPLACE_SLOT: Record<ClothingCategory, string> = {
  shoes: 'обувь',
  outerwear: 'верхнюю одежду',
  tops: 'верх',
  bottoms: 'низ',
  accessories: 'аксессуар',
};
const SLOT_ORDER: readonly ClothingCategory[] = ['shoes', 'outerwear', 'tops', 'bottoms', 'accessories'];

function outfitSuggestions(items: readonly WardrobeItem[], wardrobe: readonly WardrobeItem[]): ChatSuggestion[] {
  const outfitIds = new Set(items.map(({ id }) => id));
  const edits: ChatSuggestion[] = [];
  for (const category of SLOT_ORDER) {
    if (!wardrobe.some((item) => item.category === category && !outfitIds.has(item.id))) continue;
    const count = items.filter((item) => item.category === category).length;
    const slot = REPLACE_SLOT[category];
    if (count === 1) {
      edits.push({ title: `Заменить ${slot}`, text: `Замени ${slot} в этом образе.` });
    } else if (count === 0 && (category === 'outerwear' || category === 'accessories')) {
      edits.push({ title: `Добавить ${slot}`, text: `Добавь ${slot} к этому образу.` });
    }
  }
  return [CARD_PROMPTS.warmer, ...edits.slice(0, 1), CARD_PROMPTS.alternative,
    CARD_PROMPTS.dressier, CARD_PROMPTS.comfort, ...edits.slice(1)];
}

function itemSuggestions(items: readonly WardrobeItem[]): ChatSuggestion[] {
  const suggestions: ChatSuggestion[] = [];
  const categories = new Set<ClothingCategory>();
  for (const { category, title } of items) {
    const name = title.trim();
    if (name.length < 4 || categories.has(category)) continue;
    const label = name.length > 24 ? `${name.slice(0, 23).trimEnd()}…` : name;
    suggestions.push({ title: `С чем носить: ${label}`, text: `Подбери образ из моего гардероба с вещью «${name}».` });
    categories.add(category);
    if (suggestions.length === 2) break;
  }
  return suggestions;
}

export function getChatSuggestions(
  threads: readonly ChatThread[],
  messages: readonly ChatMessage[],
  wardrobe: readonly WardrobeItem[],
): readonly ChatSuggestion[] {

  const counts = TOPICS.map(() => 0);
  for (const thread of threads) {
    for (const message of thread.messages) {
      if (message.sender !== 'user') continue;
      const text = message.text.toLowerCase();
      TOPICS.forEach(({ pattern }, index) => {
        if (pattern.test(text)) counts[index] += 1;
      });
    }
  }

  const frequent = TOPICS.map((topic, index) => ({ topic, count: counts[index] }))
    .filter(({ count }) => count >= 2)
    .sort((a, b) => b.count - a.count)
    .map(({ topic }) => topic);
  const ranked = [...new Set([...frequent, ...TOPICS])];
  const lastCard = messages.findLast((message) => message.sender === 'assistant' && message.suggestedOutfit);
  const outfit = lastCard?.suggestedOutfit;
  if (outfit) {
    // Use current wardrobe entries by ID: names may have changed since the card was saved.
    const currentItems = outfit.items
      .map(({ id }) => wardrobe.find((item) => item.id === id))
      .filter((item) => item !== undefined);
    currentItems.sort((a, b) => Number(b.category === 'shoes') - Number(a.category === 'shoes'));
    const items = itemSuggestions(currentItems);
    if (lastCard === messages.at(-1)) {
      return [...items, ...outfitSuggestions(outfit.items, wardrobe), ...ranked.slice(0, 2)];
    }
    return [...items, ...ranked];
  }

  return [...ranked.slice(0, 2), ...itemSuggestions(wardrobe), ...ranked.slice(2)];
}
