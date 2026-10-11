import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, WardrobeItem } from '../types';
import { OutfitCard } from './OutfitCard';
import {
  Send,
  RotateCcw,
  Sun,
  Moon,
  ArrowUpRight,
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
    text: 'Подбери сдержанный, статусный образ для встречи в офисе в духе лаконичной классики 12 STOREEZ.',
  },
  {
    title: 'Прохладный день и дождь',
    text: 'Что надеть на прогулку? На улице ветрено, около +12 градусов. Нужен теплый, многослойный аутфит.',
  },
  {
    title: 'Кофе в городе',
    text: 'Собери расслабленный повседневный монохромный образ для неспешного выходного дня в городе.',
  },
  {
    title: 'Вечерний ужин',
    text: 'Посоветуй утонченный комплект для вечернего выхода в ресторан с акцентом на текстуры.',
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
    <div className="flex-1 flex flex-col h-full bg-[#FAF7F2] dark:bg-[#191715] overflow-hidden relative transition-colors duration-300">
      {/* Top Header */}
      <div className="h-16 border-b border-[#E3DCD1] dark:border-[#2F2C28] px-6 sm:px-10 flex items-center justify-between shrink-0 bg-[#FAF7F2]/90 dark:bg-[#191715]/90 backdrop-blur-md z-10">
        <div>
          <h2 className="text-base font-serif-luxury tracking-wide text-[#2C2926] dark:text-[#EAE6DF] font-light uppercase">
            Персональный диалог со стилистом
          </h2>
          <p className="text-[10px] tracking-[0.16em] uppercase text-[#8A7F73] dark:text-[#9E9283]">
            Капсульные сочетания • Сдержанная роскошь
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Theme Switcher */}
          <button
            onClick={toggleTheme}
            title={theme === 'light' ? 'Включить вечерний режим' : 'Включить дневной режим'}
            className="p-2 text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#EAE6DF] transition-colors"
          >
            {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>

          <button
            onClick={onResetChat}
            title="Очистить диалог"
            className="flex items-center gap-2 px-3 py-1.5 border border-[#D5CBC0] dark:border-[#38332E] text-[11px] uppercase tracking-[0.12em] text-[#6E6357] dark:text-[#A89C8F] hover:border-[#2C2926] dark:hover:border-[#EAE6DF] transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span className="hidden sm:inline">Новый запрос</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto px-6 sm:px-12 py-8 space-y-8">
        {messages.map((message) => {
          const isUser = message.sender === 'user';
          return (
            <div
              key={message.id}
              className={`flex gap-4 max-w-4xl mx-auto ${
                isUser ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`flex flex-col max-w-2xl ${
                  isUser ? 'items-end' : 'items-start'
                }`}
              >
                {/* Bubble in 12 STOREEZ minimal aesthetic */}
                <div
                  className={`p-5 sm:p-6 transition-all leading-relaxed ${
                    isUser
                      ? 'bg-[#2C2926] dark:bg-[#EAE6DF] text-[#F7F4EE] dark:text-[#1C1A18] text-sm sm:text-base font-light tracking-normal shadow-xs'
                      : 'bg-[#F2ECE1] dark:bg-[#23201D] text-[#2C2926] dark:text-[#EAE6DF] text-sm sm:text-base border border-[#DDD3C4] dark:border-[#34302B]'
                  }`}
                >
                  <p className="whitespace-pre-line font-light">{message.text}</p>

                  {/* Generated Outfit */}
                  {message.suggestedOutfit && (
                    <OutfitCard
                      outfit={message.suggestedOutfit}
                      onSelectItem={onSelectItem}
                    />
                  )}
                </div>

                <span className="text-[10px] tracking-[0.12em] uppercase text-[#9B8F82] dark:text-[#786E63] mt-2 px-1">
                  {message.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex max-w-4xl mx-auto justify-start">
            <div className="bg-[#F2ECE1] dark:bg-[#23201D] border border-[#DDD3C4] dark:border-[#34302B] p-4 text-xs text-[#6E6357] dark:text-[#A89C8F] flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-[#8A7F73] animate-pulse" />
              <span className="font-serif-luxury text-sm italic tracking-wide">
                Стилист подбирает пропорции и фактуры из вашей капсулы...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-6 sm:p-8 border-t border-[#E3DCD1] dark:border-[#2F2C28] bg-[#F7F4EE]/95 dark:bg-[#191715]/95 backdrop-blur-md">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Quick Ideas */}
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none pb-1">
            <span className="text-[10px] tracking-[0.16em] uppercase text-[#8A7F73] dark:text-[#A89C8F] shrink-0 font-medium mr-1">
              Сценарии:
            </span>
            {QUICK_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                disabled={isLoading}
                onClick={() => onSendMessage(p.text)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#D5CBC0] dark:border-[#38332E] hover:border-[#2C2926] dark:hover:border-[#EAE6DF] text-[11px] font-light text-[#574E43] dark:text-[#D5CCC0] tracking-wide whitespace-nowrap transition-all shrink-0 disabled:opacity-40"
              >
                <span>{p.title}</span>
                <ArrowUpRight className="w-3 h-3 text-[#8A7F73]" />
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
              placeholder="Напишите стилисту (например: «С чем носить бежевый тренч весной?»)..."
              className="w-full bg-[#FFFFFF] dark:bg-[#23201D] border border-[#DDD3C4] dark:border-[#38332E] focus:border-[#2C2926] dark:focus:border-[#EAE6DF] px-5 py-4 pr-14 text-sm text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none transition-colors"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2.5 p-2.5 bg-[#2C2926] hover:bg-[#423D38] dark:bg-[#EAE6DF] dark:hover:bg-[#FFFFFF] text-white dark:text-[#1C1A18] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center text-[10px] tracking-[0.16em] uppercase text-[#9B8F82] dark:text-[#786E63]">
            Капсульный подход • Идеальная сочетаемость вещей
          </p>
        </div>
      </div>
    </div>
  );
};
