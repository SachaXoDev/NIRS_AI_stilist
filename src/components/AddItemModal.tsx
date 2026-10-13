import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { X } from 'lucide-react';

interface AddItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: WardrobeItem) => void;
}

const CATEGORY_OPTIONS: { value: ClothingCategory; label: string }[] = [
  { value: 'tops', label: 'Верх и трикотаж' },
  { value: 'bottoms', label: 'Брюки и юбки' },
  { value: 'outerwear', label: 'Верхняя одежда' },
  { value: 'shoes', label: 'Обувь' },
  { value: 'accessories', label: 'Аксессуары' },
];

export const AddItemModal = ({ isOpen, onClose, onAdd }: AddItemModalProps) => {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<ClothingCategory>('tops');
  const [color, setColor] = useState('');
  const [material, setMaterial] = useState('');
  const [brand, setBrand] = useState('12 STOREEZ');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    const newItem: WardrobeItem = {
      id: `custom-${Date.now()}`,
      title: title.trim(),
      category,
      color: color.trim() || 'Базовый',
      season: 'all',
      style: ['минимализм'],
      tags: [category, color.toLowerCase(), material.toLowerCase()].filter(Boolean),
      brand: brand.trim() || '12 STOREEZ',
      material: material.trim() || 'Натуральные волокна',
      imageUrl: '/clothes/shirt.svg',
      uploadedAt: new Date().toISOString(),
    };

    onAdd(newItem);
    onClose();
    setTitle('');
    setColor('');
    setMaterial('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
      <div className="w-full max-w-md bg-[#FFFFFF] dark:bg-[#181818] border border-[#E5E5E5] dark:border-[#2B2B2B] p-6 shadow-xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-[#888888] hover:text-[#111111] dark:hover:text-[#FFFFFF]"
        >
          <X className="w-4 h-4" />
        </button>

        <h3 className="text-xs uppercase tracking-[0.16em] font-medium text-[#111111] dark:text-[#FFFFFF] mb-6">
          Новая вещь
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[11px] uppercase tracking-[0.1em] text-[#767676] dark:text-[#888888] mb-1">
              Название
            </label>
            <input
              type="text"
              required
              placeholder="Например: Прямой блейзер из шерсти"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-[#F5F5F5] dark:bg-[#222222] text-[#111111] dark:text-[#FFFFFF] focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] uppercase tracking-[0.1em] text-[#767676] dark:text-[#888888] mb-1">
                Категория
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ClothingCategory)}
                className="w-full px-3 py-2 text-xs bg-[#F5F5F5] dark:bg-[#222222] text-[#111111] dark:text-[#FFFFFF] focus:outline-none"
              >
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.1em] text-[#767676] dark:text-[#888888] mb-1">
                Цвет
              </label>
              <input
                type="text"
                placeholder="Экрю, Графит..."
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#F5F5F5] dark:bg-[#222222] text-[#111111] dark:text-[#FFFFFF] focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] uppercase tracking-[0.1em] text-[#767676] dark:text-[#888888] mb-1">
                Материал
              </label>
              <input
                type="text"
                placeholder="Шерсть, шелк..."
                value={material}
                onChange={(e) => setMaterial(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#F5F5F5] dark:bg-[#222222] text-[#111111] dark:text-[#FFFFFF] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.1em] text-[#767676] dark:text-[#888888] mb-1">
                Бренд
              </label>
              <input
                type="text"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#F5F5F5] dark:bg-[#222222] text-[#111111] dark:text-[#FFFFFF] focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-[#767676] hover:text-[#111111] dark:hover:text-[#FFFFFF] transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-[#111111] hover:bg-[#333333] dark:bg-[#FFFFFF] dark:hover:bg-[#E5E5E5] text-white dark:text-[#111111] text-xs uppercase tracking-[0.12em] font-medium transition-colors"
            >
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
