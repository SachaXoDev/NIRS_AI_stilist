import React, { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Plus, X, UploadCloud } from 'lucide-react';

interface AddItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: WardrobeItem) => void;
}

export const AddItemModal: React.FC<AddItemModalProps> = ({ isOpen, onClose, onAdd }) => {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl bg-neutral-900 border border-neutral-800 p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-neutral-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <UploadCloud className="w-6 h-6 text-rose-500" />
          Добавить вещь в гардероб
        </h3>
        <p className="text-xs text-neutral-400 mb-5">
          Загрузите фотографию и укажите характеристики. Векторные эмбеддинги будут вычислены для RAG-поиска.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-1">
              Название вещи *
            </label>
            <input
              type="text"
              required
              placeholder="Например: Оливковый льняной пиджак"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3.5 py-2.5 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-rose-500 transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-300 mb-1">
                Категория *
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ClothingCategory)}
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-rose-500 transition-colors"
              >
                <option value="tops">Верх (рубашки, топы, свитера)</option>
                <option value="bottoms">Низ (брюки, джинсы, юбки)</option>
                <option value="outerwear">Верхняя одежда (жакеты, куртки)</option>
                <option value="shoes">Обувь</option>
                <option value="accessories">Аксессуары (сумки, платки)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-300 mb-1">
                Цвет
              </label>
              <input
                type="text"
                placeholder="Бежевый, графит..."
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3.5 py-2.5 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-rose-500 transition-colors"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-300 mb-1">
                Бренд (опционально)
              </label>
              <input
                type="text"
                placeholder="Zara, Massimo Dutti, Lime..."
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3.5 py-2.5 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-rose-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-300 mb-1">
                Теги через запятую
              </label>
              <input
                type="text"
                placeholder="оверсайз, лен, лето"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3.5 py-2.5 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-rose-500 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-300 mb-1">
              Фотография вещи
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                placeholder="URL ссылка на фото или загрузите с устройства"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="flex-1 rounded-xl bg-neutral-800 border border-neutral-700 px-3.5 py-2 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-rose-500 transition-colors"
              />
              <label className="cursor-pointer px-3.5 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 text-xs text-neutral-200 font-medium whitespace-nowrap transition-colors flex items-center gap-1.5">
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
            <div className="flex items-center gap-3 p-2 rounded-xl bg-neutral-800/50 border border-neutral-700">
              <img
                src={imageUrl}
                alt="Предпросмотр"
                className="w-14 h-14 object-cover rounded-lg border border-neutral-700"
              />
              <span className="text-xs text-neutral-400">Превью изображения готово к индексации</span>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-neutral-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-sm font-medium text-neutral-300 transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 text-sm font-semibold text-white shadow-lg shadow-rose-500/20 transition-all flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              Добавить в гардероб
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
