import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, WardrobeItem } from '../types';
import { OutfitCard } from './OutfitCard';
import {
  Send,
  Plus,
  ArrowUpRight,
  Menu,
} from 'lucide-react';

interface ChatAreaProps {
  chatTitle: string;
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onCreateNewChat: () => void;
  onSelectItem: (item: WardrobeItem) => void;
  onOpenChatListModal?: () => void;
  showBackButton?: boolean;
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
  chatTitle,
  messages,
  isLoading,
  onSendMessage,
  onCreateNewChat,
  onSelectItem,
  onOpenChatListModal,
}: ChatAreaProps) => {
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
    <div className="flex-1 flex flex-col h-full bg-[#F5F2EB] dark:bg-[#141210] overflow-hidden relative transition-colors duration-300">
      {/* Top Header */}
      <div className="h-14 sm:h-16 border-b border-[#D8CFC2] dark:border-[#2D2A26] px-4 sm:px-8 flex items-center justify-between shrink-0 bg-[#FAF7F2]/95 dark:bg-[#181614]/95 backdrop-blur-md z-10">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          {/* Mobile button to open Telegram-style chat sidebar */}
          {onOpenChatListModal && (
            <button
              onClick={onOpenChatListModal}
              title="Открыть список диалогов"
              className="md:hidden p-1.5 -ml-1 text-[#111111] dark:text-[#FFFFFF] hover:bg-[#EAE2D5] dark:hover:bg-[#282420] transition-colors flex items-center gap-1.5"
            >
              <Menu className="w-5 h-5 text-[#111111] dark:text-[#FFFFFF]" />
              <span className="text-[11px] uppercase tracking-wider font-semibold text-[#111111] dark:text-[#FFFFFF]">Чаты</span>
            </button>
          )}

          <div className="min-w-0">
            <h2 className="text-xs sm:text-sm font-semibold text-[#111111] dark:text-[#FFFFFF] truncate tracking-tight">
              {chatTitle}
            </h2>
            <p className="text-[9px] sm:text-[10px] tracking-[0.14em] uppercase text-[#6E6457] dark:text-[#B5AAA0] font-medium truncate">
              {messages.length} сообщений в переписке
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onCreateNewChat}
            title="Создать новый чат"
            className="flex items-center gap-1.5 px-3 py-1.5 border border-[#B5A898] dark:border-[#4A433A] bg-white dark:bg-[#221F1C] text-[10px] sm:text-[11px] uppercase tracking-[0.12em] font-medium text-[#111111] dark:text-[#FFFFFF] hover:bg-[#111111] hover:text-white dark:hover:bg-white dark:hover:text-[#111111] transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Новый диалог</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto px-3.5 sm:px-10 py-4 sm:py-8 space-y-4 sm:space-y-8">
        {messages.map((message) => {
          const isUser = message.sender === 'user';
          return (
            <div
              key={message.id}
              className={`flex gap-3 max-w-4xl mx-auto ${
                isUser ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`flex flex-col w-full sm:max-w-2xl ${
                  isUser ? 'items-end' : 'items-start'
                }`}
              >
                {/* Crisp Contrast Message Bubbles */}
                <div
                  className={`p-4 sm:p-6 transition-all leading-relaxed shadow-sm ${
                    isUser
                      ? 'bg-[#141414] dark:bg-[#FFFFFF] text-[#FFFFFF] dark:text-[#111111] text-xs sm:text-[15px] font-normal tracking-normal'
                      : 'bg-[#FFFFFF] dark:bg-[#1E1B18] text-[#111111] dark:text-[#F7F4EE] text-xs sm:text-[15px] font-normal border border-[#D5CBC0] dark:border-[#38332E]'
                  }`}
                >
                  <p className="whitespace-pre-line leading-relaxed font-normal">{message.text}</p>

                  {/* Generated Outfit */}
                  {message.suggestedOutfit && (
                    <OutfitCard
                      outfit={message.suggestedOutfit}
                      onSelectItem={onSelectItem}
                    />
                  )}
                </div>

                <span className="text-[9px] sm:text-[10px] tracking-[0.12em] uppercase text-[#73685C] dark:text-[#9E9285] font-medium mt-1.5 px-1">
                  {message.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex max-w-4xl mx-auto justify-start">
            <div className="bg-[#FFFFFF] dark:bg-[#1E1B18] border border-[#D5CBC0] dark:border-[#38332E] p-3.5 sm:p-4 text-xs text-[#2A2621] dark:text-[#EAE6DF] font-medium flex items-center gap-2.5 shadow-sm">
              <div className="w-2 h-2 rounded-full bg-[#111111] dark:bg-[#FFFFFF] animate-pulse" />
              <span className="font-serif-luxury text-sm italic tracking-wide">
                Стилист подбирает пропорции и фактуры из вашей капсулы...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-3.5 sm:p-6 border-t border-[#D8CFC2] dark:border-[#2D2A26] bg-[#FAF7F2]/95 dark:bg-[#161412]/95 backdrop-blur-md">
        <div className="max-w-4xl mx-auto space-y-3 sm:space-y-4">
          {/* Quick Ideas */}
          <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto scrollbar-none pb-0.5">
            <span className="text-[10px] tracking-[0.16em] uppercase text-[#4D453C] dark:text-[#C5BBAE] shrink-0 font-semibold mr-1">
              Сценарии:
            </span>
            {QUICK_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                disabled={isLoading}
                onClick={() => onSendMessage(p.text)}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-white dark:bg-[#201D1A] border border-[#C5BBAE] dark:border-[#423C34] hover:border-[#111111] dark:hover:border-[#FFFFFF] text-[10px] sm:text-[11px] font-medium text-[#1A1A1A] dark:text-[#EAE6DF] tracking-wide whitespace-nowrap transition-all shrink-0 disabled:opacity-40 shadow-2xs"
              >
                <span>{p.title}</span>
                <ArrowUpRight className="w-3 h-3 text-[#5A5044] dark:text-[#B5AAA0]" />
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
              placeholder="Спросите стилиста (например: «С чем носить бежевый тренч?»)..."
              className="w-full bg-[#FFFFFF] dark:bg-[#201D1A] border-2 border-[#C5BBAE] dark:border-[#423C34] focus:border-[#111111] dark:focus:border-[#FFFFFF] px-4 py-3 sm:px-5 sm:py-3.5 pr-14 text-xs sm:text-sm font-medium text-[#111111] dark:text-[#FFFFFF] placeholder-[#7D7366] focus:outline-none transition-colors shadow-xs"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="absolute right-1.5 sm:right-2 p-2 sm:p-2 bg-[#111111] hover:bg-[#2E2E2E] dark:bg-[#FFFFFF] dark:hover:bg-[#E0E0E0] text-white dark:text-[#111111] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center text-[9px] sm:text-[10px] tracking-[0.16em] uppercase text-[#6B6154] dark:text-[#9E9283] font-medium">
            Капсульный подход 12 STOREEZ • Высокий контраст и безупречный крой
          </p>
        </div>
      </div>
    </div>
  );
};
