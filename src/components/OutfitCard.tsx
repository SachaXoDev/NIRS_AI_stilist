import { useState } from 'react';
import type { WardrobeItem } from '../types';
import { ExternalLink, Bookmark, Share2, Sparkles, Check, ArrowRight } from 'lucide-react';
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
        colors: ['#78716c', '#a8a29e', '#d6d3d1', '#1c1917'],
      });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`Образ: ${outfit.title} — ${outfit.description}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-5 rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/90 dark:border-stone-800 p-5 sm:p-6 shadow-sm hover:shadow-md transition-all duration-300">
      {/* Top Header */}
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-stone-100 dark:border-stone-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium tracking-wide uppercase bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
              <Sparkles className="w-2.5 h-2.5 text-stone-500" />
              Совпадение {outfit.matchScore}%
            </span>
            <span className="text-xs text-stone-400 dark:text-stone-500">
              • {outfit.occasion}
            </span>
          </div>
          <h4 className="text-lg sm:text-xl font-serif-luxury font-medium text-stone-900 dark:text-stone-100 tracking-tight">
            {outfit.title}
          </h4>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={handleShare}
            title="Скопировать описание"
            className="p-2 rounded-xl text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> : <Share2 className="w-4 h-4" />}
          </button>
          <button
            onClick={handleSave}
            title={isSaved ? 'Сохранено' : 'Сохранить образ'}
            className={`p-2 rounded-xl transition-colors ${
              isSaved
                ? 'bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900'
                : 'text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100 hover:bg-stone-100 dark:hover:bg-stone-800'
            }`}
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
          </button>
        </div>
      </div>

      {/* Wardrobe Items Gallery */}
      <div className="my-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-semibold tracking-wider text-stone-400 dark:text-stone-500 uppercase">
            Вещи из вашего гардероба в этом образе ({outfit.items.length})
          </span>
          <span className="text-[11px] text-stone-400 dark:text-stone-500">
            Нажмите на вещь для деталей
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {outfit.items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectItem?.(item)}
              className="group relative flex flex-col rounded-xl bg-stone-50/70 dark:bg-stone-950/40 border border-stone-200/70 dark:border-stone-800/80 overflow-hidden cursor-pointer hover:border-stone-400 dark:hover:border-stone-600 transition-all duration-200"
            >
              <div className="aspect-[4/5] w-full overflow-hidden bg-stone-100 dark:bg-stone-900">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
              </div>
              <div className="p-2.5 flex flex-col justify-between flex-1">
                <span className="text-xs font-medium text-stone-800 dark:text-stone-200 line-clamp-1 leading-snug">
                  {item.title}
                </span>
                <div className="flex items-center justify-between mt-1 text-[10px] text-stone-400 dark:text-stone-500">
                  <span className="truncate">{item.brand || item.color}</span>
                  <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity text-stone-700 dark:text-stone-300" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stylist Breakdown */}
      <div className="space-y-3 pt-3 border-t border-stone-100 dark:border-stone-800">
        <div className="rounded-xl bg-stone-50 dark:bg-stone-950/50 p-4 border border-stone-150 dark:border-stone-800/80">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-stone-800 dark:text-stone-200 mb-1.5">
            <span>Композиция и колористика</span>
          </div>
          <p className="text-xs sm:text-sm text-stone-600 dark:text-stone-300 leading-relaxed">
            {outfit.stylistReasoning}
          </p>
        </div>

        {outfit.confidenceTips?.length > 0 && (
          <div className="rounded-xl bg-stone-50 dark:bg-stone-950/50 p-4 border border-stone-150 dark:border-stone-800/80">
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-800 dark:text-stone-200 mb-2">
              Советы по стилизации:
            </div>
            <ul className="space-y-1.5">
              {outfit.confidenceTips.map((tip, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-stone-600 dark:text-stone-300 leading-relaxed">
                  <ArrowRight className="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" />
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
