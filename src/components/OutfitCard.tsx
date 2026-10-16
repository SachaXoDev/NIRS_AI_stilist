import { useState } from 'react';
import type { WardrobeItem, OutfitLook } from '../types';
import { Bookmark, Share2, Check } from 'lucide-react';

interface OutfitCardProps {
  outfit: OutfitLook;
  onSelectItem?: (item: WardrobeItem) => void;
  isSaved?: boolean;
  onToggleSave?: (outfit: OutfitLook) => void;
}

export const OutfitCard = ({
  outfit,
  onSelectItem,
  isSaved = false,
  onToggleSave,
}: OutfitCardProps) => {
  const [copied, setCopied] = useState(false);

  const handleShare = () => {
    navigator.clipboard.writeText(`12 STOREEZ | ${outfit.title}: ${outfit.description}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-5 border border-[#DFD9CF] dark:border-[#2E2A26] bg-[#FCFAF7] dark:bg-[#1C1A18] p-4 sm:p-6 transition-all relative">
      {/* Copied Notification Toast */}
      {copied && (
        <div className="absolute top-2 right-16 bg-[#1E1B18] text-white dark:bg-white dark:text-black text-[10px] tracking-wider uppercase px-2.5 py-1 shadow-md animate-in fade-in duration-150">
          Скопировано
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-[#EFECE6] dark:border-[#282420]">
        <div>
          <span className="text-[10px] tracking-[0.16em] uppercase text-[#7C7469] dark:text-[#A69D92] font-normal block mb-1">
            {outfit.occasion}
          </span>
          <h4 className="text-sm sm:text-base font-medium text-[#1E1B18] dark:text-[#F7F5F0] tracking-normal">
            {outfit.title}
          </h4>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleShare}
            title="Поделиться формулой образа"
            className="p-1.5 text-[#7C7469] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-4 h-4 text-[#1E1B18] dark:text-[#F7F5F0]" /> : <Share2 className="w-4 h-4" />}
          </button>
          <button
            onClick={() => onToggleSave?.(outfit)}
            title={isSaved ? 'Убрать из сохраненных' : 'Сохранить в лукбук'}
            className="p-1.5 text-[#7C7469] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer"
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current text-[#1E1B18] dark:text-[#F7F5F0]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Wardrobe Items Gallery */}
      <div className="my-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
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
                onClick={() => onSelectItem?.(item)}
                className="group flex flex-col bg-[#F6F4F0] dark:bg-[#221F1C] border border-[#EBE7DF] dark:border-[#2D2925] cursor-pointer"
              >
                <div className="aspect-[3/4] w-full overflow-hidden bg-[#ECE7DE] dark:bg-[#1A1816] flex items-center justify-center p-2">
                  <img
                    src={item.imageUrl || fallbackSvg}
                    alt={item.title}
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).src = fallbackSvg;
                    }}
                    className="h-full w-full object-contain group-hover:scale-102 transition-transform duration-300"
                  />
                </div>
                <div className="p-2.5 flex flex-col justify-between flex-1">
                  <span className="text-[11px] font-normal text-[#1E1B18] dark:text-[#F7F5F0] line-clamp-1">
                    {item.title}
                  </span>
                  <span className="text-[10px] text-[#7C7469] dark:text-[#A69D92] mt-0.5">
                    {item.color}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stylist Breakdown */}
      <div className="space-y-3 pt-3 border-t border-[#EFECE6] dark:border-[#282420]">
        <div className="text-xs text-[#38332E] dark:text-[#D8D1C7] leading-relaxed font-light">
          {outfit.stylistReasoning}
        </div>

        {outfit.confidenceTips?.length > 0 && (
          <ul className="space-y-1.5 pt-2">
            {outfit.confidenceTips.map((tip, idx) => (
              <li
                key={idx}
                className="text-xs text-[#6B6359] dark:text-[#A69D92] flex items-start gap-2 font-light"
              >
                <span className="text-[#8A8175] select-none">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Match Quality */}
      <div className="mt-4 pt-3 border-t border-[#EFECE6] dark:border-[#282420] flex items-center justify-between text-[11px] text-[#7C7469] dark:text-[#A69D92]">
        <span>Согласованность силуэта: {outfit.matchScore}%</span>
        <span>Капсула 12 STOREEZ</span>
      </div>
    </div>
  );
};
