import type { ClothingCategory, ClothingSeason } from '../types';

export const CLOTHING_SEASONS: Record<ClothingSeason, string> = {
  unknown: 'Не указан',
  all: 'Всесезонно',
  'spring/summer': 'Весна / лето',
  'autumn/winter': 'Осень / зима',
};

export const CLOTHING_SEASON_VALUES = Object.keys(CLOTHING_SEASONS) as ClothingSeason[];

export function isClothingSeason(value: unknown): value is ClothingSeason {
  return typeof value === 'string' && Object.hasOwn(CLOTHING_SEASONS, value);
}

const WARM_SEASON = /^(?:летн[а-я]+|пляжн[а-я]+|сандал[а-я]+|босоножк[а-я]+|шл[её]п[а-я]+|шорт[а-я]*|summer|beachwear|sandals?|shorts)$/iu;
const COLD_SEASON = /^(?:зимн[а-я]+|утепленн[а-я]+|пуховик[а-я]*|winter|insulated|puffer)$/iu;
const NO_INSULATION = /(?:^|\s)(?:без|нет|не|неизвестно|no|none|unknown|uninsulated)(?:\s|$)/iu;

export function suggestWardrobeSeason(title: string, category: ClothingCategory | '', insulation?: string): ClothingSeason {
  const words = title.toLowerCase().replaceAll('ё', 'е').match(/\p{L}+/gu) ?? [];
  const warm = words.some((word) => WARM_SEASON.test(word));
  const cold = words.some((word, index) => COLD_SEASON.test(word) && words[index - 1] !== 'не') ||
    ((category === 'outerwear' || category === 'shoes') && /\p{L}/u.test(insulation ?? '') && !NO_INSULATION.test(insulation ?? ''));
  if (warm === cold) return 'unknown';
  return warm ? 'spring/summer' : 'autumn/winter';
}
