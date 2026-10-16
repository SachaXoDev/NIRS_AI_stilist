import type { OutfitLook, WardrobeItem } from '../types';
import { Bookmark, Sparkles, Trash2 } from 'lucide-react';

interface SavedOutfitsViewProps {
  savedOutfits: OutfitLook[];
  onRemoveOutfit: (outfitId: string) => void;
  onSelectItem: (item: WardrobeItem) => void;
  onGoToChat: () => void;
}

export const SavedOutfitsView = ({
  savedOutfits,
  onRemoveOutfit,
  onSelectItem,
  onGoToChat,
}: SavedOutfitsViewProps) => {
  return (
    <div className="flex-1 flex flex-col w-full h-full max-w-7xl mx-auto overflow-hidden px-4 sm:px-8 py-4 sm:py-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#DFD9CF] dark:border-[#2E2A26] shrink-0">
        <div>
          <span className="text-[10px] tracking-[0.2em] uppercase text-[#8A8175] dark:text-[#A69D92] block mb-1 font-normal">
            12 STOREEZ • AI LOOKBOOK
          </span>
          <h2 className="text-xl sm:text-2xl font-light tracking-wide text-[#1E1B18] dark:text-[#F7F5F0]">
            AI Lookbook
          </h2>
          <p className="text-xs text-[#7C7469] dark:text-[#A69D92] mt-0.5 font-light">
            Персональные формулы стайлинга и капсулы, отобранные вами
          </p>
        </div>

        <div className="text-xs text-[#7C7469] dark:text-[#A69D92] font-normal uppercase tracking-wider">
          Всего в подборке: <strong>{savedOutfits.length}</strong>
        </div>
      </div>

      {/* Grid of Saved Outfits */}
      <div className="flex-1 overflow-y-auto py-6">
        {savedOutfits.length === 0 ? (
          <div className="text-center py-24 px-4 flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full border border-[#DFD9CF] dark:border-[#38332E] flex items-center justify-center mb-3 text-[#8A8175]">
              <Bookmark className="w-5 h-5" />
            </div>
            <p className="text-xs font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-1">
              В вашем AI Lookbook пока нет сохраненных образов
            </p>
            <p className="text-[11px] text-[#7C7469] dark:text-[#A69D92] max-w-xs mb-5 font-light leading-relaxed">
              Во время диалога со стилистом нажимайте на значок закладки в карточке лука, чтобы сохранить его сюда
            </p>
            <button
              onClick={onGoToChat}
              className="px-5 py-2.5 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-[11px] font-normal tracking-[0.14em] uppercase transition-colors cursor-pointer"
            >
              Перейти к стилисту
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {savedOutfits.map((outfit) => (
              <div
                key={outfit.id}
                className="bg-[#FCFAF7] dark:bg-[#1E1C19] border border-[#DFD9CF] dark:border-[#2E2A26] p-5 flex flex-col justify-between"
              >
                <div>
                  {/* Top line: occasion & delete action */}
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[10px] uppercase tracking-[0.18em] text-[#8A8175] dark:text-[#A69D92] font-normal">
                      {outfit.occasion || 'Капсула'}
                    </span>
                    <button
                      onClick={() => onRemoveOutfit(outfit.id)}
                      title="Убрать из сохраненных"
                      className="p-1 text-[#8A8175] hover:text-red-600 dark:hover:text-red-400 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <h3 className="text-sm font-medium tracking-wide text-[#1E1B18] dark:text-[#F7F5F0] mb-4">
                    {outfit.title}
                  </h3>

                  {/* Outfit Items in Row */}
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mb-4">
                    {outfit.items.map((item) => {
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
                          onClick={() => onSelectItem(item)}
                          className="group bg-[#F6F4F0] dark:bg-[#24211E] border border-[#EBE7DF] dark:border-[#2F2B27] p-1.5 cursor-pointer flex flex-col"
                        >
                          <div className="aspect-[3/4] w-full overflow-hidden bg-[#ECE7DE] dark:bg-[#1A1816] flex items-center justify-center mb-1">
                            <img
                              src={item.imageUrl || fallbackSvg}
                              alt={item.title}
                              onError={(e) => {
                                (e.currentTarget as HTMLImageElement).src = fallbackSvg;
                              }}
                              className="w-full h-full object-contain"
                            />
                          </div>
                          <span className="text-[10px] text-[#1E1B18] dark:text-[#F7F5F0] truncate font-light">
                            {item.title}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Stylist Reasoning */}
                  {outfit.stylistReasoning && (
                    <p className="text-xs text-[#6B6359] dark:text-[#A69D92] leading-relaxed mb-3 font-light border-t border-[#EFECE6] dark:border-[#282420] pt-3">
                      {outfit.stylistReasoning}
                    </p>
                  )}
                </div>

                {/* Match Score Badge */}
                <div className="pt-3 border-t border-[#EFECE6] dark:border-[#282420] flex items-center justify-between text-[11px] text-[#8A8175]">
                  <span className="flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                    <span>Совместимость кроя: {outfit.matchScore}%</span>
                  </span>
                  <span>{outfit.items.length} предм.</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
