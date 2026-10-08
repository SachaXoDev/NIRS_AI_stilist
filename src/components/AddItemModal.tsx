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
  const [brand, setBrand] = useState('');
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
      color: color.trim() || 'Базовый',
      season: 'all',
      style: ['casual'],
      tags: tagsInput.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean),
      imageUrl: imageUrl.trim() || 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=600&auto=format&fit=crop&q=80',
      brand: brand.trim() || 'Личный гардероб',
      embeddingSnippet: `${title.trim()}. Категория: ${category}. Цвет: ${color}. Теги: ${tagsInput}`,
      uploadedAt: new Date().toISOString().split('T')[0],
    };

    onAdd(newItem);
    onClose();
    setTitle('');
    setColor('');
    setBrand('');
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 dark:bg-black/70 backdrop-blur-xs transition-opacity">
      <div className="relative w-full max-w-lg rounded-3xl bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 p-6 sm:p-7 shadow-2xl transition-all">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-xl font-serif-luxury font-medium text-stone-900 dark:text-stone-100 mb-1">
          Добавить предмет гардероба
        </h3>
        <p className="text-xs text-stone-500 dark:text-stone-400 mb-6">
          Вещь будет автоматически оцифрована и добавлена в контекст RAG-модели
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
              Название вещи *
            </label>
            <input
              type="text"
              required
              placeholder="Например: Оливковый льняной блейзер"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800 px-3.5 py-2.5 text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-stone-500 transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
                Категория
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ClothingCategory)}
                className="w-full rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800 px-3 py-2.5 text-sm text-stone-900 dark:text-stone-100 focus:outline-none focus:border-stone-500 transition-colors"
              >
                <option value="tops">Верх (рубашки, топы)</option>
                <option value="bottoms">Низ (брюки, деним)</option>
                <option value="outerwear">Верхняя одежда</option>
                <option value="shoes">Обувь</option>
                <option value="accessories">Аксессуары</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
                Цвет
              </label>
              <input
                type="text"
                placeholder="Слоновая кость, шоколад..."
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800 px-3.5 py-2.5 text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-stone-500 transition-colors"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
                Бренд
              </label>
              <input
                type="text"
                placeholder="Massimo Dutti, COS..."
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800 px-3.5 py-2.5 text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-stone-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
                Теги стиля
              </label>
              <input
                type="text"
                placeholder="лен, оверсайз, лето"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                className="w-full rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800 px-3.5 py-2.5 text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-stone-500 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
              Изображение
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="URL фотографии или выберите файл"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="flex-1 rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800 px-3.5 py-2 text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-stone-500 transition-colors"
              />
              <label className="cursor-pointer px-3.5 py-2 rounded-xl bg-stone-100 dark:bg-stone-800 hover:bg-stone-200 dark:hover:bg-stone-750 text-xs text-stone-700 dark:text-stone-300 font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 border border-stone-200 dark:border-stone-700">
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

          {imageUrl && (
            <div className="flex items-center gap-3 p-2 rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
              <img
                src={imageUrl}
                alt="Превью"
                className="w-12 h-14 object-cover rounded-lg border border-stone-200 dark:border-stone-800"
              />
              <span className="text-xs text-stone-500 dark:text-stone-400">Фото загружено и готово</span>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-stone-100 dark:border-stone-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-xs font-medium text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl bg-stone-900 dark:bg-stone-100 hover:bg-stone-800 dark:hover:bg-white text-xs font-medium text-white dark:text-stone-900 shadow-sm transition-all"
            >
              Сохранить в гардероб
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
