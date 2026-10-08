import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage, WardrobeItem } from '../types';
import { OutfitCard } from './OutfitCard';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Compass,
  CloudSun,
  Briefcase,
  Coffee,
  Heart,
  RotateCcw,
  CheckCircle,
} from 'lucide-react';

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onResetChat: () => void;
  onSelectItem: (item: WardrobeItem) => void;
}

const QUICK_PROMPTS = [
  {
    icon: <Briefcase className="w-3.5 h-3.5 text-blue-400" />,
    label: 'Деловая встреча',
    text: 'Подбери элегантный и строгий образ для важной деловой встречи в офисе.',
  },
  {
    icon: <CloudSun className="w-3.5 h-3.5 text-amber-400" />,
    label: 'Дождь и +12°C',
    text: 'Что надеть сегодня? На улице ветрено, дождь и около +12 градусов.',
  },
  {
    icon: <Coffee className="w-3.5 h-3.5 text-rose-400" />,
    label: 'Повседневный casual',
    text: 'Собери расслабленный стильный лук на прогулку по городу и в кофейню с друзьями.',
  },
  {
    icon: <Heart className="w-3.5 h-3.5 text-pink-400" />,
    label: 'Свидание вечером',
    text: 'Посоветуй привлекательный образ на романтический ужин в ресторан.',
  },
];

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onResetChat,
  onSelectItem,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText);
    setInputText('');
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-neutral-950 overflow-hidden relative">
      {/* Top Chat Header */}
      <div className="h-14 border-b border-neutral-800 px-6 flex items-center justify-between shrink-0 bg-neutral-950/80 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-rose-500 to-amber-500 p-0.5 flex items-center justify-center">
            <div className="w-full h-full bg-neutral-900 rounded-full flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-rose-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-tight">AI Fashion Stylist</h2>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <p className="text-[11px] text-neutral-400">RAG-powered персональный подбор луков</p>
          </div>
        </div>

        <button
          onClick={onResetChat}
          title="Начать новый диалог"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-neutral-400 hover:text-white bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Новый диалог</span>
        </button>
      </div>

      {/* Messages Scrollable Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.map((message) => {
          const isUser = message.sender === 'user';
          return (
            <div
              key={message.id}
              className={`flex gap-3 sm:gap-4 max-w-4xl mx-auto ${
                isUser ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${
                  isUser
                    ? 'bg-rose-500 text-white'
                    : 'bg-neutral-850 text-rose-400 border border-neutral-700'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Content Bubble */}
              <div
                className={`flex-1 rounded-2xl p-4 sm:p-5 transition-all ${
                  isUser
                    ? 'bg-gradient-to-r from-rose-600 to-rose-700 text-white max-w-xl ml-auto rounded-tr-none'
                    : 'bg-neutral-900/90 text-neutral-100 border border-neutral-800 rounded-tl-none shadow-lg'
                }`}
              >
                <div className="text-sm sm:text-base leading-relaxed whitespace-pre-line">
                  {message.text}
                </div>

                {/* Outfit card if assistant recommended one */}
                {message.suggestedOutfit && (
                  <OutfitCard
                    outfit={message.suggestedOutfit}
                    onSelectItem={onSelectItem}
                  />
                )}

                <div
                  className={`text-[10px] mt-2 flex items-center gap-1.5 ${
                    isUser ? 'text-rose-200 justify-end' : 'text-neutral-500'
                  }`}
                >
                  <span>{message.timestamp}</span>
                  {isUser && <CheckCircle className="w-3 h-3" />}
                </div>
              </div>
            </div>
          );
        })}

        {/* Thinking Indicator */}
        {isLoading && (
          <div className="flex gap-4 max-w-4xl mx-auto">
            <div className="w-8 h-8 rounded-full bg-neutral-850 text-rose-400 border border-neutral-700 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="rounded-2xl rounded-tl-none bg-neutral-900 border border-neutral-800 p-4 text-sm text-neutral-400 flex items-center gap-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-rose-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-rose-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-rose-500 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-neutral-300">
                ИИ-Стилист ищет подходящие вещи в вашем гардеробе через RAG...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Sticky Area: Quick chips + Input Bar */}
      <div className="p-4 sm:p-5 border-t border-neutral-850 bg-neutral-950/95 backdrop-blur-md">
        <div className="max-w-4xl mx-auto space-y-3">
          {/* Quick Prompts */}
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none pb-1">
            <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1 shrink-0">
              <Compass className="w-3.5 h-3.5 text-neutral-400" />
              Идеи:
            </span>
            {QUICK_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                disabled={isLoading}
                onClick={() => onSendMessage(p.text)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 hover:border-neutral-700 text-xs text-neutral-300 hover:text-white transition-all shrink-0 cursor-pointer disabled:opacity-50"
              >
                {p.icon}
                <span>{p.label}</span>
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoading}
              placeholder="Спросите стилиста (например: «Что надеть на собеседование в IT-компанию?»)..."
              className="w-full rounded-2xl bg-neutral-900/90 border border-neutral-800 focus:border-rose-500/80 px-4 py-3.5 pr-14 text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none transition-all shadow-inner"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2 p-2 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:from-rose-600 hover:to-pink-600 transition-all shadow-md shadow-rose-500/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="text-center text-[10px] text-neutral-500">
            ИИ подбирает сочетания исключительно из загруженных в гардероб вещей на основе семантического сходства
          </div>
        </div>
      </div>
    </div>
  );
};
