import type { WardrobeItem } from '../types';
import { X, Sparkles } from 'lucide-react';

interface ItemDetailModalProps {
  item: WardrobeItem | null;
  onClose: () => void;
  onAskAboutItem: (item: WardrobeItem) => void;
}

export const ItemDetailModal = ({
  item,
  onClose,
  onAskAboutItem,
}: ItemDetailModalProps) => {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 dark:bg-black/75 backdrop-blur-xs">
      <div className="relative w-full max-w-lg rounded-3xl bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 overflow-hidden shadow-2xl transition-all">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 p-2 rounded-full bg-white/80 dark:bg-stone-950/80 text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-white backdrop-blur-xs transition-colors shadow-xs"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="aspect-[4/3] w-full overflow-hidden bg-stone-100 dark:bg-stone-950 relative">
          <img
            src={item.imageUrl}
            alt={item.title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-white dark:from-stone-900 via-transparent to-transparent" />
        </div>

        <div className="p-6 -mt-6 relative">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
              {item.category}
            </span>
            {item.brand && (
              <span className="text-xs text-stone-500 dark:text-stone-400">• {item.brand}</span>
            )}
          </div>

          <h3 className="text-xl font-serif-luxury font-medium text-stone-900 dark:text-stone-100 mb-3">
            {item.title}
          </h3>

          <div className="space-y-2.5 my-4 text-xs sm:text-sm text-stone-600 dark:text-stone-300">
            {item.material && (
              <div className="flex justify-between border-b border-stone-100 dark:border-stone-800 pb-2">
                <span className="text-stone-400">Материал:</span>
                <span className="font-medium text-stone-800 dark:text-stone-200">{item.material}</span>
              </div>
            )}
            <div className="flex justify-between border-b border-stone-100 dark:border-stone-800 pb-2">
              <span className="text-stone-400">Цвет:</span>
              <span className="font-medium text-stone-800 dark:text-stone-200">{item.color}</span>
            </div>
            <div className="flex justify-between border-b border-stone-100 dark:border-stone-800 pb-2">
              <span className="text-stone-400">Сезонность:</span>
              <span className="font-medium text-stone-800 dark:text-stone-200">{item.season}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 mb-6">
            {item.tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded-lg text-xs bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 border border-stone-200/60 dark:border-stone-700"
              >
                #{tag}
              </span>
            ))}
          </div>

          <button
            onClick={() => {
              onAskAboutItem(item);
              onClose();
            }}
            className="w-full py-3 px-4 rounded-xl bg-stone-900 dark:bg-stone-100 hover:bg-stone-800 dark:hover:bg-white text-xs sm:text-sm font-medium text-white dark:text-stone-900 flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            <Sparkles className="w-4 h-4 text-stone-400" />
            <span>Собрать аутфит вокруг этой вещи</span>
          </button>
        </div>
      </div>
    </div>
  );
};
