import React from 'react';
import type { WardrobeItem } from '../types';
import { X, Sparkles, ShieldCheck } from 'lucide-react';

interface ItemDetailModalProps {
  item: WardrobeItem | null;
  onClose: () => void;
  onAskAboutItem: (item: WardrobeItem) => void;
}

export const ItemDetailModal: React.FC<ItemDetailModalProps> = ({
  item,
  onClose,
  onAskAboutItem,
}) => {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl bg-neutral-900 border border-neutral-800 overflow-hidden shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 p-2 rounded-full bg-neutral-950/70 text-neutral-300 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="aspect-video w-full overflow-hidden bg-neutral-950 relative">
          <img
            src={item.imageUrl}
            alt={item.title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-neutral-900 via-transparent to-transparent" />
        </div>

        <div className="p-6 -mt-6 relative">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
              {item.category.toUpperCase()}
            </span>
            {item.brand && (
              <span className="text-xs text-neutral-400">Бренд: {item.brand}</span>
            )}
          </div>

          <h3 className="text-xl font-bold text-white mb-2">{item.title}</h3>

          <div className="space-y-3 my-4 text-xs sm:text-sm text-neutral-300">
            {item.material && (
              <div className="flex justify-between border-b border-neutral-800 pb-2">
                <span className="text-neutral-400">Материал:</span>
                <span className="font-medium text-neutral-200">{item.material}</span>
              </div>
            )}
            <div className="flex justify-between border-b border-neutral-800 pb-2">
              <span className="text-neutral-400">Цвет:</span>
              <span className="font-medium text-neutral-200">{item.color}</span>
            </div>
            <div className="flex justify-between border-b border-neutral-800 pb-2">
              <span className="text-neutral-400">Сезонность:</span>
              <span className="font-medium text-neutral-200">{item.season}</span>
            </div>
            {item.embeddingSnippet && (
              <div className="rounded-xl bg-neutral-950/70 p-3 border border-neutral-800 text-xs">
                <div className="text-neutral-400 font-medium mb-1 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  RAG Векторное описание вещи:
                </div>
                <p className="text-neutral-300">{item.embeddingSnippet}</p>
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-1.5 mb-6">
            {item.tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2 py-1 rounded-lg text-xs bg-neutral-800 text-neutral-300 border border-neutral-700/60"
              >
                #{tag}
              </span>
            ))}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                onAskAboutItem(item);
                onClose();
              }}
              className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 font-semibold text-xs sm:text-sm text-white flex items-center justify-center gap-2 shadow-lg shadow-rose-500/20 transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>Подобрать образ с этой вещью</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
