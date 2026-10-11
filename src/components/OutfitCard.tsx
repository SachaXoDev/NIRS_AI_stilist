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
        colors: ['#8A7F73', '#C4A482', '#2C2926'],
      });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`Образ 12 STOREEZ: ${outfit.title} — ${outfit.description}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-6 border border-[#DDD3C4] dark:border-[#38332E] bg-[#F7F4EE] dark:bg-[#1E1B19] p-6 sm:p-8 transition-all">
      {/* Editorial Header */}
      <div className="flex items-start justify-between gap-6 pb-6 border-b border-[#E3DCD1] dark:border-[#2D2A26]">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[10px] tracking-[0.2em] uppercase font-medium text-[#8A7F73] dark:text-[#A89C8F]">
              Гармония капсулы: {outfit.matchScore}%
            </span>
            <span className="w-1 h-1 rounded-full bg-[#8A7F73]" />
            <span className="text-[10px] tracking-[0.16em] uppercase text-[#6B6156] dark:text-[#BFB4A7]">
              {outfit.occasion}
            </span>
          </div>
          <h4 className="text-xl sm:text-2xl font-serif-luxury font-light text-[#2C2926] dark:text-[#F3EEE5] tracking-wide">
            {outfit.title}
          </h4>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleShare}
            title="Скопировать формулу образа"
            className="p-2 text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#F3EEE5] transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-[#4A7C59]" /> : <Share2 className="w-4 h-4" />}
          </button>
          <button
            onClick={handleSave}
            title={isSaved ? 'Сохранено в избранное' : 'Сохранить формулу'}
            className="p-2 text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#F3EEE5] transition-colors"
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current text-[#2C2926] dark:text-[#F3EEE5]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Wardrobe Items Gallery in 12 STOREEZ Lookbook format */}
      <div className="my-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[10px] tracking-[0.18em] uppercase text-[#8A7F73] dark:text-[#A89C8F] font-medium">
            Комплектация ({outfit.items.length} изделия)
          </span>
          <span className="text-[10px] uppercase tracking-[0.12em] text-[#A69B8E]">
            Нажмите на карточку для описания
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3.5">
          {outfit.items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectItem?.(item)}
              className="group relative flex flex-col bg-[#FAF7F2] dark:bg-[#181614] border border-[#DDD3C4] dark:border-[#332F2A] hover:border-[#2C2926] dark:hover:border-[#EAE6DF] cursor-pointer transition-all duration-300"
            >
              <div className="aspect-[3/4] w-full overflow-hidden bg-[#ECE5DB] dark:bg-[#151312]">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
              </div>
              <div className="p-3 flex flex-col justify-between flex-1">
                <span className="text-[10px] tracking-[0.14em] uppercase text-[#8A7F73] mb-0.5">
                  {item.brand || '12 STOREEZ'}
                </span>
                <span className="text-xs font-light text-[#2C2926] dark:text-[#EAE6DF] line-clamp-1 leading-snug">
                  {item.title}
                </span>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#EAE2D5] dark:border-[#2A2622] text-[10px] text-[#8A7F73]">
                  <span>{item.color}</span>
                  <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity text-[#2C2926] dark:text-[#EAE6DF]" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stylist Breakdown */}
      <div className="space-y-4 pt-4 border-t border-[#E3DCD1] dark:border-[#2D2A26]">
        <div className="bg-[#EFE9DF]/60 dark:bg-[#23201D] p-5 border border-[#DDD3C4] dark:border-[#38332E]">
          <div className="text-[10px] tracking-[0.2em] uppercase font-medium text-[#8A7F73] dark:text-[#A89C8F] mb-2">
            Идея стилизации и баланс фактур
          </div>
          <p className="text-xs sm:text-sm text-[#4A433A] dark:text-[#C5BCB1] leading-relaxed font-light">
            {outfit.stylistReasoning}
          </p>
        </div>

        {outfit.confidenceTips?.length > 0 && (
          <div className="p-5 border border-[#E3DCD1] dark:border-[#2F2C28]">
            <div className="text-[10px] tracking-[0.2em] uppercase font-medium text-[#8A7F73] dark:text-[#A89C8F] mb-3">
              Рекомендации стилиста к образу:
            </div>
            <ul className="space-y-2">
              {outfit.confidenceTips.map((tip, idx) => (
                <li key={idx} className="flex items-start gap-3 text-xs text-[#574E43] dark:text-[#B2A89B] leading-relaxed font-light">
                  <span className="w-1 h-1 rounded-full bg-[#8A7F73] mt-2 shrink-0" />
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
