import React, { useState } from 'react';
import type { WardrobeItem } from '../types';
import { ExternalLink, Sparkles, CheckCircle2, Bookmark, Share2 } from 'lucide-react';
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

export const OutfitCard: React.FC<OutfitCardProps> = ({ outfit, onSelectItem }) => {
  const [isSaved, setIsSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSave = () => {
    setIsSaved(!isSaved);
    if (!isSaved) {
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 },
        colors: ['#f43f5e', '#fb7185', '#fda4af', '#fcd34d'],
      });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`Образ: ${outfit.title} — ${outfit.description}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-4 rounded-2xl bg-neutral-900/90 border border-neutral-800 p-5 shadow-xl backdrop-blur-sm transition-all hover:border-neutral-700">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-neutral-800/80 pb-3">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 text-xs font-medium mb-1.5 border border-rose-500/20">
            <Sparkles className="w-3 h-3" />
            <span>Совпадение RAG {outfit.matchScore}%</span>
          </div>
          <h4 className="text-base sm:text-lg font-semibold text-white tracking-tight">
            {outfit.title}
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleShare}
            title="Скопировать описание"
            className="p-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition-colors"
          >
            {copied ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4" />}
          </button>
          <button
            onClick={handleSave}
            title={isSaved ? 'Сохранено' : 'Сохранить образ'}
            className={`p-2 rounded-lg transition-colors ${
              isSaved
                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                : 'bg-neutral-800 hover:bg-neutral-700 text-neutral-300'
            }`}
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-rose-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Grid of clothes in this outfit */}
      <div className="my-4">
        <p className="text-xs uppercase tracking-wider font-semibold text-neutral-400 mb-2.5">
          Вещи из вашего гардероба в этом образе ({outfit.items.length})
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {outfit.items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectItem?.(item)}
              className="group relative flex flex-col rounded-xl bg-neutral-800/70 border border-neutral-700/60 overflow-hidden cursor-pointer hover:border-rose-500/50 hover:shadow-lg transition-all duration-200"
            >
              <div className="aspect-square w-full overflow-hidden bg-neutral-900">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              </div>
              <div className="p-2 flex flex-col justify-between flex-1">
                <span className="text-xs font-medium text-neutral-200 line-clamp-2 leading-tight">
                  {item.title}
                </span>
                <span className="text-[10px] text-neutral-400 mt-1 flex items-center justify-between">
                  <span className="truncate">{item.brand || item.color}</span>
                  <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity text-rose-400" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stylist Reasoning and Tips */}
      <div className="space-y-2 pt-2 border-t border-neutral-800/70 text-sm">
        <div className="rounded-xl bg-neutral-950/60 p-3 border border-neutral-800">
          <span className="text-xs font-semibold text-rose-400 uppercase tracking-wide block mb-1">
            💡 Разбор стилиста (Колористика и композиция):
          </span>
          <p className="text-neutral-300 text-xs sm:text-sm leading-relaxed">
            {outfit.stylistReasoning}
          </p>
        </div>

        {outfit.confidenceTips?.length > 0 && (
          <div className="rounded-xl bg-neutral-950/40 p-3 border border-neutral-800">
            <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide block mb-1">
              ✨ Фирменные приемы стайлинга:
            </span>
            <ul className="list-disc list-inside space-y-1 text-xs text-neutral-300">
              {outfit.confidenceTips.map((tip, idx) => (
                <li key={idx} className="leading-relaxed">
                  {tip}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
