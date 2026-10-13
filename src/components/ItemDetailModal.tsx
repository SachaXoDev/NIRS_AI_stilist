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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-[#FFFFFF] dark:bg-[#181818] border border-[#E5E5E5] dark:border-[#2B2B2B] p-6 shadow-xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-[#888888] hover:text-[#111111] dark:hover:text-[#FFFFFF]"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Image */}
          <div className="w-full sm:w-44 aspect-[3/4] bg-[#F5F5F5] dark:bg-[#202020] shrink-0 overflow-hidden">
            <img
              src={item.imageUrl}
              alt={item.title}
              className="w-full h-full object-cover"
            />
          </div>

          {/* Details */}
          <div className="flex-1 flex flex-col justify-between">
            <div>
              <span className="text-[10px] tracking-[0.18em] uppercase text-[#767676] dark:text-[#888888] block mb-1">
                {item.brand || '12 STOREEZ'}
              </span>

              <h3 className="text-base font-medium text-[#111111] dark:text-[#FFFFFF] mb-4">
                {item.title}
              </h3>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-[#F0F0F0] dark:border-[#242424]">
                  <span className="text-[#767676] dark:text-[#888888]">Категория</span>
                  <span className="text-[#111111] dark:text-[#FFFFFF] capitalize">{item.category}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#F0F0F0] dark:border-[#242424]">
                  <span className="text-[#767676] dark:text-[#888888]">Цвет</span>
                  <span className="text-[#111111] dark:text-[#FFFFFF]">{item.color}</span>
                </div>
                {item.material && (
                  <div className="flex justify-between py-1 border-b border-[#F0F0F0] dark:border-[#242424]">
                    <span className="text-[#767676] dark:text-[#888888]">Материал</span>
                    <span className="text-[#111111] dark:text-[#FFFFFF]">{item.material}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-6">
              <button
                onClick={() => {
                  onAskAboutItem(item);
                  onClose();
                }}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#111111] hover:bg-[#333333] dark:bg-[#FFFFFF] dark:hover:bg-[#E5E5E5] text-white dark:text-[#111111] text-xs uppercase tracking-[0.14em] font-medium transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Собрать образ с этой вещью</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
