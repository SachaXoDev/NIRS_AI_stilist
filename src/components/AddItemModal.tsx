import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { X, UploadCloud } from 'lucide-react';

interface AddItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: WardrobeItem) => void;
}

export const AddItemModal = ({ isOpen, onClose, onAdd }: AddItemModalProps) => {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<ClothingCategory>('tops');
  const [color, setColor] = useState('');
  const [brand, setBrand] = useState('12 STOREEZ');
  const [imageUrl, setImageUrl] = useState('');
  const [tagsInput, setTagsInput] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    const newItem: WardrobeItem = {
      id: `custom-${Date.now()}`,
      title: title.trim(),
      category,
      color: color.trim() || 'Песочный',
      season: 'all',
      style: ['casual'],
      tags: tagsInput.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean),
      imageUrl: imageUrl.trim() || '/clothes/shirt.svg',
      brand: brand.trim() || '12 STOREEZ',
      embeddingSnippet: `${title.trim()}. Категория: ${category}. Цвет: ${color}. Теги: ${tagsInput}`,
      uploadedAt: new Date().toISOString().split('T')[0],
    };

    onAdd(newItem);
    onClose();
    setTitle('');
    setColor('');
    setBrand('12 STOREEZ');
    setImageUrl('');
    setTagsInput('');
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImageUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-[#1C1A18]/60 backdrop-blur-xs transition-opacity">
      <div className="relative w-full max-w-lg max-h-[92dvh] overflow-y-auto rounded-t-2xl sm:rounded-none bg-[#FAF7F2] dark:bg-[#1C1A18] border border-[#DDD3C4] dark:border-[#38332E] p-6 sm:p-8 shadow-2xl transition-all">
        {/* Mobile handle indicator */}
        <div className="sm:hidden w-12 h-1 bg-[#D6CDC0] dark:bg-[#38332E] rounded-full mx-auto mb-4" />

        <button
          onClick={onClose}
          className="absolute top-5 right-5 sm:top-6 sm:right-6 p-2 text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#F3EEE5] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-xl sm:text-2xl font-serif-luxury font-light tracking-wide text-[#2C2926] dark:text-[#F3EEE5] uppercase mb-1">
          Добавить в капсулу
        </h3>
        <p className="text-[10px] sm:text-[11px] tracking-[0.14em] uppercase text-[#8A7F73] dark:text-[#A89C8F] mb-6 sm:mb-8 font-light">
          Параметры изделия и ткани
        </p>

        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
          <div>
            <label className="block text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium text-[#6E6357] dark:text-[#B5A99B] mb-1.5 sm:mb-2">
              Наименование изделия *
            </label>
            <input
              type="text"
              required
              placeholder="Например: Двубортный жакет из шерсти"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-[#FFFFFF] dark:bg-[#25221F] border border-[#DDD3C4] dark:border-[#38332E] px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#2C2926] transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className="block text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium text-[#6E6357] dark:text-[#B5A99B] mb-1.5 sm:mb-2">
                Категория
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ClothingCategory)}
                className="w-full bg-[#FFFFFF] dark:bg-[#25221F] border border-[#DDD3C4] dark:border-[#38332E] px-2.5 sm:px-3 py-2.5 sm:py-3 text-xs text-[#2C2926] dark:text-[#EAE6DF] focus:outline-none focus:border-[#2C2926] transition-colors"
              >
                <option value="tops">Верх</option>
                <option value="bottoms">Низ</option>
                <option value="outerwear">Пальто</option>
                <option value="shoes">Обувь</option>
                <option value="accessories">Аксессуары</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium text-[#6E6357] dark:text-[#B5A99B] mb-1.5 sm:mb-2">
                Оттенок
              </label>
              <input
                type="text"
                placeholder="Кэмел, графит..."
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full bg-[#FFFFFF] dark:bg-[#25221F] border border-[#DDD3C4] dark:border-[#38332E] px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#2C2926] transition-colors"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className="block text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium text-[#6E6357] dark:text-[#B5A99B] mb-1.5 sm:mb-2">
                Бренд
              </label>
              <input
                type="text"
                placeholder="12 STOREEZ, COS..."
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full bg-[#FFFFFF] dark:bg-[#25221F] border border-[#DDD3C4] dark:border-[#38332E] px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#2C2926] transition-colors"
              />
            </div>

            <div>
              <label className="block text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium text-[#6E6357] dark:text-[#B5A99B] mb-1.5 sm:mb-2">
                Особенности
              </label>
              <input
                type="text"
                placeholder="кашемир, оверсайз..."
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                className="w-full bg-[#FFFFFF] dark:bg-[#25221F] border border-[#DDD3C4] dark:border-[#38332E] px-3.5 sm:px-4 py-2.5 sm:py-3 text-xs text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#2C2926] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium text-[#6E6357] dark:text-[#B5A99B] mb-1.5 sm:mb-2">
              Фотография
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Ссылка на фото"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="flex-1 bg-[#FFFFFF] dark:bg-[#25221F] border border-[#DDD3C4] dark:border-[#38332E] px-3.5 sm:px-4 py-2.5 text-xs text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#2C2926] transition-colors"
              />
              <label className="cursor-pointer px-3.5 sm:px-4 py-2.5 bg-[#EDE6DC] dark:bg-[#2A2723] hover:bg-[#E2D9CC] text-[10px] sm:text-[11px] uppercase tracking-[0.12em] font-medium text-[#4A433A] dark:text-[#C5BCB1] whitespace-nowrap transition-colors flex items-center gap-1.5 border border-[#DDD3C4] dark:border-[#38332E]">
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Файл</span>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 sm:pt-6 border-t border-[#E3DCD1] dark:border-[#2F2C28]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 sm:px-5 py-2.5 text-[10px] sm:text-[11px] uppercase tracking-[0.14em] text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#EAE6DF] transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-6 sm:px-7 py-2.5 bg-[#2C2926] hover:bg-[#423D38] dark:bg-[#EAE6DF] dark:hover:bg-[#FFFFFF] text-white dark:text-[#1C1A18] text-[10px] sm:text-[11px] font-medium uppercase tracking-[0.14em] transition-all"
            >
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
