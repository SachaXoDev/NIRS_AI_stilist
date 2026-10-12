import { useState } from 'react';
import type { WardrobeItem } from '../types';
import { ExternalLink, Bookmark, Share2, Check } from 'lucide-react';
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
        particleCount: 40,
        spread: 50,
        origin: { y: 0.8 },
        colors: ['#111111', '#8C6D4F', '#D5CBC0'],
      });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`Образ 12 STOREEZ: ${outfit.title} — ${outfit.description}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-4 sm:mt-6 border-2 border-[#D8CFC2] dark:border-[#3D372F] bg-[#FAF7F2] dark:bg-[#171513] p-4 sm:p-8 transition-all shadow-xs">
      {/* Editorial Header */}
      <div className="flex items-start justify-between gap-3 sm:gap-6 pb-4 sm:pb-6 border-b border-[#D8CFC2] dark:border-[#332F2A]">
        <div>
          <div className="flex items-center gap-2 sm:gap-3 mb-1.5 sm:mb-2">
            <span className="text-[10px] sm:text-[11px] tracking-[0.18em] uppercase font-bold text-[#111111] dark:text-[#FFFFFF] bg-[#EAE2D3] dark:bg-[#2A2621] px-2 py-0.5 border border-[#C5BBAE] dark:border-[#423C34]">
              Гармония: {outfit.matchScore}%
            </span>
            <span className="w-1 h-1 rounded-full bg-[#111111] dark:bg-[#FFFFFF]" />
            <span className="text-[10px] sm:text-[11px] tracking-[0.14em] uppercase font-semibold text-[#4A4135] dark:text-[#D5CCC0]">
              {outfit.occasion}
            </span>
          </div>
          <h4 className="text-xl sm:text-2xl font-serif-luxury font-medium text-[#111111] dark:text-[#FFFFFF] tracking-wide">
            {outfit.title}
          </h4>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          <button
            onClick={handleShare}
            title="Скопировать формулу образа"
            className="p-1.5 sm:p-2 text-[#4A4135] hover:text-[#111111] dark:text-[#D5CCC0] dark:hover:text-[#FFFFFF] hover:bg-[#EAE2D5] dark:hover:bg-[#282420] transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-[#15803D]" /> : <Share2 className="w-4 h-4" />}
          </button>
          <button
            onClick={handleSave}
            title={isSaved ? 'Сохранено в избранное' : 'Сохранить формулу'}
            className="p-1.5 sm:p-2 text-[#4A4135] hover:text-[#111111] dark:text-[#D5CCC0] dark:hover:text-[#FFFFFF] hover:bg-[#EAE2D5] dark:hover:bg-[#282420] transition-colors"
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current text-[#111111] dark:text-[#FFFFFF]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Wardrobe Items Gallery in 12 STOREEZ Lookbook format */}
      <div className="my-4 sm:my-6">
        <div className="flex items-center justify-between mb-3 sm:mb-4">
          <span className="text-[10px] sm:text-[11px] tracking-[0.18em] uppercase text-[#111111] dark:text-[#FFFFFF] font-bold">
            Комплектация ({outfit.items.length} вещей)
          </span>
          <span className="text-[10px] uppercase tracking-[0.12em] text-[#6B6154] dark:text-[#B5AAA0] font-medium">
            Нажмите для деталей
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2.5 sm:gap-3.5">
          {outfit.items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectItem?.(item)}
              className="group relative flex flex-col bg-[#FFFFFF] dark:bg-[#1E1B18] border border-[#C5BBAE] dark:border-[#38332B] hover:border-[#111111] dark:hover:border-[#FFFFFF] cursor-pointer transition-all duration-200 shadow-2xs"
            >
              <div className="aspect-[3/4] w-full overflow-hidden bg-[#EFE9DF] dark:bg-[#141210] relative">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
              </div>
              <div className="p-2 sm:p-3 flex flex-col justify-between flex-1">
                <span className="text-[8px] sm:text-[9px] tracking-[0.14em] uppercase text-[#6B6154] dark:text-[#B5AAA0] font-semibold mb-0.5">
                  {item.brand || '12 STOREEZ'}
                </span>
                <span className="text-[11px] sm:text-xs font-semibold text-[#111111] dark:text-[#FFFFFF] line-clamp-1 leading-snug">
                  {item.title}
                </span>
                <div className="flex items-center justify-between mt-1.5 pt-1.5 sm:mt-2 sm:pt-2 border-t border-[#EAE2D5] dark:border-[#2D2A26] text-[10px] text-[#4A4135] dark:text-[#D5CCC0] font-medium">
                  <span>{item.color}</span>
                  <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity text-[#111111] dark:text-[#FFFFFF]" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stylist Breakdown */}
      <div className="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-[#D8CFC2] dark:border-[#332F2A]">
        <div className="bg-[#FFFFFF] dark:bg-[#201D1A] p-4 sm:p-5 border border-[#C5BBAE] dark:border-[#3E3830]">
          <div className="text-[10px] sm:text-[11px] tracking-[0.18em] uppercase font-bold text-[#111111] dark:text-[#FFFFFF] mb-2">
            Идея стилизации и баланс фактур
          </div>
          <p className="text-xs sm:text-[14px] text-[#1A1A1A] dark:text-[#ECE7E0] leading-relaxed font-normal">
            {outfit.stylistReasoning}
          </p>
        </div>

        {outfit.confidenceTips?.length > 0 && (
          <div className="p-4 sm:p-5 border border-[#D8CFC2] dark:border-[#38332E] bg-[#F7F4EE]/60 dark:bg-[#1C1A18]/60">
            <div className="text-[10px] sm:text-[11px] tracking-[0.18em] uppercase font-bold text-[#111111] dark:text-[#FFFFFF] mb-2.5">
              Рекомендации стилиста к образу:
            </div>
            <ul className="space-y-2">
              {outfit.confidenceTips.map((tip, idx) => (
                <li key={idx} className="flex items-start gap-2.5 text-xs sm:text-[13px] text-[#1F1B16] dark:text-[#E0D8CB] leading-relaxed font-normal">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#111111] dark:bg-[#FFFFFF] mt-1.5 shrink-0" />
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
