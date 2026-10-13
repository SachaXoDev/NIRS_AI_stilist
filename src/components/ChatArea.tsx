import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, WardrobeItem } from '../types';
import { OutfitCard } from './OutfitCard';
import { Send, Menu } from 'lucide-react';

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
    text: 'Подбери лаконичный образ для деловой встречи в офисе.',
  },
  {
    title: 'Прохладный день',
    text: 'Что надеть на прогулку в прохладную погоду? Нужен многослойный аутфит.',
  },
  {
    title: 'Выходной в городе',
    text: 'Собери расслабленный повседневный монохромный образ для выходного дня.',
  },
  {
    title: 'Ужин в ресторане',
    text: 'Посоветуй сдержанный вечерний комплект с акцентом на фактуры.',
  },
];

export const ChatArea = ({
  chatTitle,
  messages,
  isLoading,
  onSendMessage,
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
    <div className="flex-1 flex flex-col h-full bg-[#FFFFFF] dark:bg-[#121212] overflow-hidden relative">
      {/* Top Header */}
      <div className="h-14 sm:h-16 border-b border-[#E5E5E5] dark:border-[#262626] px-4 sm:px-8 flex items-center justify-between shrink-0 bg-[#FFFFFF]/90 dark:bg-[#121212]/90 backdrop-blur-md z-10">
        <div className="flex items-center gap-3 min-w-0">
          {onOpenChatListModal && (
            <button
              onClick={onOpenChatListModal}
              title="Открыть список диалогов"
              className="md:hidden p-1.5 -ml-1 text-[#111111] dark:text-[#FFFFFF]"
            >
              <Menu className="w-4 h-4" />
            </button>
          )}

          <h2 className="text-xs sm:text-sm font-medium tracking-normal text-[#111111] dark:text-[#FFFFFF] truncate">
            {chatTitle}
          </h2>
        </div>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-12 py-6 sm:py-8 space-y-6">
        {messages.map((message) => {
          const isUser = message.sender === 'user';
          return (
            <div
              key={message.id}
              className={`flex gap-3 max-w-3xl mx-auto ${
                isUser ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`flex flex-col w-full sm:max-w-xl ${
                  isUser ? 'items-end' : 'items-start'
                }`}
              >
                {/* 12 STOREEZ Minimal Aesthetic: crisp, clean, flat, modern */}
                <div
                  className={`p-4 sm:p-5 leading-relaxed text-xs sm:text-sm ${
                    isUser
                      ? 'bg-[#111111] dark:bg-[#FFFFFF] text-[#FFFFFF] dark:text-[#111111] font-normal'
                      : 'bg-[#F7F7F7] dark:bg-[#1C1C1C] text-[#111111] dark:text-[#E5E5E5] font-normal border border-[#EAEAEA] dark:border-[#282828]'
                  }`}
                >
                  <p className="whitespace-pre-line leading-relaxed">{message.text}</p>

                  {/* Generated Outfit */}
                  {message.suggestedOutfit && (
                    <OutfitCard
                      outfit={message.suggestedOutfit}
                      onSelectItem={onSelectItem}
                    />
                  )}
                </div>

                <span className="text-[10px] text-[#888888] dark:text-[#777777] mt-1.5 px-0.5">
                  {message.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex max-w-3xl mx-auto justify-start">
            <div className="bg-[#F7F7F7] dark:bg-[#1C1C1C] border border-[#EAEAEA] dark:border-[#282828] p-3 text-xs text-[#555555] dark:text-[#AAAAAA] flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#111111] dark:bg-[#FFFFFF] animate-pulse" />
              <span>Подбираем вещи и формулу образа...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 sm:p-6 border-t border-[#E5E5E5] dark:border-[#262626] bg-[#FFFFFF] dark:bg-[#121212]">
        <div className="max-w-3xl mx-auto space-y-3">
          {/* Quick Ideas */}
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pb-0.5">
            {QUICK_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                disabled={isLoading}
                onClick={() => onSendMessage(p.text)}
                className="px-3 py-1 bg-[#F5F5F5] dark:bg-[#1E1E1E] hover:bg-[#EBEBEB] dark:hover:bg-[#2A2A2A] text-[11px] font-normal text-[#333333] dark:text-[#CCCCCC] whitespace-nowrap transition-colors shrink-0 disabled:opacity-40"
              >
                {p.title}
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
              placeholder="Спросите стилиста (например: «С чем носить тренч?»)..."
              className="w-full bg-[#F5F5F5] dark:bg-[#1C1C1C] border border-transparent focus:border-[#111111] dark:focus:border-[#FFFFFF] px-4 py-3 pr-12 text-xs sm:text-sm text-[#111111] dark:text-[#FFFFFF] placeholder-[#888888] focus:outline-none transition-colors"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2 p-1.5 bg-[#111111] dark:bg-[#FFFFFF] text-white dark:text-[#111111] hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
