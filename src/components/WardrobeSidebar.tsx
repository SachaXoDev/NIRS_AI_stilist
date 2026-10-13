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
  { id: 'outerwear', label: 'Пальто и куртки' },
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
    <div className="w-full h-full flex flex-col bg-[#FFFFFF] dark:bg-[#121212] select-none">
      {/* Top Header */}
      <div className="py-4 border-b border-[#E5E5E5] dark:border-[#262626] flex items-center justify-between">
        <h2 className="text-sm font-medium tracking-[0.16em] uppercase text-[#111111] dark:text-[#FFFFFF]">
          Гардероб ({wardrobe.length})
        </h2>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#111111] hover:bg-[#333333] dark:bg-[#FFFFFF] dark:hover:bg-[#E5E5E5] text-white dark:text-[#111111] text-[11px] font-medium tracking-[0.12em] uppercase transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="py-3.5 border-b border-[#E5E5E5] dark:border-[#262626] flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Categories Tabs */}
        <div className="flex gap-4 sm:gap-6 overflow-x-auto scrollbar-none pb-1 md:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`text-xs uppercase tracking-[0.12em] whitespace-nowrap transition-colors pb-1 border-b ${
                selectedCategory === cat.id
                  ? 'border-[#111111] dark:border-[#FFFFFF] text-[#111111] dark:text-[#FFFFFF] font-medium'
                  : 'border-transparent text-[#767676] dark:text-[#888888] hover:text-[#111111] dark:hover:text-[#FFFFFF]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-60 shrink-0">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#999999]" />
          <input
            type="text"
            placeholder="Поиск по вещам..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#F5F5F5] dark:bg-[#1C1C1C] text-[#111111] dark:text-[#FFFFFF] placeholder-[#888888] focus:outline-none"
          />
        </div>
      </div>

      {/* Wardrobe Items Grid (12 STOREEZ E-commerce lookbook) */}
      <div className="flex-1 overflow-y-auto py-6">
        {filteredItems.length === 0 ? (
          <div className="text-center py-20 px-4 text-[#767676]">
            <p className="text-xs">В этой категории пока нет вещей</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                onClick={() => onItemClick(item)}
                className="group flex flex-col cursor-pointer"
              >
                {/* Image */}
                <div className="aspect-[3/4] overflow-hidden bg-[#F5F5F5] dark:bg-[#1A1A1A] relative mb-2.5">
                  <img
                    src={item.imageUrl}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-102 transition-transform duration-300"
                  />

                  {/* Delete Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteItem(item.id);
                    }}
                    title="Удалить"
                    className="opacity-0 group-hover:opacity-100 p-1.5 bg-[#FFFFFF] dark:bg-[#111111] text-[#767676] hover:text-[#111111] dark:hover:text-[#FFFFFF] transition-opacity absolute top-2 right-2"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Details */}
                <div className="flex flex-col">
                  <h4 className="text-xs font-normal text-[#111111] dark:text-[#FFFFFF] truncate">
                    {item.title}
                  </h4>
                  <p className="text-[11px] text-[#767676] dark:text-[#888888] mt-0.5 font-normal">
                    {item.color} {item.material ? `• ${item.material}` : ''}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
