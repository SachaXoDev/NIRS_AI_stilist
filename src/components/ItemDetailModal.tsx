import { useState, useEffect } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { X, Pencil, Check, ArrowRight } from 'lucide-react';

interface ItemDetailModalProps {
  item: WardrobeItem | null;
  onClose: () => void;
  onAskAboutItem: (item: WardrobeItem, occasion?: string) => void;
  onUpdateItem?: (updatedItem: WardrobeItem) => void;
}

const CATEGORY_NAMES: Record<ClothingCategory, string> = {
  tops: 'Верх и трикотаж',
  bottoms: 'Брюки и деним',
  outerwear: 'Верхняя одежда',
  shoes: 'Обувь',
  accessories: 'Аксессуары',
};

const OCCASIONS = [
  { id: 'work', label: 'Офис и деловые встречи', prompt: 'делового выхода в офис' },
  { id: 'evening', label: 'Вечерний выход и ресторан', prompt: 'вечернего выхода и ужина' },
  { id: 'casual', label: 'Повседневный городской образ', prompt: 'расслабленного городского дня' },
  { id: 'weather', label: 'Прохладная погода / многослойность', prompt: 'прохладной ветреной погоды' },
  { id: 'travel', label: 'Поездка и путешествие', prompt: 'комфортной поездки' },
];

export const ItemDetailModal = ({
  item,
  onClose,
  onAskAboutItem,
  onUpdateItem,
}: ItemDetailModalProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isChoosingOccasion, setIsChoosingOccasion] = useState(false);
  const [customOccasion, setCustomOccasion] = useState('');

  const [title, setTitle] = useState('');
  const [color, setColor] = useState('');
  const [material, setMaterial] = useState('');
  const [category, setCategory] = useState<ClothingCategory>('tops');
  const [season, setSeason] = useState<'all' | 'spring/summer' | 'autumn/winter'>('all');

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setColor(item.color);
      setMaterial(item.material || '');
      setCategory(item.category);
      setSeason(item.season || 'all');
      setIsEditing(false);
      setIsChoosingOccasion(false);
      setCustomOccasion('');
    }
  }, [item]);

  if (!item) return null;

  const handleSave = () => {
    if (!title.trim()) return;

    const updated: WardrobeItem = {
      ...item,
      title: title.trim(),
      color: color.trim() || 'Базовый',
      material: material.trim() || undefined,
      category,
      season,
    };

    if (onUpdateItem) {
      onUpdateItem(updated);
    }
    setIsEditing(false);
  };

  const handleSelectOccasion = (promptText: string) => {
    onAskAboutItem(item, promptText);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-[#FCFAF7] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#2E2A26] p-6 sm:p-7 shadow-2xl relative text-[#1E1B18] dark:text-[#F7F5F0]">
        {/* Controls top right */}
        <div className="absolute top-5 right-5 flex items-center gap-2">
          {!isChoosingOccasion && onUpdateItem && (
            <button
              onClick={() => setIsEditing(!isEditing)}
              title={isEditing ? 'Отменить редактирование' : 'Редактировать вещь'}
              className="text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer p-1"
            >
              <Pencil className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* STEP 2: Choosing Occasion for the selected item */}
        {isChoosingOccasion ? (
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A8175] dark:text-[#A69D92] mb-2 font-normal">
              12 STOREEZ • Подбор повода
            </div>

            <h3 className="text-base font-medium uppercase tracking-[0.04em] text-[#1E1B18] dark:text-[#F7F5F0] mb-2">
              Для какого повода собираем образ?
            </h3>

            <p className="text-xs text-[#6B6359] dark:text-[#A69D92] font-light mb-4 leading-relaxed">
              Выберите повод для выхода с вещью «<strong>{item.title}</strong>» или укажите свой сценарий.
            </p>

            <div className="space-y-2 mb-4">
              {OCCASIONS.map((occ) => (
                <button
                  key={occ.id}
                  onClick={() => handleSelectOccasion(occ.prompt)}
                  className="w-full text-left py-2.5 px-3.5 border border-[#DFD9CF] dark:border-[#2E2A26] hover:border-[#1E1B18] dark:hover:border-white bg-[#FAF8F5] dark:bg-[#221F1C] text-xs text-[#1E1B18] dark:text-[#F7F5F0] transition-colors flex items-center justify-between cursor-pointer"
                >
                  <span>{occ.label}</span>
                  <span className="text-[10px] text-[#8A8175]">Выбрать</span>
                </button>
              ))}
            </div>

            {/* Custom Occasion input */}
            <div className="pt-2 border-t border-[#DFD9CF] dark:border-[#2E2A26] flex gap-2 mb-4">
              <input
                type="text"
                placeholder="Или напишите свой повод (например: на бранч с подругой)..."
                value={customOccasion}
                onChange={(e) => setCustomOccasion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && customOccasion.trim()) {
                    handleSelectOccasion(customOccasion.trim());
                  }
                }}
                className="flex-1 px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
              />
              <button
                disabled={!customOccasion.trim()}
                onClick={() => handleSelectOccasion(customOccasion.trim())}
                className="px-3.5 py-2 bg-[#1E1B18] text-white dark:bg-white dark:text-black text-xs uppercase tracking-wider disabled:opacity-40 transition-opacity cursor-pointer flex items-center"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex justify-between items-center">
              <button
                type="button"
                onClick={() => setIsChoosingOccasion(false)}
                className="text-xs text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer font-light"
              >
                ← Вернуться к вещи
              </button>
              <button
                type="button"
                onClick={() => handleSelectOccasion('любого универсального повода')}
                className="text-xs text-[#1E1B18] dark:text-white underline hover:opacity-80 transition-opacity cursor-pointer font-light"
              >
                Без конкретного повода
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row gap-6">
            {/* Image */}
            <div className="w-full sm:w-44 aspect-[3/4] bg-[#ECE7DE] dark:bg-[#201D1A] border border-[#DFD9CF] dark:border-[#2E2A26] shrink-0 overflow-hidden flex items-center justify-center p-2">
              <img
                src={
                  item.imageUrl ||
                  (item.category === 'bottoms'
                    ? '/clothes/palazzo.svg'
                    : item.category === 'outerwear'
                    ? '/clothes/blazer.svg'
                    : item.category === 'shoes'
                    ? '/clothes/loafers.svg'
                    : item.category === 'accessories'
                    ? '/clothes/tote.svg'
                    : '/clothes/shirt.svg')
                }
                alt={item.title}
                onError={(e) => {
                  const fallback =
                    item.category === 'bottoms'
                      ? '/clothes/palazzo.svg'
                      : item.category === 'outerwear'
                      ? '/clothes/blazer.svg'
                      : item.category === 'shoes'
                      ? '/clothes/loafers.svg'
                      : item.category === 'accessories'
                      ? '/clothes/tote.svg'
                      : '/clothes/shirt.svg';
                  (e.currentTarget as HTMLImageElement).src = fallback;
                }}
                className="w-full h-full object-contain"
              />
            </div>

            {/* Details / Edit View */}
            <div className="flex-1 flex flex-col justify-between">
              {!isEditing ? (
                <div>
                  <span className="text-[10px] tracking-[0.2em] uppercase text-[#8A8175] dark:text-[#A69D92] block mb-1 font-normal">
                    {item.brand || '12 STOREEZ'}
                  </span>

                  <h3 className="text-base font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-4 leading-snug">
                    {item.title}
                  </h3>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1.5 border-b border-[#EFECE6] dark:border-[#282420]">
                      <span className="text-[#8A8175] dark:text-[#A69D92]">Линейка</span>
                      <span className="text-[#1E1B18] dark:text-[#F7F5F0] font-normal">
                        {CATEGORY_NAMES[item.category] || item.category}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-[#EFECE6] dark:border-[#282420]">
                      <span className="text-[#8A8175] dark:text-[#A69D92]">Оттенок</span>
                      <span className="text-[#1E1B18] dark:text-[#F7F5F0]">{item.color}</span>
                    </div>
                    {item.material && (
                      <div className="flex justify-between py-1.5 border-b border-[#EFECE6] dark:border-[#282420]">
                        <span className="text-[#8A8175] dark:text-[#A69D92]">Состав ткани</span>
                        <span className="text-[#1E1B18] dark:text-[#F7F5F0]">{item.material}</span>
                      </div>
                    )}
                    {item.season && (
                      <div className="flex justify-between py-1.5 border-b border-[#EFECE6] dark:border-[#282420]">
                        <span className="text-[#8A8175] dark:text-[#A69D92]">Сезонность</span>
                        <span className="text-[#1E1B18] dark:text-[#F7F5F0]">
                          {item.season === 'all'
                            ? 'Внесезонная базовая модель'
                            : item.season === 'autumn/winter'
                            ? 'Осень / Зима (утепленная)'
                            : 'Весна / Лето (облегченная)'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <span className="text-[10px] tracking-[0.2em] uppercase text-[#8A8175] dark:text-[#A69D92] block font-normal">
                    Редактирование вещи
                  </span>

                  <div>
                    <label className="block text-[10px] uppercase tracking-wider text-[#8A8175] mb-1">
                      Название
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-[#8A8175] mb-1">
                        Линейка
                      </label>
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value as ClothingCategory)}
                        className="w-full px-2 py-1.5 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                      >
                        <option value="tops">Верх и трикотаж</option>
                        <option value="bottoms">Брюки и деним</option>
                        <option value="outerwear">Верхняя одежда</option>
                        <option value="shoes">Обувь</option>
                        <option value="accessories">Аксессуары</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-[#8A8175] mb-1">
                        Оттенок
                      </label>
                      <input
                        type="text"
                        value={color}
                        onChange={(e) => setColor(e.target.value)}
                        className="w-full px-2.5 py-1.5 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-[#8A8175] mb-1">
                        Состав ткани
                      </label>
                      <input
                        type="text"
                        value={material}
                        onChange={(e) => setMaterial(e.target.value)}
                        placeholder="Шерсть, кашемир..."
                        className="w-full px-2.5 py-1.5 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-[#8A8175] mb-1">
                        Сезон
                      </label>
                      <select
                        value={season}
                        onChange={(e) => setSeason(e.target.value as 'all' | 'spring/summer' | 'autumn/winter')}
                        className="w-full px-2 py-1.5 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                      >
                        <option value="all">Внесезонно</option>
                        <option value="autumn/winter">Осень / Зима</option>
                        <option value="spring/summer">Весна / Лето</option>
                      </select>
                    </div>
                  </div>

                  <div className="pt-2 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1 text-xs text-[#8A8175] hover:text-[#1E1B18] transition-colors cursor-pointer"
                    >
                      Отмена
                    </button>
                    <button
                      type="button"
                      onClick={handleSave}
                      className="px-3.5 py-1.5 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-wider transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Сохранить</span>
                    </button>
                  </div>
                </div>
              )}

              {!isEditing && (
                <div className="pt-6">
                  <button
                    onClick={() => setIsChoosingOccasion(true)}
                    className="w-full py-3 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.14em] font-normal transition-colors cursor-pointer text-center"
                  >
                    С чем носить в моем гардеробе?
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
