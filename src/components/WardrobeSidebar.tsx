import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Plus, Trash2, Search, Sparkles } from 'lucide-react';

interface WardrobeSidebarProps {
  wardrobe: WardrobeItem[];
  onOpenAddModal: () => void;
  onDeleteItem: (id: string) => void;
  onItemClick: (item: WardrobeItem) => void;
}

const CATEGORIES: { id: ClothingCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'Все вещи' },
  { id: 'tops', label: 'Верх и трикотаж' },
  { id: 'bottoms', label: 'Брюки и юбки' },
  { id: 'outerwear', label: 'Верхняя одежда' },
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
    <div className="w-full h-full flex flex-col bg-[#FAF7F2] dark:bg-[#1E1B19] border border-[#E3DCD1] dark:border-[#2F2C28] select-none shadow-xs">
      {/* Top Header */}
      <div className="p-4 sm:p-6 border-b border-[#E3DCD1] dark:border-[#2F2C28] flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] sm:text-[11px] tracking-[0.2em] uppercase text-[#8A7F73] dark:text-[#A89C8F]">
              Персональная капсула
            </span>
            <span className="w-1 h-1 rounded-full bg-[#8A7F73]" />
            <span className="text-[10px] sm:text-[11px] text-[#8A7F73] dark:text-[#A89C8F]">
              {wardrobe.length} единиц
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-serif-luxury font-light tracking-[0.06em] text-[#2C2926] dark:text-[#F3EEE5] uppercase mt-1">
            Коллекция гардероба
          </h2>
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-2 px-4 py-2 sm:px-5 sm:py-2.5 bg-[#2C2926] hover:bg-[#423D38] dark:bg-[#EAE6DF] dark:hover:bg-[#FFFFFF] text-white dark:text-[#1C1A18] text-xs font-medium tracking-[0.14em] uppercase transition-all shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Добавить вещь</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 sm:p-5 border-b border-[#ECE5D9] dark:border-[#2A2723] flex flex-col md:flex-row md:items-center justify-between gap-3 bg-[#F4EFE6]/50 dark:bg-[#23201D]/50">
        {/* Categories Pills */}
        <div className="flex gap-2 overflow-x-auto scrollbar-none pb-1 md:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 text-[10px] sm:text-[11px] uppercase tracking-[0.12em] font-medium whitespace-nowrap transition-all border ${
                selectedCategory === cat.id
                  ? 'border-[#2C2926] dark:border-[#EAE6DF] bg-[#2C2926] dark:bg-[#EAE6DF] text-white dark:text-[#1C1A18]'
                  : 'border-[#DDD4C6] dark:border-[#38332E] text-[#8A7F73] dark:text-[#A89C8F] hover:border-[#2C2926] dark:hover:border-[#EAE6DF]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-72 shrink-0">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8A7F73]" />
          <input
            type="text"
            placeholder="Поиск по крою, ткани, цвету..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs bg-[#FFFFFF] dark:bg-[#262320] border border-[#DCD3C5] dark:border-[#38332E] text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#8A7F73] transition-colors"
          />
        </div>
      </div>

      {/* Wardrobe Items Grid (Lookbook style in 2 to 4 columns) */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        {filteredItems.length === 0 ? (
          <div className="text-center py-20 px-4">
            <Sparkles className="w-8 h-8 text-[#A69B8E] mx-auto mb-3 stroke-1" />
            <p className="font-serif-luxury text-lg text-[#8A7F73] italic">В этой категории пока нет вещей</p>
            <p className="text-xs uppercase tracking-[0.12em] text-[#A69B8E] mt-1">
              Нажмите «Добавить вещь», чтобы внести её в цифровую капсулу
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-5">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                onClick={() => onItemClick(item)}
                className="group relative flex flex-col bg-[#FFFFFF] dark:bg-[#24211E] border border-[#DDD4C6] dark:border-[#35302B] hover:border-[#2C2926] dark:hover:border-[#EAE6DF] cursor-pointer transition-all duration-300"
              >
                {/* Image */}
                <div className="aspect-3/4 overflow-hidden bg-[#F2ECE1] dark:bg-[#1A1816] relative border-b border-[#ECE5D9] dark:border-[#2D2A26]">
                  <img
                    src={item.imageUrl}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute top-2 left-2">
                    <span className="text-[9px] uppercase tracking-[0.12em] px-1.5 py-0.5 bg-[#FAF7F2]/90 dark:bg-[#1C1A18]/90 text-[#2C2926] dark:text-[#EAE6DF] border border-[#DDD3C4] dark:border-[#38332E]">
                      {item.brand || '12 STOREEZ'}
                    </span>
                  </div>

                  {/* Delete Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteItem(item.id);
                    }}
                    title="Удалить из капсулы"
                    className="opacity-0 group-hover:opacity-100 p-1.5 bg-[#FAF7F2]/90 dark:bg-[#1C1A18]/90 hover:bg-[#991B1B] hover:text-white text-[#8A7F73] border border-[#DDD3C4] dark:border-[#38332E] transition-all absolute top-2 right-2"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Details */}
                <div className="p-3 flex flex-col flex-1 justify-between">
                  <div>
                    <h4 className="text-xs font-medium text-[#2C2926] dark:text-[#EAE6DF] truncate tracking-tight">
                      {item.title}
                    </h4>
                    <p className="text-[10px] text-[#7A6F63] dark:text-[#ABA092] font-light mt-0.5">
                      {item.color} {item.material ? `• ${item.material}` : ''}
                    </p>
                  </div>

                  <div className="mt-2.5 pt-2 border-t border-[#ECE5D9] dark:border-[#2A2723] flex items-center justify-between">
                    <span className="text-[9px] uppercase tracking-[0.14em] text-[#8A7F73] dark:text-[#8F8477]">
                      {item.category}
                    </span>
                    <span className="text-[10px] font-serif-luxury italic text-[#8A7F73]">
                      Смотреть
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom Footer Notice */}
      <div className="p-3 border-t border-[#E3DCD1] dark:border-[#2F2C28] bg-[#F1ECE2] dark:bg-[#221F1C] text-center">
        <p className="text-[10px] uppercase tracking-[0.18em] text-[#8A7F73] dark:text-[#A89C8F]">
          12 STOREEZ • Высококачественные материалы и продуманный крой
        </p>
      </div>
    </div>
  );
};
