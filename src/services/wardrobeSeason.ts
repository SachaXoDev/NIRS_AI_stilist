import type { ClothingSeason } from '../types';

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
