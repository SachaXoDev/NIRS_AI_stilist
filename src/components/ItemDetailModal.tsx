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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-[#FCFAF7] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#2E2A26] p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0]"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Image */}
          <div className="w-full sm:w-44 aspect-[3/4] bg-[#ECE7DE] dark:bg-[#201D1A] border border-[#DFD9CF] dark:border-[#2E2A26] shrink-0 overflow-hidden">
            <img
              src={item.imageUrl}
              alt={item.title}
              className="w-full h-full object-cover"
            />
          </div>

          {/* Details */}
          <div className="flex-1 flex flex-col justify-between">
            <div>
              <span className="text-[10px] tracking-[0.18em] uppercase text-[#7C7469] dark:text-[#A69D92] block mb-1">
                {item.brand || '12 STOREEZ'}
              </span>

              <h3 className="text-base font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-4">
                {item.title}
              </h3>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-[#EFECE6] dark:border-[#282420]">
                  <span className="text-[#7C7469] dark:text-[#A69D92]">Категория</span>
                  <span className="text-[#1E1B18] dark:text-[#F7F5F0] capitalize">{item.category}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#EFECE6] dark:border-[#282420]">
                  <span className="text-[#7C7469] dark:text-[#A69D92]">Цвет</span>
                  <span className="text-[#1E1B18] dark:text-[#F7F5F0]">{item.color}</span>
                </div>
                {item.material && (
                  <div className="flex justify-between py-1 border-b border-[#EFECE6] dark:border-[#282420]">
                    <span className="text-[#7C7469] dark:text-[#A69D92]">Материал</span>
                    <span className="text-[#1E1B18] dark:text-[#F7F5F0]">{item.material}</span>
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
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.14em] font-medium transition-colors"
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
