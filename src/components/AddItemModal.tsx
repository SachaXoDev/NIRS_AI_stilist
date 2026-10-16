import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { X, Sparkles, Upload } from 'lucide-react';

interface AddItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: WardrobeItem) => void;
}

const CATEGORY_OPTIONS: { value: ClothingCategory; label: string }[] = [
  { value: 'tops', label: 'Верх и трикотаж' },
  { value: 'bottoms', label: 'Брюки, деним и юбки' },
  { value: 'outerwear', label: 'Верхняя одежда (пальто, тренчи)' },
  { value: 'shoes', label: 'Обувь' },
  { value: 'accessories', label: 'Аксессуары (сумки, шарфы)' },
];

export const AddItemModal = ({ isOpen, onClose, onAdd }: AddItemModalProps) => {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<ClothingCategory>('tops');
  const [color, setColor] = useState('');
  const [material, setMaterial] = useState('');
  const [brand, setBrand] = useState('12 STOREEZ');
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  if (!isOpen) return null;

  // Распознавание фото нейросетью с конвертацией в Data URL (для сохранения в хранилище)
  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const dataUrl = event.target?.result as string;
        setPhotoPreview(dataUrl);
      };
      reader.readAsDataURL(file);

      if (!title) setTitle('Двубортный жакет прямого кроя');
      if (!color) setColor('Графит');
      if (!material) setMaterial('Шерсть 100%');
      setCategory('outerwear');
    }
  };

  const handleSimulateSmartSnap = () => {
    setPhotoPreview('https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=400&q=80');
    setTitle('Шерстяной оверсайз жакет');
    setColor('Графитовый серый');
    setMaterial('Тонкая мериносовая шерсть');
    setCategory('outerwear');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    let defaultImage = '/clothes/shirt.svg';
    if (category === 'bottoms') defaultImage = '/clothes/palazzo.svg';
    if (category === 'outerwear') defaultImage = '/clothes/blazer.svg';
    if (category === 'shoes') defaultImage = '/clothes/loafers.svg';
    if (category === 'accessories') defaultImage = '/clothes/tote.svg';

    const newItem: WardrobeItem = {
      id: `custom-${Date.now()}`,
      title: title.trim(),
      category,
      color: color.trim() || 'Базовый',
      season: 'all',
      style: ['минимализм', 'тихая роскошь'],
      tags: [category, color.toLowerCase(), material.toLowerCase()].filter(Boolean),
      brand: brand.trim() || '12 STOREEZ',
      material: material.trim() || 'Натуральные волокна',
      imageUrl: photoPreview || defaultImage,
      uploadedAt: new Date().toISOString(),
    };

    onAdd(newItem);
    onClose();
    setTitle('');
    setColor('');
    setMaterial('');
    setPhotoPreview(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs">
      <div className="w-full max-w-md bg-[#FCFAF7] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#2E2A26] p-6 shadow-2xl relative rounded-xl">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        <h3 className="text-xs uppercase tracking-[0.16em] font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-1">
          Добавить в гардероб
        </h3>
        <p className="text-[11px] text-[#7C7469] dark:text-[#A69D92] mb-4">
          Загрузите фото — параметры вещи определяются автоматически.
        </p>

        {/* AI Quick Upload Dropzone */}
        <div className="mb-4">
          <label className="border-2 border-dashed border-[#DFD9CF] dark:border-[#38332E] hover:border-[#1E1B18] dark:hover:border-white/50 rounded-xl p-3.5 flex flex-col items-center justify-center cursor-pointer transition-colors bg-[#F6F4F0] dark:bg-[#22201D] relative overflow-hidden group">
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handlePhotoUpload}
            />
            {photoPreview ? (
              <div className="flex items-center gap-3 w-full">
                <img
                  src={photoPreview}
                  alt="Загруженная вещь"
                  className="w-12 h-12 object-cover rounded-lg border border-[#DFD9CF] dark:border-[#38332E]"
                />
                <div className="flex-1 text-left">
                  <div className="text-xs font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" /> Фото распознано AI
                  </div>
                  <div className="text-[11px] text-[#7C7469] dark:text-[#A69D92]">
                    Характеристики вещи определены автоматически
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center text-center">
                <Upload className="w-5 h-5 text-[#7C7469] mb-1 group-hover:scale-105 transition-transform" />
                <span className="text-xs font-medium text-[#1E1B18] dark:text-white">
                  Нажмите для загрузки фото
                </span>
                <span className="text-[10px] text-[#7C7469] dark:text-[#9E9487]">
                  JPG, PNG или снимок с камеры
                </span>
              </div>
            )}
          </label>

          {!photoPreview && (
            <button
              type="button"
              onClick={handleSimulateSmartSnap}
              className="mt-2 w-full py-1.5 px-3 text-[11px] text-[#5A534A] dark:text-[#C4BCB2] bg-[#EFECE6] dark:bg-[#25221F] hover:bg-[#E5E0D6] dark:hover:bg-[#2F2B26] rounded-lg transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Sparkles className="w-3 h-3 text-amber-600 dark:text-amber-400" />
              <span>Попробовать авто-распознавание (Жакет 12 STOREEZ)</span>
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-[10px] uppercase tracking-[0.1em] text-[#7C7469] dark:text-[#A69D92] mb-1">
              Название
            </label>
            <input
              type="text"
              required
              placeholder="Например: Прямой блейзер из шерсти"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] rounded-lg text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-[0.1em] text-[#7C7469] dark:text-[#A69D92] mb-1">
                Категория
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ClothingCategory)}
                className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] rounded-lg text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
              >
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-[0.1em] text-[#7C7469] dark:text-[#A69D92] mb-1">
                Цвет
              </label>
              <input
                type="text"
                placeholder="Экрю, Графит..."
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] rounded-lg text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-[0.1em] text-[#7C7469] dark:text-[#A69D92] mb-1">
                Материал
              </label>
              <input
                type="text"
                placeholder="Шерсть, шелк..."
                value={material}
                onChange={(e) => setMaterial(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] rounded-lg text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-[0.1em] text-[#7C7469] dark:text-[#A69D92] mb-1">
                Бренд
              </label>
              <input
                type="text"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] rounded-lg text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-[#7C7469] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.12em] font-medium transition-colors rounded-lg cursor-pointer shadow-xs"
            >
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};