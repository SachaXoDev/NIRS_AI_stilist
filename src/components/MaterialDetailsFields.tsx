import { useState } from 'react';
import type { MaterialDetails, MaterialPart } from '../types';
import { MATERIAL_PART_KEYS, MATERIAL_PARTS } from '../services/materialDetails';

export function MaterialDetailsFields({ value, onChange }: {
  value: MaterialDetails;
  onChange: (part: MaterialPart, material: string) => void;
}) {
  const [expanded, setExpanded] = useState<boolean | undefined>();
  const open = expanded ?? MATERIAL_PART_KEYS.some((part) => Boolean(value[part]));
  return (
    <details className="space-y-2 text-xs text-[#6B6258] dark:text-[#BFB3A6]" open={open}>
      <summary className="cursor-pointer" onClick={(event) => {
        event.preventDefault();
        setExpanded(!open);
      }}>Состав по частям</summary>
      <div className="grid grid-cols-2 gap-2">
        {MATERIAL_PART_KEYS.map((part) => (
          <label key={part} className="min-w-0">
            {MATERIAL_PARTS[part]}
            <input
              value={value[part] ?? ''}
              onChange={(event) => onChange(part, event.target.value)}
              className="mt-1 w-full rounded-md border border-[#DFD9CF] bg-[#EFECE6] px-2 py-1.5 text-base text-[#1E1B18] dark:border-[#38332E] dark:bg-[#25221F] dark:text-[#F7F5F0] sm:text-sm"
            />
          </label>
        ))}
      </div>
    </details>
  );
}
