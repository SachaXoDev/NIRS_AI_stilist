import type { MaterialDetails, MaterialPart } from '../types';

export const MATERIAL_PARTS: Record<MaterialPart, string> = {
  lining: 'Подкладка',
  insulation: 'Утеплитель / наполнитель',
  sole: 'Подошва',
  insole: 'Стелька',
  trim: 'Отделка',
};

export const MATERIAL_PART_KEYS = Object.keys(MATERIAL_PARTS) as MaterialPart[];

export function cleanMaterialDetails(value: unknown): MaterialDetails | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  const clean: MaterialDetails = {};
  for (const part of MATERIAL_PART_KEYS) {
    const material = raw[part];
    if (typeof material === 'string' && material.trim()) clean[part] = material.trim();
  }
  return Object.keys(clean).length ? clean : undefined;
}
