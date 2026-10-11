import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, WardrobeItem } from '../types';
import { OutfitCard } from './OutfitCard';
import {
  Send,
  RotateCcw,
  Sun,
  Moon,
  ArrowUpRight,
  Briefcase,
  CloudRain,
  Coffee,
  Wine,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onResetChat: () => void;
  onSelectItem: (item: WardrobeItem) => void;
}

const QUICK_PROMPTS = [
  {
    title: 'Деловая встреча',
    text: 'Подбери элегантный и строгий образ для важной деловой встречи в офисе.',
    icon: Briefcase,
    color: 'bg-amber-100/70 text-amber-900 border-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-800',
  },
  {
    title: 'Дождь и +12°C',
    text: 'Что надеть сегодня? На улице ветрено, дождь и около +12 градусов.',
    icon: CloudRain,
    color: 'bg-sky-100/70 text-sky-900 border-sky-200 dark:bg-sky-950/40 dark:text-sky-200 dark:border-sky-800',
  },
  {
    title: 'Городской casual',
    text: 'Собери расслабленный стильный лук на прогулку по городу и в кофейню с друзьями.',
    icon: Coffee,
    color: 'bg-emerald-100/70 text-emerald-900 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-800',
  },
  {
    title: 'Вечерний выход',
    text: 'Посоветуй привлекательный образ на романтический ужин в ресторан.',
    icon: Wine,
    color: 'bg-rose-100/70 text-rose-900 border-rose-200 dark:bg-rose-950/40 dark:text-rose-200 dark:border-rose-800',
  },
];

export const ChatArea = ({
  messages,
  isLoading,
  onSendMessage,
  onResetChat,
  onSelectItem,
}: ChatAreaProps) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { theme, toggleTheme } = useTheme();

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
    <div className="flex-1 flex flex-col h-full bg-gradient-to-b from-stone-50/70 via-rose-50/20 to-stone-50/80 dark:from-stone-950 dark:via-stone-900/60 dark:to-stone-950 overflow-hidden relative transition-colors duration-200">
      {/* Top Header */}
      <div className="h-14 border-b border-rose-200/50 dark:border-stone-800 px-5 sm:px-8 flex items-center justify-between shrink-0 bg-white/70 dark:bg-stone-950/80 backdrop-blur-md z-10 shadow-2xs">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-base font-serif-luxury font-medium tracking-tight text-stone-900 dark:text-stone-100 flex items-center gap-2">
              Персональный стилист
            </h2>
            <div className="flex items-center gap-1.5 text-[11px] text-rose-700 dark:text-rose-300 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-600" />
              <span>Умный подбор по вашей одежде</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Theme Switcher */}
          <button
            onClick={toggleTheme}
            title={theme === 'light' ? 'Переключить на темную тему' : 'Переключить на светлую тему'}
            className="p-2 rounded-xl text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-rose-100/60 dark:hover:bg-stone-800 transition-colors"
          >
            {theme === 'light' ? <Moon className="w-4 h-4 text-amber-700" /> : <Sun className="w-4 h-4 text-amber-400" />}
          </button>

          <button
            onClick={onResetChat}
            title="Очистить и начать заново"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs text-stone-700 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 hover:border-rose-300 dark:hover:border-stone-700 transition-colors shadow-2xs"
          >
            <RotateCcw className="w-3.5 h-3.5 text-stone-400" />
            <span className="hidden sm:inline">Новый диалог</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6">
        {messages.map((message) => {
          const isUser = message.sender === 'user';
          return (
            <div
              key={message.id}
              className={`flex gap-3 sm:gap-4 max-w-3xl mx-auto ${
                isUser ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`flex flex-col max-w-2xl ${
                  isUser ? 'items-end' : 'items-start'
                }`}
              >
                {/* Bubble */}
                <div
                  className={`rounded-2xl p-4 sm:p-5 transition-all leading-relaxed ${
                    isUser
                      ? 'bg-gradient-to-r from-stone-900 to-rose-950 dark:from-stone-100 dark:to-rose-100 text-white dark:text-stone-900 rounded-br-none text-sm sm:text-base font-normal shadow-md'
                      : 'bg-white/95 dark:bg-stone-900 text-stone-800 dark:text-stone-200 rounded-bl-none text-sm sm:text-base border border-stone-200/80 dark:border-stone-800 shadow-sm'
                  }`}
                >
                  <p className="whitespace-pre-line">{message.text}</p>

                  {/* Generated Outfit */}
                  {message.suggestedOutfit && (
                    <OutfitCard
                      outfit={message.suggestedOutfit}
                      onSelectItem={onSelectItem}
                    />
                  )}
                </div>

                <span className="text-[10px] text-stone-400 dark:text-stone-500 mt-1.5 px-1">
                  {message.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex max-w-3xl mx-auto justify-start">
            <div className="rounded-2xl rounded-bl-none bg-white dark:bg-stone-900 border border-rose-200/80 dark:border-stone-800 p-4 text-xs text-rose-900 dark:text-rose-200 flex items-center gap-3 shadow-sm">
              <div className="flex space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-600 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-rose-600 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="font-serif-luxury text-sm italic font-medium">
                Стилист подбирает гармоничный образ из вашего гардероба...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 sm:p-6 border-t border-rose-200/50 dark:border-stone-800 bg-white/80 dark:bg-stone-950/90 backdrop-blur-md">
        <div className="max-w-3xl mx-auto space-y-3">
          {/* Quick Ideas */}
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none pb-0.5">
            <span className="text-[10px] font-bold tracking-wider text-rose-800 dark:text-rose-300 uppercase shrink-0">
              Поводы:
            </span>
            {QUICK_PROMPTS.map((p, idx) => {
              const IconComp = p.icon;
              return (
                <button
                  key={idx}
                  disabled={isLoading}
                  onClick={() => onSendMessage(p.text)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium transition-all hover:scale-105 shrink-0 disabled:opacity-40 shadow-2xs ${p.color}`}
                >
                  <IconComp className="w-3.5 h-3.5" />
                  <span>{p.title}</span>
                  <ArrowUpRight className="w-3 h-3 opacity-60" />
                </button>
              );
            })}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoading}
              placeholder="Спросите стилиста (например: «Что надеть в офис на деловую встречу?»)..."
              className="w-full rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/90 dark:border-stone-800 focus:border-rose-600 dark:focus:border-rose-400 focus:ring-2 focus:ring-rose-500/20 px-4 py-3.5 pr-14 text-sm text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-none transition-all shadow-sm"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2 p-2 rounded-xl bg-gradient-to-r from-rose-700 to-amber-700 hover:from-rose-800 hover:to-amber-800 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center text-[11px] text-stone-500 dark:text-stone-400">
            ИИ подбирает комплекты только из вещей вашего личного гардероба
          </p>
        </div>
      </div>
    </div>
  );
};
