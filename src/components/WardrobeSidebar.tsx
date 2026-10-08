import { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Search, Plus, Trash2, CheckCircle } from 'lucide-react';

interface WardrobeSidebarProps {
  wardrobe: WardrobeItem[];
  onOpenAddModal: () => void;
  onDeleteItem: (id: string) => void;
  onItemClick: (item: WardrobeItem) => void;
}

const CATEGORIES: { key: ClothingCategory | 'all'; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'tops', label: 'Верх' },
  { key: 'bottoms', label: 'Низ' },
  { key: 'outerwear', label: 'Верхняя одежда' },
  { key: 'shoes', label: 'Обувь' },
  { key: 'accessories', label: 'Аксессуары' },
];

export const WardrobeSidebar = ({
  wardrobe,
  onOpenAddModal,
  onDeleteItem,
  onItemClick,
}: WardrobeSidebarProps) => {
  const [activeCategory, setActiveCategory] = useState<ClothingCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredItems = wardrobe.filter((item) => {
    const matchesCategory = activeCategory === 'all' || item.category === activeCategory;
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())) ||
      item.color.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.brand && item.brand.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <aside className="w-full lg:w-96 flex flex-col h-full bg-stone-50/80 dark:bg-stone-900/60 border-l lg:border-l-0 lg:border-r border-stone-200 dark:border-stone-800 transition-colors">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between">
        <div>
          <span className="text-[10px] uppercase tracking-widest font-semibold text-stone-400 dark:text-stone-500">
            Персональная капсула
          </span>
          <h2 className="text-base sm:text-lg font-serif-luxury font-medium text-stone-900 dark:text-stone-100">
            Ваш гардероб <span className="text-xs font-sans text-stone-400 font-normal">({wardrobe.length})</span>
          </h2>
        </div>

        <button
          onClick={onOpenAddModal}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-stone-900 dark:bg-stone-100 hover:bg-stone-800 dark:hover:bg-white text-xs font-medium text-white dark:text-stone-900 transition-all shadow-sm"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Category Tabs */}
      <div className="px-4 py-2.5 border-b border-stone-200/80 dark:border-stone-800/80 overflow-x-auto scrollbar-none flex gap-1.5 bg-stone-100/50 dark:bg-stone-950/30">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActiveCategory(cat.key)}
            className={`px-3 py-1 rounded-lg text-xs transition-colors whitespace-nowrap ${
              activeCategory === cat.key
                ? 'bg-white dark:bg-stone-800 text-stone-900 dark:text-stone-100 font-medium shadow-xs border border-stone-200 dark:border-stone-700'
                : 'text-stone-500 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div className="p-3">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            type="text"
            placeholder="Поиск по названию, цвету, бренду..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-xs rounded-xl bg-white dark:bg-stone-950/70 border border-stone-200 dark:border-stone-800 text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none focus:border-stone-400 dark:focus:border-stone-600 transition-colors"
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
              className="group relative flex items-center gap-3 p-2.5 rounded-xl bg-white dark:bg-stone-900/60 hover:bg-stone-100/70 dark:hover:bg-stone-850 border border-stone-200/80 dark:border-stone-800/80 hover:border-stone-300 dark:hover:border-stone-700 cursor-pointer transition-all duration-200"
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
                  <span>{item.color}</span>
                  {item.brand && <span>• {item.brand}</span>}
                </div>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {item.tags.slice(0, 2).map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.2 rounded text-[9px] bg-stone-100 dark:bg-stone-800 text-stone-500 dark:text-stone-400"
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
                className="absolute top-2.5 right-2.5 p-1 rounded-md text-stone-400 hover:text-rose-600 dark:hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Footer notice */}
      <div className="p-3 border-t border-stone-200 dark:border-stone-800 bg-stone-100/50 dark:bg-stone-950/40 text-[11px] text-stone-500 dark:text-stone-400 flex items-center gap-2">
        <CheckCircle className="w-3.5 h-3.5 shrink-0 text-emerald-500" />
        <span className="truncate">Вещи готовы для составления образов</span>
      </div>
    </aside>
  );
};
