import React, { useState } from 'react';
import type { ClothingCategory, WardrobeItem } from '../types';
import { Plus, Trash2, Layers, Info } from 'lucide-react';

interface WardrobeSidebarProps {
  wardrobe: WardrobeItem[];
  onOpenAddModal: () => void;
  onDeleteItem: (id: string) => void;
  onItemClick: (item: WardrobeItem) => void;
}

const CATEGORIES: { key: ClothingCategory | 'all'; label: string; icon: string }[] = [
  { key: 'all', label: 'Все вещи', icon: '✨' },
  { key: 'tops', label: 'Верх', icon: '👔' },
  { key: 'bottoms', label: 'Низ', icon: '👖' },
  { key: 'outerwear', label: 'Верхняя одежда', icon: '🧥' },
  { key: 'shoes', label: 'Обувь', icon: '👟' },
  { key: 'accessories', label: 'Аксессуары', icon: '👜' },
];

export const WardrobeSidebar: React.FC<WardrobeSidebarProps> = ({
  wardrobe,
  onOpenAddModal,
  onDeleteItem,
  onItemClick,
}) => {
  const [activeCategory, setActiveCategory] = useState<ClothingCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredItems = wardrobe.filter((item) => {
    const matchesCategory = activeCategory === 'all' || item.category === activeCategory;
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())) ||
      item.color.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <aside className="w-full lg:w-96 flex flex-col h-full bg-neutral-900/60 border-l lg:border-l-0 lg:border-r border-neutral-800">
      {/* Top Header */}
      <div className="p-4 border-b border-neutral-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Мой Гардероб</h2>
            <p className="text-xs text-neutral-400">
              База знаний для RAG ({wardrobe.length} шт.)
            </p>
          </div>
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500 hover:bg-rose-600 text-xs font-semibold text-white shadow-md shadow-rose-500/20 transition-all hover:scale-[1.02]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Category Pills */}
      <div className="p-3 border-b border-neutral-800/80 overflow-x-auto scrollbar-none flex gap-1.5">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActiveCategory(cat.key)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeCategory === cat.key
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-neutral-800/50 text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200 border border-transparent'
            }`}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div className="px-3 pt-3">
        <input
          type="text"
          placeholder="Поиск по вещам, цвету или тегу..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full rounded-xl bg-neutral-800/60 border border-neutral-700/60 px-3 py-2 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-rose-500/60 transition-colors"
        />
      </div>

      {/* Wardrobe Items List / Grid */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {filteredItems.length === 0 ? (
          <div className="text-center py-12 px-4">
            <p className="text-xs text-neutral-400">Ничего не найдено</p>
            <p className="text-[11px] text-neutral-500 mt-1">
              Попробуйте изменить категорию или поисковый запрос
            </p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              onClick={() => onItemClick(item)}
              className="group relative flex items-center gap-3 p-2.5 rounded-xl bg-neutral-850/40 hover:bg-neutral-800/80 border border-neutral-800 hover:border-neutral-700 cursor-pointer transition-all duration-200"
            >
              <div className="w-16 h-16 rounded-lg overflow-hidden bg-neutral-900 shrink-0 border border-neutral-800">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              </div>

              <div className="flex-1 min-w-0 pr-6">
                <h4 className="text-xs font-semibold text-neutral-200 truncate group-hover:text-rose-300 transition-colors">
                  {item.title}
                </h4>
                <div className="flex items-center gap-2 mt-0.5 text-[11px] text-neutral-400">
                  <span>{item.color}</span>
                  {item.brand && <span>• {item.brand}</span>}
                </div>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {item.tags.slice(0, 3).map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.5 rounded text-[10px] bg-neutral-800 text-neutral-400 border border-neutral-700/50"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Delete button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteItem(item.id);
                }}
                title="Удалить из гардероба"
                className="absolute top-2.5 right-2.5 p-1 rounded-md text-neutral-500 hover:text-red-400 hover:bg-neutral-800/80 opacity-0 group-hover:opacity-100 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* RAG Context Banner */}
      <div className="p-3 border-t border-neutral-800 bg-neutral-950/40 text-[11px] text-neutral-400 flex items-start gap-2">
        <Info className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
        <p>
          Все эти вещи оцифрованы и используются как контекст для RAG-поиска стилиста.
        </p>
      </div>
    </aside>
  );
};
