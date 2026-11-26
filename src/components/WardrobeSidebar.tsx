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

const SUBCATEGORIES: { slot: ClothingCategory; tag: string; label: string; aliases?: string[]; originalId?: string }[] = [
  { slot: 'tops', tag: 'рубашки', label: 'Рубашки', aliases: ['рубашка', 'сорочка'], originalId: 'item-1' },
  { slot: 'tops', tag: 'футболки и топы', label: 'Футболки и топы', aliases: ['футболка', 'топ'] },
  { slot: 'tops', tag: 'трикотаж', label: 'Трикотаж', aliases: ['джемпер', 'свитер', 'кардиган', 'водолазка'] },
  { slot: 'bottoms', tag: 'брюки', label: 'Брюки', aliases: ['палаццо', 'чиносы'] },
  { slot: 'bottoms', tag: 'джинсы', label: 'Джинсы' },
  { slot: 'bottoms', tag: 'юбки', label: 'Юбки', aliases: ['юбка'] },
  { slot: 'bottoms', tag: 'шорты', label: 'Шорты', aliases: ['бермуды'] },
  { slot: 'outerwear', tag: 'жакеты', label: 'Жакеты', aliases: ['жакет', 'блейзер', 'пиджак'] },
  { slot: 'outerwear', tag: 'тренчи и пальто', label: 'Тренчи и пальто', aliases: ['тренч', 'тренчкот', 'пальто', 'плащ'] },
  { slot: 'outerwear', tag: 'куртки', label: 'Куртки', aliases: ['куртка', 'пуховик', 'бомбер'] },
  { slot: 'shoes', tag: 'кеды и кроссовки', label: 'Кеды и кроссовки', aliases: ['кеды', 'кроссовки'] },
  { slot: 'shoes', tag: 'туфли и лоферы', label: 'Туфли и лоферы', aliases: ['туфли', 'лоферы', 'лодочки', 'балетки'] },
  { slot: 'shoes', tag: 'сандалии', label: 'Сандалии', aliases: ['босоножки'] },
  { slot: 'shoes', tag: 'ботинки', label: 'Ботинки', aliases: ['сапоги', 'ботильоны'] },
  { slot: 'accessories', tag: 'сумки', label: 'Сумки', aliases: ['сумка', 'тоут', 'клатч'] },
  { slot: 'accessories', tag: 'платки и шарфы', label: 'Платки и шарфы', aliases: ['платок', 'шарф'] },
  { slot: 'accessories', tag: 'головные уборы', label: 'Головные уборы', aliases: ['шапка', 'кепка', 'панама', 'шляпа'] },
  { slot: 'accessories', tag: 'украшения и ремни', label: 'Украшения и ремни', aliases: ['украшения', 'ремень', 'серьги', 'колье', 'браслет'] },
];

const STYLES = [
  { id: 'business', label: 'Деловой' },
  { id: 'casual', label: 'Повседневный' },
  { id: 'sport', label: 'Спортивный' },
  { id: 'evening', label: 'Вечерний' },
  { id: 'beach', label: 'Пляжный' },
] as const;

const FILTER_CLASS = 'w-full min-w-0 min-h-9 text-xs bg-[#EFECE6] dark:bg-night-field border border-[#DFD9CF] dark:border-night-divider text-[#1E1B18] dark:text-night-fg';

export const WardrobeSidebar = ({
  wardrobe,
  onOpenAddModal,
  onDeleteItem,
  onItemClick,
  onRestoreDefaultCapsule,
}: WardrobeSidebarProps) => {
  const [selectedCategory, setSelectedCategory] = useState<ClothingCategory | 'all'>('all');
  const [selectedSubtype, setSelectedSubtype] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingItem, setDeletingItem] = useState<WardrobeItem | null>(null);

  const activeSubtype = SUBCATEGORIES.find(({ tag }) => tag === selectedSubtype);
  const query = searchQuery.trim().toLowerCase();

  const resetFilters = () => {
    setSelectedCategory('all');
    setSelectedSubtype('');
    setSelectedStyle('');
    setSearchQuery('');
  };

  const filteredItems = wardrobe.filter((item) => {
    if (selectedCategory !== 'all' && item.category !== selectedCategory) return false;
    if (activeSubtype) {
      if (item.category !== activeSubtype.slot) return false;
      const matchesSubtype = item.id === activeSubtype.originalId || item.tags.some((tag) => {
        const normalized = tag.trim().toLowerCase();
        return normalized === activeSubtype.tag || activeSubtype.aliases?.includes(normalized);
      });
      if (!matchesSubtype) return false;
    }
    if (selectedStyle && !item.style.some((style) => style === selectedStyle)) return false;
    return !query || item.title.toLowerCase().includes(query) ||
      item.tags.some((tag) => tag.toLowerCase().includes(query)) ||
      item.color.toLowerCase().includes(query) ||
      Boolean(item.brand?.toLowerCase().includes(query));
  });

  return (
    <div className="w-full h-full flex flex-col bg-[#F6F4F0] dark:bg-night-canvas select-none">
      {/* Top Header */}
      <div className="py-4 border-b border-[#DFD9CF] dark:border-night-divider flex items-center justify-between gap-2">
        <div className="flex flex-col items-start gap-1 sm:flex-row sm:items-center sm:gap-3">
          <h2 className="text-sm font-medium tracking-[0.16em] uppercase text-[#1E1B18] dark:text-night-fg">
            Гардероб ({wardrobe.length})
          </h2>
          {onRestoreDefaultCapsule && (
            <button
              type="button"
              onClick={onRestoreDefaultCapsule}
              title="Добавить недостающие вещи из капсулы, не заменяя ваши"
              className="flex min-h-8 items-center gap-1 text-[11px] text-[#8A8175] dark:text-night-muted hover:text-[#1E1B18] dark:hover:text-night-fg transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Базовая капсула</span>
            </button>
          )}
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-night-accent dark:hover:bg-night-accent-hover text-[#F7F5F0] dark:text-night-ink text-[11px] font-medium tracking-[0.12em] uppercase transition-colors cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="min-w-0 py-3.5 border-b border-[#DFD9CF] dark:border-night-divider flex flex-col gap-3">
        {/* Categories Tabs */}
        <div className="flex gap-4 sm:gap-6 overflow-x-auto scrollbar-none pb-1" role="group" aria-label="Раздел гардероба">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              aria-pressed={selectedCategory === cat.id}
              onClick={() => {
                setSelectedCategory(cat.id);
                if (cat.id !== 'all' && activeSubtype?.slot !== cat.id) setSelectedSubtype('');
              }}
              className={`text-xs uppercase tracking-[0.12em] whitespace-nowrap transition-colors pb-1 border-b cursor-pointer ${
                selectedCategory === cat.id
                  ? 'border-[#1E1B18] dark:border-night-accent text-[#1E1B18] dark:text-night-fg font-medium'
                  : 'border-transparent text-[#7C7469] dark:text-night-muted hover:text-[#1E1B18] dark:hover:text-night-fg'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <select
            aria-label="Подкатегория"
            value={selectedSubtype}
            onChange={(e) => setSelectedSubtype(e.target.value)}
            className={`${FILTER_CLASS} px-2`}
          >
            <option value="">Все подкатегории</option>
            {selectedCategory === 'all'
              ? CATEGORIES.filter(({ id }) => id !== 'all').map(({ id, label }) => (
                  <optgroup key={id} label={label}>
                    {SUBCATEGORIES.filter(({ slot }) => slot === id).map(({ tag, label: subtypeLabel }) => (
                      <option key={tag} value={tag}>{subtypeLabel}</option>
                    ))}
                  </optgroup>
                ))
              : SUBCATEGORIES.filter(({ slot }) => slot === selectedCategory).map(({ tag, label }) => (
                  <option key={tag} value={tag}>{label}</option>
                ))}
          </select>
          <select
            aria-label="Стиль"
            value={selectedStyle}
            onChange={(e) => setSelectedStyle(e.target.value)}
            className={`${FILTER_CLASS} px-2`}
          >
            <option value="">Все стили</option>
            {STYLES.map(({ id, label }) => <option key={id} value={id}>{label}</option>)}
          </select>
          <div className="relative col-span-2 sm:col-span-1">
            <Search aria-hidden="true" className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8A8175] dark:text-night-muted pointer-events-none" />
            <input
              type="search"
              aria-label="Поиск по вещам"
              placeholder="Поиск по вещам..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`${FILTER_CLASS} pl-8 pr-2 placeholder-[#8A8175] dark:placeholder-night-muted`}
            />
          </div>
        </div>
      </div>

      {/* Wardrobe Items Grid */}
      <div className="flex-1 overflow-y-auto py-6">
        {wardrobe.length === 0 ? (
          <div className="text-center py-24 px-4 flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full border border-dashed border-[#DFD9CF] dark:border-night-outline flex items-center justify-center mb-3 text-[#8A8175] dark:text-night-muted">
              <Plus className="w-5 h-5" />
            </div>
            <p className="text-xs font-medium text-[#1E1B18] dark:text-night-fg mb-1">
              Ваш гардероб пока пуст
            </p>
            <p className="text-[11px] text-[#7C7469] dark:text-night-muted max-w-xs mb-4">
              Загрузите фото ваших любимых вещей, чтобы стилист мог собирать законченные образы
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={onOpenAddModal}
                className="px-4 py-2 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-night-accent dark:hover:bg-night-accent-hover text-[#F7F5F0] dark:text-night-ink text-[11px] font-medium tracking-[0.12em] uppercase rounded-lg transition-colors cursor-pointer"
              >
                + Добавить вещь
              </button>
              {onRestoreDefaultCapsule && (
                <button
                  onClick={onRestoreDefaultCapsule}
                  className="px-4 py-2 border border-[#DFD9CF] dark:border-night-divider hover:border-[#1E1B18] text-[#1E1B18] dark:text-night-fg text-[11px] font-normal tracking-[0.12em] uppercase transition-colors cursor-pointer"
                >
                  Добавить базовую капсулу
                </button>
              )}
            </div>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-16 px-4">
            <p role="status" className="text-xs font-medium text-[#1E1B18] dark:text-night-fg mb-2">
              Ничего не найдено
            </p>
            <p className="text-[11px] text-[#7C7469] dark:text-night-muted mb-4">
              Измените поисковый запрос или сбросьте фильтры.
            </p>
            <button
              type="button"
              onClick={resetFilters}
              className="px-4 py-2 border border-[#DFD9CF] dark:border-night-divider hover:border-[#1E1B18] text-[#1E1B18] dark:text-night-fg text-xs cursor-pointer"
            >
              Сбросить фильтры
            </button>
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
                  <div className="aspect-[3/4] overflow-hidden bg-[#ECE7DE] dark:bg-night-image border border-[#DFD9CF] dark:border-night-divider relative mb-2.5 flex items-center justify-center p-2">
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
                      className="opacity-0 group-hover:opacity-100 p-1.5 bg-[#FCFAF7] dark:bg-night-canvas text-[#7C7469] hover:text-red-600 dark:hover:text-red-400 border border-[#DFD9CF] dark:border-night-divider transition-all absolute top-2 right-2 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Details */}
                  <div className="flex flex-col">
                    <h4 className="text-xs font-normal text-[#1E1B18] dark:text-night-fg truncate">
                      {item.title}
                    </h4>
                    <p className="text-[11px] text-[#7C7469] dark:text-night-muted mt-0.5 font-normal">
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
            className="w-full max-w-sm bg-[#FCFAF7] dark:bg-night-panel border border-[#DFD9CF] dark:border-night-divider p-6 shadow-2xl relative text-[#1E1B18] dark:text-night-fg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A8175] dark:text-night-muted mb-2 font-normal">
              12 STOREEZ • Гардероб
            </div>

            <h3 className="text-sm uppercase tracking-[0.06em] font-medium text-[#1E1B18] dark:text-night-fg mb-2">
              Удалить эту вещь?
            </h3>

            <p className="text-xs text-[#6B6359] dark:text-night-muted font-light leading-relaxed mb-5">
              Предмет «<strong>{deletingItem.title}</strong>» будет удален из вашего личного гардероба.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#EFECE6] dark:border-night-divider">
              <button
                onClick={() => setDeletingItem(null)}
                className="px-3.5 py-2 text-xs text-[#8A8175] dark:text-night-muted hover:text-[#1E1B18] dark:hover:text-night-fg transition-colors cursor-pointer font-light"
              >
                Отмена
              </button>
              <button
                onClick={() => {
                  onDeleteItem(deletingItem.id);
                  setDeletingItem(null);
                }}
                className="px-4 py-2 bg-[#1E1B18] hover:bg-black dark:bg-night-accent dark:hover:bg-night-accent-hover text-[#F7F5F0] dark:text-night-ink text-xs uppercase tracking-[0.12em] font-normal transition-colors cursor-pointer"
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
