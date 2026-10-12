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
    <div className="w-full h-full flex flex-col bg-[#FAF7F2] dark:bg-[#1A1816] border-2 border-[#D8CFC2] dark:border-[#38332E] select-none shadow-xs">
      {/* Top Header */}
      <div className="p-4 sm:p-6 border-b border-[#D8CFC2] dark:border-[#332F2A] flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] sm:text-[11px] tracking-[0.2em] uppercase font-bold text-[#111111] dark:text-[#FFFFFF]">
              Персональная капсула
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#111111] dark:bg-[#FFFFFF]" />
            <span className="text-[10px] sm:text-[11px] font-semibold text-[#544B3F] dark:text-[#C5BBAE]">
              {wardrobe.length} единиц
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-serif-luxury font-medium tracking-[0.06em] text-[#111111] dark:text-[#FFFFFF] uppercase mt-1">
            Коллекция гардероба
          </h2>
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-2 px-4 py-2 sm:px-5 sm:py-2.5 bg-[#111111] hover:bg-[#2E2E2E] dark:bg-[#FFFFFF] dark:hover:bg-[#EAEAEA] text-white dark:text-[#111111] text-xs font-semibold tracking-[0.14em] uppercase transition-all shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Добавить вещь</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 sm:p-5 border-b border-[#D8CFC2] dark:border-[#332F2A] flex flex-col md:flex-row md:items-center justify-between gap-3 bg-[#F2EDE4]/60 dark:bg-[#201D1A]/60">
        {/* Categories Pills */}
        <div className="flex gap-2 overflow-x-auto scrollbar-none pb-1 md:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3.5 py-1.5 text-[10px] sm:text-[11px] uppercase tracking-[0.12em] font-semibold whitespace-nowrap transition-all border ${
                selectedCategory === cat.id
                  ? 'border-[#111111] dark:border-[#FFFFFF] bg-[#111111] dark:bg-[#FFFFFF] text-white dark:text-[#111111] shadow-xs'
                  : 'border-[#C5BBAE] dark:border-[#3E3830] bg-white dark:bg-[#25221E] text-[#3D352B] dark:text-[#D5CCC0] hover:border-[#111111] dark:hover:border-[#FFFFFF]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-72 shrink-0">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#574D41] dark:text-[#A89C8F]" />
          <input
            type="text"
            placeholder="Поиск по крою, ткани, цвету..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs bg-[#FFFFFF] dark:bg-[#25221E] border border-[#C5BBAE] dark:border-[#3E3830] text-[#111111] dark:text-[#FFFFFF] placeholder-[#7D7366] font-medium focus:outline-none focus:border-[#111111] dark:focus:border-[#FFFFFF] transition-colors"
          />
        </div>
      </div>

      {/* Wardrobe Items Grid */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        {filteredItems.length === 0 ? (
          <div className="text-center py-20 px-4">
            <Sparkles className="w-8 h-8 text-[#8C7D6B] mx-auto mb-3 stroke-1" />
            <p className="font-serif-luxury text-lg text-[#3D352B] dark:text-[#D5CCC0] italic font-medium">В этой категории пока нет вещей</p>
            <p className="text-xs uppercase tracking-[0.12em] text-[#6B6154] dark:text-[#A89D90] font-semibold mt-1">
              Нажмите «Добавить вещь», чтобы внести её в цифровую капсулу
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-5">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                onClick={() => onItemClick(item)}
                className="group relative flex flex-col bg-[#FFFFFF] dark:bg-[#221F1C] border border-[#C5BBAE] dark:border-[#3A342D] hover:border-[#111111] dark:hover:border-[#FFFFFF] cursor-pointer transition-all duration-300 shadow-2xs"
              >
                {/* Image */}
                <div className="aspect-3/4 overflow-hidden bg-[#EFE9DF] dark:bg-[#161412] relative border-b border-[#D8CFC2] dark:border-[#302B25]">
                  <img
                    src={item.imageUrl}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute top-2 left-2">
                    <span className="text-[9px] uppercase tracking-[0.12em] px-2 py-0.5 bg-[#FFFFFF]/95 dark:bg-[#111111]/95 text-[#111111] dark:text-[#FFFFFF] border border-[#C5BBAE] dark:border-[#423C34] font-semibold">
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
                    className="opacity-0 group-hover:opacity-100 p-1.5 bg-[#FFFFFF] dark:bg-[#111111] hover:bg-[#B91C1C] hover:text-white text-[#574D41] dark:text-[#D5CCC0] border border-[#C5BBAE] dark:border-[#423C34] transition-all absolute top-2 right-2"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Details */}
                <div className="p-3 flex flex-col flex-1 justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-[#111111] dark:text-[#FFFFFF] truncate tracking-tight">
                      {item.title}
                    </h4>
                    <p className="text-[11px] text-[#4A4135] dark:text-[#C5BBAE] font-medium mt-0.5">
                      {item.color} {item.material ? `• ${item.material}` : ''}
                    </p>
                  </div>

                  <div className="mt-2.5 pt-2 border-t border-[#EAE2D5] dark:border-[#2D2A26] flex items-center justify-between">
                    <span className="text-[9px] uppercase tracking-[0.14em] font-semibold text-[#6B6154] dark:text-[#A89D90]">
                      {item.category}
                    </span>
                    <span className="text-[11px] font-serif-luxury italic font-medium text-[#111111] dark:text-[#FFFFFF]">
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
      <div className="p-3 border-t border-[#D8CFC2] dark:border-[#332F2A] bg-[#F1ECE2] dark:bg-[#201D1A] text-center">
        <p className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#544B3F] dark:text-[#B5AAA0]">
          12 STOREEZ • Высококачественные материалы и продуманный крой
        </p>
      </div>
    </div>
  );
};
