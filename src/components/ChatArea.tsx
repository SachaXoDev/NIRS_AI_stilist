import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, WardrobeItem, OutfitLook } from '../types';
import { OutfitCard } from './OutfitCard';
import { Send, Menu } from 'lucide-react';
import { WeatherPicker } from './WeatherPicker';

interface ChatAreaProps {
  chatTitle: string;
  messages: ChatMessage[];
  draft?: ChatMessage;
  onSendMessage: (text: string) => void;
  onCreateNewChat: () => void;
  onSelectItem: (item: WardrobeItem) => void;
  onOpenChatListModal?: () => void;
  showBackButton?: boolean;
  savedOutfitIds?: string[];
  onToggleSaveOutfit?: (outfit: OutfitLook) => void;
}

const QUICK_PROMPTS = [
  {
    title: 'Деловая встреча',
    text: 'Подбери лаконичный образ для деловой встречи в офисе.',
  },
  {
    title: 'Ужин в ресторане',
    text: 'Посоветуй сдержанный вечерний комплект с акцентом на фактуры.',
  },
  {
    title: 'Выходной в городе',
    text: 'Собери расслабленный повседневный монохромный образ для выходного дня.',
  },
  {
    title: 'Пляж и +30°C',
    text: 'Подбери образ для пляжа в жару при +30°C.',
  },
];

export const ChatArea = ({
  chatTitle,
  messages,
  draft,
  onSendMessage,
  onSelectItem,
  onOpenChatListModal,
  savedOutfitIds = [],
  onToggleSaveOutfit,
}: ChatAreaProps) => {
  const [inputText, setInputText] = useState('');
  const weatherPromptRef = useRef('');
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isLoading = Boolean(draft);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: draft ? 'instant' : 'smooth' });
  }, [messages, draft]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText);
    weatherPromptRef.current = '';
    setInputText('');
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#F6F4F0] dark:bg-[#181614] overflow-hidden relative">
      {/* Top Header */}
      <div className="h-14 sm:h-16 border-b border-[#DFD9CF] dark:border-[#2E2A26] px-4 sm:px-8 flex items-center justify-between shrink-0 bg-[#F6F4F0]/90 dark:bg-[#181614]/90 backdrop-blur-md z-10">
        <div className="flex items-center gap-3 min-w-0">
          {onOpenChatListModal && (
            <button
              onClick={onOpenChatListModal}
              title="Открыть список диалогов"
              className="md:hidden p-1.5 -ml-1 text-[#1E1B18] dark:text-[#F7F5F0]"
            >
              <Menu className="w-4 h-4" />
            </button>
          )}

          <h2 className="text-xs sm:text-sm font-medium tracking-normal text-[#1E1B18] dark:text-[#F7F5F0] truncate">
            {chatTitle}
          </h2>
        </div>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-12 py-6 sm:py-8 space-y-6">
        {(draft?.text ? [...messages, draft] : messages).map((message) => {
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
                {/* 12 STOREEZ Tactile Aesthetic: Warm cashmere, ivory & deep espresso */}
                <div
                  className={`p-4 sm:p-5 leading-relaxed text-xs sm:text-sm ${
                    isUser
                      ? 'bg-[#1E1B18] dark:bg-[#F7F5F0] text-[#F7F5F0] dark:text-[#1E1B18] font-normal shadow-xs'
                      : 'bg-[#FCFAF7] dark:bg-[#221F1C] text-[#1E1B18] dark:text-[#E8E2D8] font-normal border border-[#DFD9CF] dark:border-[#332F2A]'
                  }`}
                >
                  <p className="whitespace-pre-line leading-relaxed">{message.text}</p>

                  {/* Generated Outfit */}
                  {message.suggestedOutfit && (
                    <OutfitCard
                      outfit={message.suggestedOutfit}
                      onSelectItem={onSelectItem}
                      isSaved={savedOutfitIds.includes(message.suggestedOutfit.id)}
                      onToggleSave={onToggleSaveOutfit}
                    />
                  )}
                </div>

                <span className="text-[10px] text-[#8A8175] dark:text-[#7A7268] mt-1.5 px-0.5">
                  {message.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && !draft?.text && (
          <div className="flex max-w-3xl mx-auto justify-start">
            <div role="status" className="bg-[#FCFAF7] dark:bg-[#221F1C] border border-[#DFD9CF] dark:border-[#332F2A] p-3 text-xs text-[#6B6359] dark:text-[#A69D92] flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#1E1B18] dark:bg-[#F7F5F0] animate-pulse" />
              <span>Стилист готовит ответ...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 sm:p-6 border-t border-[#DFD9CF] dark:border-[#2E2A26] bg-[#F6F4F0] dark:bg-[#181614]">
        <div className="max-w-3xl mx-auto space-y-3">
          {/* Quick Ideas */}
          <WeatherPicker disabled={isLoading} onUse={(text) => {
            const previous = weatherPromptRef.current;
            weatherPromptRef.current = text;
            setInputText((draftText) => {
              const note = previous && draftText.endsWith(previous) ? draftText.slice(0, -previous.length) : draftText;
              return note.trim() ? `${note.trimEnd()} ${text}` : text;
            });
            inputRef.current?.focus();
          }}>
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt.title}
                disabled={isLoading}
                onClick={() => onSendMessage(prompt.text)}
                className="shrink-0 cursor-pointer whitespace-nowrap border border-[#DFD9CF] bg-[#ECE7DF] px-3 py-1.5 text-[11px] text-[#38332E] transition-colors hover:bg-[#E2DCCF] disabled:opacity-40 dark:border-[#332F2A] dark:bg-[#24211E] dark:text-[#D8D1C7] dark:hover:bg-[#2E2A26]"
              >
                {prompt.title}
              </button>
            ))}
          </WeatherPicker>

          {/* Form */}
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoading}
              placeholder="Спросите стилиста (например: «С чем носить тренч?»)..."
              className="w-full bg-[#FCFAF7] dark:bg-[#221F1C] border border-[#DFD9CF] dark:border-[#332F2A] focus:border-[#1E1B18] dark:focus:border-[#F7F5F0] px-4 py-3 pr-12 text-xs sm:text-sm text-[#1E1B18] dark:text-[#F7F5F0] placeholder-[#8A8175] focus:outline-none transition-colors"
            />
            <button
              type="submit"
              aria-label="Отправить сообщение"
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2 p-1.5 bg-[#1E1B18] dark:bg-[#F7F5F0] text-[#F7F5F0] dark:text-[#1E1B18] hover:opacity-85 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
