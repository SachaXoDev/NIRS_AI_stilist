import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Plus, Search, Trash2, RotateCcw } from 'lucide-react';

interface WardrobeSidebarProps {
  wardrobe: WardrobeItem[];
  onOpenAddModal: () => void;
  onDeleteItem: (id: string) => void;
  onItemClick: (item: WardrobeItem) => void;
  onRestoreDefaultCapsule?: () => void;
}

const CATEGORIES: { id: ClothingCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'Все' },
  { id: 'tops', label: 'Верх' },
  { id: 'bottoms', label: 'Низ' },
  { id: 'outerwear', label: 'Верхняя одежда' },
  { id: 'shoes', label: 'Обувь' },
  { id: 'accessories', label: 'Аксессуары' },
];

export const WardrobeSidebar = ({
  wardrobe,
  onOpenAddModal,
  onDeleteItem,
  onItemClick,
  onRestoreDefaultCapsule,
}: WardrobeSidebarProps) => {
  const [selectedCategory, setSelectedCategory] = useState<ClothingCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingItem, setDeletingItem] = useState<WardrobeItem | null>(null);

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
    <div className="w-full h-full flex flex-col bg-[#F6F4F0] dark:bg-[#181614] select-none">
      {/* Top Header */}
      <div className="py-4 border-b border-[#DFD9CF] dark:border-[#2E2A26] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium tracking-[0.16em] uppercase text-[#1E1B18] dark:text-[#F7F5F0]">
            Гардероб ({wardrobe.length})
          </h2>
          {onRestoreDefaultCapsule && (
            <button
              onClick={onRestoreDefaultCapsule}
              title="Загрузить базовую капсулу 12 STOREEZ"
              className="hidden sm:flex items-center gap-1 text-[11px] text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Базовая капсула</span>
            </button>
          )}
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-[11px] font-medium tracking-[0.12em] uppercase transition-colors cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="py-3.5 border-b border-[#DFD9CF] dark:border-[#2E2A26] flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Categories Tabs */}
        <div className="flex gap-4 sm:gap-6 overflow-x-auto scrollbar-none pb-1 md:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`text-xs uppercase tracking-[0.12em] whitespace-nowrap transition-colors pb-1 border-b cursor-pointer ${
                selectedCategory === cat.id
                  ? 'border-[#1E1B18] dark:border-[#F7F5F0] text-[#1E1B18] dark:text-[#F7F5F0] font-medium'
                  : 'border-transparent text-[#7C7469] dark:text-[#A69D92] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-60 shrink-0">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8A8175]" />
          <input
            type="text"
            placeholder="Поиск по вещам..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#EFECE6] dark:bg-[#201D1A] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] placeholder-[#8A8175] focus:outline-none"
          />
        </div>
      </div>

      {/* Wardrobe Items Grid */}
      <div className="flex-1 overflow-y-auto py-6">
        {filteredItems.length === 0 ? (
          <div className="text-center py-24 px-4 flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full border border-dashed border-[#DFD9CF] dark:border-[#38332E] flex items-center justify-center mb-3 text-[#8A8175]">
              <Plus className="w-5 h-5" />
            </div>
            <p className="text-xs font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-1">
              Ваш гардероб пока пуст
            </p>
            <p className="text-[11px] text-[#7C7469] dark:text-[#A69D92] max-w-xs mb-4">
              Загрузите фото ваших любимых вещей, чтобы стилист мог собирать законченные образы
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={onOpenAddModal}
                className="px-4 py-2 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-[11px] font-medium tracking-[0.12em] uppercase rounded-lg transition-colors cursor-pointer"
              >
                + Добавить вещь
              </button>
              {onRestoreDefaultCapsule && (
                <button
                  onClick={onRestoreDefaultCapsule}
                  className="px-4 py-2 border border-[#DFD9CF] dark:border-[#2E2A26] hover:border-[#1E1B18] text-[#1E1B18] dark:text-white text-[11px] font-normal tracking-[0.12em] uppercase transition-colors cursor-pointer"
                >
                  Загрузить капсулу бренда
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
            {filteredItems.map((item) => {
              const fallbackSvg =
                item.category === 'bottoms'
                  ? '/clothes/palazzo.svg'
                  : item.category === 'outerwear'
                  ? '/clothes/blazer.svg'
                  : item.category === 'shoes'
                  ? '/clothes/loafers.svg'
                  : item.category === 'accessories'
                  ? '/clothes/tote.svg'
                  : '/clothes/shirt.svg';

              return (
                <div
                  key={item.id}
                  onClick={() => onItemClick(item)}
                  className="group flex flex-col cursor-pointer"
                >
                  {/* Image */}
                  <div className="aspect-[3/4] overflow-hidden bg-[#ECE7DE] dark:bg-[#1E1B19] border border-[#DFD9CF] dark:border-[#2E2A26] relative mb-2.5 flex items-center justify-center p-2">
                    <img
                      src={item.imageUrl || fallbackSvg}
                      alt={item.title}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).src = fallbackSvg;
                      }}
                      className="w-full h-full object-contain group-hover:scale-102 transition-transform duration-300"
                    />

                    {/* Delete Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeletingItem(item);
                      }}
                      title="Удалить вещь"
                      className="opacity-0 group-hover:opacity-100 p-1.5 bg-[#FCFAF7] dark:bg-[#181614] text-[#7C7469] hover:text-red-600 dark:hover:text-red-400 border border-[#DFD9CF] dark:border-[#2E2A26] transition-all absolute top-2 right-2 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Details */}
                  <div className="flex flex-col">
                    <h4 className="text-xs font-normal text-[#1E1B18] dark:text-[#F7F5F0] truncate">
                      {item.title}
                    </h4>
                    <p className="text-[11px] text-[#7C7469] dark:text-[#A69D92] mt-0.5 font-normal">
                      {item.color} {item.material ? `• ${item.material}` : ''}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete Item Confirmation Modal in 12 STOREEZ style */}
      {deletingItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={() => setDeletingItem(null)}
        >
          <div
            className="w-full max-w-sm bg-[#FCFAF7] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#2E2A26] p-6 shadow-2xl relative text-[#1E1B18] dark:text-[#F7F5F0]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A8175] dark:text-[#A69D92] mb-2 font-normal">
              12 STOREEZ • Гардероб
            </div>

            <h3 className="text-sm uppercase tracking-[0.06em] font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-2">
              Удалить эту вещь?
            </h3>

            <p className="text-xs text-[#6B6359] dark:text-[#A69D92] font-light leading-relaxed mb-5">
              Предмет «<strong>{deletingItem.title}</strong>» будет удален из вашего личного гардероба.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#EFECE6] dark:border-[#282420]">
              <button
                onClick={() => setDeletingItem(null)}
                className="px-3.5 py-2 text-xs text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer font-light"
              >
                Отмена
              </button>
              <button
                onClick={() => {
                  onDeleteItem(deletingItem.id);
                  setDeletingItem(null);
                }}
                className="px-4 py-2 bg-[#1E1B18] hover:bg-black dark:bg-[#F7F5F0] dark:hover:bg-white text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.12em] font-normal transition-colors cursor-pointer"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
