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
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-[#1C1A18]/60 backdrop-blur-xs">
      <div className="relative w-full max-w-lg max-h-[92dvh] overflow-y-auto rounded-t-2xl sm:rounded-none bg-[#FAF7F2] dark:bg-[#1E1B19] border border-[#DDD3C4] dark:border-[#38332E] shadow-2xl transition-all">
        {/* Mobile handle indicator */}
        <div className="sm:hidden w-12 h-1 bg-[#D6CDC0] dark:bg-[#38332E] rounded-full mx-auto mt-3 mb-1" />

        <button
          onClick={onClose}
          className="absolute top-4 right-4 sm:top-5 sm:right-5 z-10 p-2 bg-[#FAF7F2]/90 dark:bg-[#1E1B19]/90 text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#F3EEE5] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="aspect-[4/3] w-full overflow-hidden bg-[#ECE5DB] dark:bg-[#151312] relative">
          <img
            src={item.imageUrl}
            alt={item.title}
            className="w-full h-full object-cover"
          />
        </div>

        <div className="p-6 sm:p-8">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] uppercase tracking-[0.2em] font-medium text-[#8A7F73]">
              {item.category}
            </span>
            <span className="text-[10px] text-[#A69B8E]">• {item.brand || '12 STOREEZ'}</span>
          </div>

          <h3 className="text-xl sm:text-2xl font-serif-luxury font-light text-[#2C2926] dark:text-[#F3EEE5] mb-4 tracking-wide">
            {item.title}
          </h3>

          <div className="space-y-2.5 sm:space-y-3 my-4 sm:my-5 text-xs text-[#574E43] dark:text-[#B2A89B]">
            {item.material && (
              <div className="flex justify-between border-b border-[#EAE2D5] dark:border-[#2D2A26] pb-2">
                <span className="text-[#8A7F73]">Состав ткани:</span>
                <span className="font-medium text-[#2C2926] dark:text-[#EAE6DF]">{item.material}</span>
              </div>
            )}
            <div className="flex justify-between border-b border-[#EAE2D5] dark:border-[#2D2A26] pb-2">
              <span className="text-[#8A7F73]">Оттенок:</span>
              <span className="font-medium text-[#2C2926] dark:text-[#EAE6DF]">{item.color}</span>
            </div>
            <div className="flex justify-between border-b border-[#EAE2D5] dark:border-[#2D2A26] pb-2">
              <span className="text-[#8A7F73]">Сезонность:</span>
              <span className="font-medium text-[#2C2926] dark:text-[#EAE6DF]">{item.season}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-6 sm:mb-8">
            {item.tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 sm:px-2.5 sm:py-1 text-[10px] sm:text-[11px] bg-[#EFE9DF] dark:bg-[#282521] text-[#6E6357] dark:text-[#A89C8F] font-light"
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
            className="w-full py-3.5 px-5 bg-[#2C2926] hover:bg-[#423D38] dark:bg-[#EAE6DF] dark:hover:bg-[#FFFFFF] text-white dark:text-[#1C1A18] text-xs font-medium uppercase tracking-[0.14em] flex items-center justify-center gap-2 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#C4A482]" />
            <span>Собрать капсульный образ с этой вещью</span>
          </button>
        </div>
      </div>
    </div>
  );
};
