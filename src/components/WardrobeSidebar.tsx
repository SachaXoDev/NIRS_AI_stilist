import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Plus, Trash2, Search } from 'lucide-react';

interface WardrobeSidebarProps {
  wardrobe: WardrobeItem[];
  onOpenAddModal: () => void;
  onDeleteItem: (id: string) => void;
  onItemClick: (item: WardrobeItem) => void;
}

const CATEGORIES: { id: ClothingCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'Все' },
  { id: 'tops', label: 'Верх' },
  { id: 'bottoms', label: 'Низ' },
  { id: 'outerwear', label: 'Пальто и жакеты' },
  { id: 'shoes', label: 'Обувь' },
  { id: 'accessories', label: 'Аксессуары' },
];

export const WardrobeSidebar = ({
  wardrobe,
  onOpenAddModal,
  onDeleteItem,
  onItemClick,
}: WardrobeSidebarProps) => {
  const [selectedCategory, setSelectedCategory] = useState<ClothingCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredItems = wardrobe.filter((item) => {
    const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory;
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())) ||
      item.color.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.brand && item.brand.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <aside className="w-full h-full flex flex-col bg-[#F7F4EE] dark:bg-[#1E1B19] border-r border-[#E3DCD1] dark:border-[#2F2C28] select-none">
      {/* Top Header */}
      <div className="p-4 sm:p-6 border-b border-[#E3DCD1] dark:border-[#2F2C28] flex items-center justify-between">
        <div>
          <h2 className="text-base sm:text-xl font-serif-luxury font-light tracking-[0.06em] text-[#2C2926] dark:text-[#F3EEE5] uppercase">
            Ваша капсула
          </h2>
          <p className="text-[10px] sm:text-[11px] uppercase tracking-[0.15em] text-[#8A7F73] dark:text-[#A89C8F] mt-0.5 sm:mt-1 font-light">
            {wardrobe.length} предметов гардероба
          </p>
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-none bg-[#2C2926] hover:bg-[#423D38] dark:bg-[#EAE6DF] dark:hover:bg-[#FFFFFF] text-white dark:text-[#1C1A18] text-[10px] sm:text-[11px] font-medium tracking-[0.12em] uppercase transition-all"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Categories Filter in 12 STOREEZ minimal tabs */}
      <div className="flex gap-2 px-4 sm:px-6 pt-3 sm:pt-4 pb-2 overflow-x-auto scrollbar-none border-b border-[#ECE5D9] dark:border-[#2A2723]">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`pb-2 text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-medium whitespace-nowrap transition-all border-b-2 ${
              selectedCategory === cat.id
                ? 'border-[#2C2926] dark:border-[#EAE6DF] text-[#2C2926] dark:text-[#EAE6DF]'
                : 'border-transparent text-[#8A7F73] dark:text-[#807568] hover:text-[#2C2926] dark:hover:text-[#D5CCC0]'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div className="px-4 sm:px-6 py-3 sm:py-3.5">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8A7F73]" />
          <input
            type="text"
            placeholder="Поиск по крою, ткани, цвету..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-none bg-[#EDE7DC]/70 dark:bg-[#262320] border border-[#DCD3C5] dark:border-[#38332E] text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#8A7F73] transition-colors"
          />
        </div>
      </div>

      {/* Wardrobe Items List */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 pb-6 space-y-2.5 sm:space-y-3">
        {filteredItems.length === 0 ? (
          <div className="text-center py-16 px-4">
            <p className="font-serif-luxury text-base sm:text-lg text-[#8A7F73] italic">В этой категории пока нет вещей</p>
            <p className="text-[10px] uppercase tracking-[0.1em] text-[#A69B8E] mt-1">
              Нажмите «Добавить», чтобы оцифровать одежду
            </p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              onClick={() => onItemClick(item)}
              className="group relative flex items-center gap-3 sm:gap-4 p-2.5 sm:p-3 rounded-none bg-[#EFE9DF]/80 dark:bg-[#25221F] hover:bg-[#EAE2D5] dark:hover:bg-[#2C2925] border border-[#DDD4C6] dark:border-[#35302B] hover:border-[#B29377] dark:hover:border-[#8F7761] cursor-pointer transition-all duration-200"
            >
              <div className="w-14 h-18 sm:w-16 sm:h-20 overflow-hidden bg-[#ECE5DB] dark:bg-[#1A1816] shrink-0 border border-[#D5CBC0] dark:border-[#2D2A26]">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
              </div>

              <div className="flex-1 min-w-0 pr-6">
                <span className="text-[9px] sm:text-[10px] tracking-[0.14em] uppercase text-[#8A7F73] dark:text-[#9E9283] block mb-0.5">
                  {item.brand || '12 STOREEZ'}
                </span>
                <h4 className="text-xs font-medium text-[#2C2926] dark:text-[#EAE6DF] truncate tracking-tight">
                  {item.title}
                </h4>
                <div className="flex items-center gap-2 mt-1 text-[10px] sm:text-[11px] text-[#7A6F63] dark:text-[#ABA092]">
                  <span className="font-light">{item.color}</span>
                  {item.material && <span>• {item.material}</span>}
                </div>
              </div>

              {/* Delete item button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteItem(item.id);
                }}
                title="Убрать из капсулы"
                className="opacity-80 sm:opacity-0 group-hover:opacity-100 p-2 text-[#8A7F73] hover:text-[#991B1B] transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Bottom Footer Notice */}
      <div className="p-2.5 sm:p-3 border-t border-[#E3DCD1] dark:border-[#2F2C28] bg-[#F1ECE2] dark:bg-[#221F1C] text-center">
        <p className="text-[9px] sm:text-[10px] uppercase tracking-[0.16em] text-[#8A7F73] dark:text-[#A89C8F]">
          Премиальные ткани • Натуральные оттенки
        </p>
      </div>
    </aside>
  );
};
