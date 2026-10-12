import { useState } from 'react';
import type { ChatThread } from '../types';
import { Plus, Search, Trash2, MessageSquare, Sparkles } from 'lucide-react';

interface ChatListSidebarProps {
  threads: ChatThread[];
  activeThreadId: string;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
}

export const ChatListSidebar = ({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
}: ChatListSidebarProps) => {
  const [search, setSearch] = useState('');

  const filteredThreads = threads.filter((t) =>
    t.title.toLowerCase().includes(search.toLowerCase()) ||
    t.messages.some((m) => m.text.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="w-full h-full flex flex-col bg-[#F9F7F2] dark:bg-[#1A1816] select-none">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-[#D8CFC2] dark:border-[#2D2A26] flex items-center justify-between">
        <div>
          <span className="text-[10px] tracking-[0.2em] uppercase text-[#6B6154] dark:text-[#B5AAA0] font-semibold">
            Консультации
          </span>
          <h3 className="text-sm font-semibold tracking-wide text-[#111111] dark:text-[#FFFFFF] uppercase">
            История диалогов
          </h3>
        </div>

        <button
          onClick={onCreateThread}
          title="Создать новый диалог со стилистом"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#111111] hover:bg-[#2E2E2E] dark:bg-[#FFFFFF] dark:hover:bg-[#EAEAEA] text-white dark:text-[#111111] text-[10px] uppercase tracking-[0.14em] font-semibold transition-all shadow-xs"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Новый чат</span>
        </button>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-[#DCD3C5] dark:border-[#2D2A26] bg-[#F2EDE4]/60 dark:bg-[#201D1A]/60">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#574D41] dark:text-[#A89C8F]" />
          <input
            type="text"
            placeholder="Поиск по диалогам..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-white dark:bg-[#25221E] border border-[#C5BBAE] dark:border-[#3E3830] text-[#111111] dark:text-[#FFFFFF] placeholder-[#7D7366] font-medium focus:outline-none focus:border-[#111111] dark:focus:border-[#FFFFFF] transition-colors"
          />
        </div>
      </div>

      {/* List of Chat Threads */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#E0D8CB] dark:divide-[#2A2723]">
        {filteredThreads.length === 0 ? (
          <div className="text-center py-12 px-4 text-[#6B6154]">
            <p className="font-serif-luxury text-sm italic font-medium">Диалогов не найдено</p>
          </div>
        ) : (
          filteredThreads.map((thread) => {
            const isActive = thread.id === activeThreadId;
            const lastMsg = thread.messages[thread.messages.length - 1];
            const hasLook = thread.messages.some((m) => !!m.suggestedOutfit);

            return (
              <div
                key={thread.id}
                onClick={() => onSelectThread(thread.id)}
                className={`group relative flex items-start gap-3 p-3.5 sm:p-4 cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-[#EAE2D3] dark:bg-[#27231F] border-l-4 border-[#111111] dark:border-[#FFFFFF]'
                    : 'hover:bg-[#EFE9DD] dark:hover:bg-[#221F1C]'
                }`}
              >
                {/* Avatar / Icon */}
                <div
                  className={`w-9 h-9 shrink-0 flex items-center justify-center border ${
                    hasLook
                      ? 'bg-[#DDD2C0] dark:bg-[#332C24] border-[#B8A892] dark:border-[#524638] text-[#111111] dark:text-[#FFFFFF]'
                      : 'bg-white dark:bg-[#25221E] border-[#D0C5B5] dark:border-[#38332B] text-[#574D41] dark:text-[#A89C8F]'
                  }`}
                >
                  {hasLook ? (
                    <Sparkles className="w-4 h-4 text-[#82542B] dark:text-[#E2B78E]" />
                  ) : (
                    <MessageSquare className="w-4 h-4" />
                  )}
                </div>

                <div className="flex-1 min-w-0 pr-5">
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <h4
                      className={`text-xs truncate tracking-tight ${
                        isActive
                          ? 'font-bold text-[#111111] dark:text-[#FFFFFF]'
                          : 'font-semibold text-[#1F1B16] dark:text-[#E5DDD2]'
                      }`}
                    >
                      {thread.title}
                    </h4>
                    <span className="text-[9px] tracking-wider text-[#6B6154] dark:text-[#A89D90] shrink-0 font-medium">
                      {thread.updatedAt}
                    </span>
                  </div>

                  <p className="text-[11px] text-[#423A31] dark:text-[#BEB4A6] truncate font-normal leading-snug">
                    <span className="font-semibold">{lastMsg?.sender === 'assistant' ? 'Стилист: ' : 'Вы: '}</span>
                    {lastMsg?.text?.slice(0, 50) || 'Новый диалог'}
                  </p>

                  {hasLook && (
                    <span className="inline-block mt-1 text-[9px] uppercase tracking-[0.14em] text-[#82542B] dark:text-[#E2B78E] font-semibold">
                      • Готовый образ внутри
                    </span>
                  )}
                </div>

                {/* Delete button */}
                {threads.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(thread.id);
                    }}
                    title="Удалить диалог"
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-[#6B6154] hover:text-[#B91C1C] transition-opacity absolute right-2.5 top-3.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
