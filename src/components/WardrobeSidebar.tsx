import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Plus, Trash2, Search, Sparkles } from 'lucide-react';

interface WardrobeSidebarProps {
  wardrobe: WardrobeItem[];
  onOpenAddModal: () => void;
  onDeleteItem: (id: string) => void;
  onItemClick: (item: WardrobeItem) => void;
}

const CATEGORIES: { id: ClothingCategory | 'all'; label: string; badgeColor: string }[] = [
  { id: 'all', label: 'Все', badgeColor: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200' },
  { id: 'tops', label: 'Верх', badgeColor: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200' },
  { id: 'bottoms', label: 'Низ', badgeColor: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200' },
  { id: 'outerwear', label: 'Верхняя', badgeColor: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200' },
  { id: 'shoes', label: 'Обувь', badgeColor: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200' },
  { id: 'accessories', label: 'Аксессуары', badgeColor: 'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-950 dark:text-fuchsia-200' },
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
    <aside className="w-full h-full flex flex-col bg-stone-50/90 dark:bg-stone-900/90 border-r border-rose-200/50 dark:border-stone-800 select-none">
      {/* Top Header */}
      <div className="p-4 sm:p-5 border-b border-rose-200/50 dark:border-stone-800 flex items-center justify-between">
        <div>
          <h2 className="text-base font-serif-luxury font-medium tracking-wide text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>Ваш гардероб</span>
            <span className="px-2 py-0.5 rounded-full text-xs font-sans font-bold bg-gradient-to-r from-rose-500 to-amber-500 text-white shadow-xs">
              {wardrobe.length}
            </span>
          </h2>
          <p className="text-[11px] text-stone-500 dark:text-stone-400 mt-0.5">
            Персональная капсула
          </p>
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-rose-700 to-amber-700 hover:from-rose-800 hover:to-amber-800 text-white text-xs font-medium shadow-sm transition-all hover:scale-105 active:scale-95"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Categories Filter */}
      <div className="flex gap-1.5 px-3 pt-3 pb-1 overflow-x-auto scrollbar-none">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1.5 rounded-xl text-xs whitespace-nowrap transition-all ${
              selectedCategory === cat.id
                ? 'bg-gradient-to-r from-stone-900 to-rose-950 dark:from-stone-100 dark:to-rose-100 text-white dark:text-stone-900 font-medium shadow-xs'
                : 'text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200 hover:bg-rose-50/80 dark:hover:bg-stone-800'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div className="p-3">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-rose-700/60 dark:text-rose-400/60" />
          <input
            type="text"
            placeholder="Поиск по названию, цвету, бренду..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-xs rounded-xl bg-white dark:bg-stone-950/70 border border-rose-200/60 dark:border-stone-800 text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-rose-400 dark:focus:border-rose-600 transition-colors shadow-2xs"
          />
        </div>
      </div>

      {/* Wardrobe Items List */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2">
        {filteredItems.length === 0 ? (
          <div className="text-center py-12 px-4">
            <p className="text-xs text-stone-500 dark:text-stone-400">Вещи не найдены</p>
            <p className="text-[11px] text-stone-400 dark:text-stone-500 mt-1">
              Измените поисковый запрос или фильтр категории
            </p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              onClick={() => onItemClick(item)}
              className="group relative flex items-center gap-3 p-2.5 rounded-xl bg-white dark:bg-stone-900/60 hover:bg-rose-50/50 dark:hover:bg-stone-850 border border-stone-200/80 dark:border-stone-800/80 hover:border-rose-300 dark:hover:border-stone-700 cursor-pointer transition-all duration-200 shadow-2xs hover:shadow-xs"
            >
              <div className="w-14 h-16 rounded-lg overflow-hidden bg-stone-100 dark:bg-stone-950 shrink-0 border border-stone-200/60 dark:border-stone-800">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              </div>

              <div className="flex-1 min-w-0 pr-6">
                <h4 className="text-xs font-medium text-stone-900 dark:text-stone-100 truncate">
                  {item.title}
                </h4>
                <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-stone-500 dark:text-stone-400">
                  <span className="font-medium text-stone-700 dark:text-stone-300">{item.color}</span>
                  {item.brand && <span>• {item.brand}</span>}
                </div>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {item.tags.slice(0, 2).map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.2 rounded-md text-[9px] bg-rose-100/70 dark:bg-rose-950/50 text-rose-900 dark:text-rose-300 font-medium"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Delete item button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteItem(item.id);
                }}
                title="Удалить вещь"
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-stone-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Bottom Footer Notice */}
      <div className="p-3 border-t border-rose-200/50 dark:border-stone-800 bg-white/70 dark:bg-stone-900/60 text-center">
        <div className="flex items-center justify-center gap-1.5 text-[11px] font-medium text-rose-800 dark:text-rose-300">
          <Sparkles className="w-3 h-3 text-amber-500" />
          <span>Вещи готовы для составления образов</span>
        </div>
      </div>
    </aside>
  );
};
