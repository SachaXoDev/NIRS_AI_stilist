import { useState } from 'react';
import type { WardrobeItem } from '../types';
import { Bookmark, Share2, Check } from 'lucide-react';
import confetti from 'canvas-confetti';

interface OutfitCardProps {
  outfit: {
    id: string;
    title: string;
    description: string;
    occasion: string;
    items: WardrobeItem[];
    stylistReasoning: string;
    matchScore: number;
    confidenceTips: string[];
  };
  onSelectItem?: (item: WardrobeItem) => void;
}

export const OutfitCard = ({ outfit, onSelectItem }: OutfitCardProps) => {
  const [isSaved, setIsSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSave = () => {
    setIsSaved(!isSaved);
    if (!isSaved) {
      confetti({
        particleCount: 30,
        spread: 40,
        origin: { y: 0.8 },
        colors: ['#111111', '#888888'],
      });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`12 STOREEZ | ${outfit.title}: ${outfit.description}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-5 border border-[#E5E5E5] dark:border-[#2B2B2B] bg-[#FFFFFF] dark:bg-[#161616] p-4 sm:p-6 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-[#EBEBEB] dark:border-[#262626]">
        <div>
          <span className="text-[10px] tracking-[0.16em] uppercase text-[#767676] dark:text-[#888888] font-normal block mb-1">
            {outfit.occasion}
          </span>
          <h4 className="text-sm sm:text-base font-medium text-[#111111] dark:text-[#FFFFFF] tracking-normal">
            {outfit.title}
          </h4>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleShare}
            title="Скопировать"
            className="p-1.5 text-[#767676] hover:text-[#111111] dark:hover:text-[#FFFFFF] transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-[#111111] dark:text-[#FFFFFF]" /> : <Share2 className="w-4 h-4" />}
          </button>
          <button
            onClick={handleSave}
            title={isSaved ? 'Сохранено' : 'Сохранить'}
            className="p-1.5 text-[#767676] hover:text-[#111111] dark:hover:text-[#FFFFFF] transition-colors"
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current text-[#111111] dark:text-[#FFFFFF]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Wardrobe Items Gallery in 12 STOREEZ format */}
      <div className="my-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {outfit.items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectItem?.(item)}
              className="group flex flex-col bg-[#FAFAFA] dark:bg-[#1C1C1C] cursor-pointer"
            >
              <div className="aspect-[3/4] w-full overflow-hidden bg-[#F2F2F2] dark:bg-[#191919]">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="h-full w-full object-cover group-hover:scale-102 transition-transform duration-300"
                />
              </div>
              <div className="p-2.5 flex flex-col justify-between flex-1">
                <span className="text-[11px] font-normal text-[#111111] dark:text-[#EDEDED] line-clamp-1">
                  {item.title}
                </span>
                <span className="text-[10px] text-[#767676] dark:text-[#888888] mt-0.5">
                  {item.color}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stylist Breakdown */}
      <div className="space-y-3 pt-3 border-t border-[#EBEBEB] dark:border-[#262626]">
        <div className="text-xs text-[#444444] dark:text-[#CCCCCC] leading-relaxed">
          {outfit.stylistReasoning}
        </div>

        {outfit.confidenceTips?.length > 0 && (
          <ul className="space-y-1.5 pt-2">
            {outfit.confidenceTips.map((tip, idx) => (
              <li key={idx} className="flex items-start gap-2 text-xs text-[#666666] dark:text-[#AAAAAA] leading-normal">
                <span className="w-1 h-1 rounded-full bg-[#888888] mt-1.5 shrink-0" />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
