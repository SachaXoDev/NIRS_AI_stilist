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
    <div className="w-full h-full flex flex-col bg-[#F7F4EE] dark:bg-[#1E1B19] border-r border-[#E3DCD1] dark:border-[#2F2C28] select-none">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-[#E3DCD1] dark:border-[#2F2C28] flex items-center justify-between">
        <div>
          <h3 className="text-base sm:text-lg font-serif-luxury font-light tracking-[0.06em] text-[#2C2926] dark:text-[#F3EEE5] uppercase">
            Диалоги
          </h3>
          <p className="text-[10px] tracking-[0.14em] uppercase text-[#8A7F73] dark:text-[#A89C8F]">
            {threads.length} сохранено
          </p>
        </div>

        <button
          onClick={onCreateThread}
          title="Создать новый диалог со стилистом"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#2C2926] hover:bg-[#423D38] dark:bg-[#EAE6DF] dark:hover:bg-[#FFFFFF] text-white dark:text-[#1C1A18] text-[10px] uppercase tracking-[0.14em] font-medium transition-all"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Новый чат</span>
        </button>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-[#ECE5D9] dark:border-[#2A2723]">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8A7F73]" />
          <input
            type="text"
            placeholder="Поиск по чатам..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#EDE7DC]/70 dark:bg-[#262320] border border-[#DCD3C5] dark:border-[#38332E] text-[#2C2926] dark:text-[#EAE6DF] placeholder-[#9D9387] focus:outline-none focus:border-[#8A7F73] transition-colors"
          />
        </div>
      </div>

      {/* List of Chat Threads */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#EAE2D5] dark:divide-[#282522]">
        {filteredThreads.length === 0 ? (
          <div className="text-center py-12 px-4 text-[#8A7F73]">
            <p className="font-serif-luxury text-sm italic">Диалогов не найдено</p>
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
                    ? 'bg-[#EDE5D8] dark:bg-[#282420] border-l-2 border-[#2C2926] dark:border-[#EAE6DF]'
                    : 'hover:bg-[#EFEAE0] dark:hover:bg-[#23201D]'
                }`}
              >
                {/* Avatar / Icon */}
                <div
                  className={`w-9 h-9 shrink-0 flex items-center justify-center rounded-none border ${
                    hasLook
                      ? 'bg-[#E2D8C9] dark:bg-[#2E2924] border-[#C7BBAA] dark:border-[#423C35] text-[#2C2926] dark:text-[#EAE6DF]'
                      : 'bg-[#F2ECE1] dark:bg-[#24211E] border-[#DED4C5] dark:border-[#332F2A] text-[#8A7F73]'
                  }`}
                >
                  {hasLook ? (
                    <Sparkles className="w-4 h-4 text-[#8C6D4F] dark:text-[#D1B89D]" />
                  ) : (
                    <MessageSquare className="w-4 h-4" />
                  )}
                </div>

                <div className="flex-1 min-w-0 pr-5">
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <h4
                      className={`text-xs truncate tracking-tight ${
                        isActive
                          ? 'font-medium text-[#2C2926] dark:text-[#F3EEE5]'
                          : 'font-normal text-[#3E3A35] dark:text-[#D5CCC0]'
                      }`}
                    >
                      {thread.title}
                    </h4>
                    <span className="text-[9px] tracking-wider text-[#9E9283] dark:text-[#786E63] shrink-0 font-light">
                      {thread.updatedAt}
                    </span>
                  </div>

                  <p className="text-[11px] text-[#7A6F63] dark:text-[#9A8E80] truncate font-light leading-snug">
                    {lastMsg?.sender === 'assistant' ? 'Стилист: ' : 'Вы: '}
                    {lastMsg?.text?.slice(0, 50) || 'Новый диалог'}
                  </p>

                  {hasLook && (
                    <span className="inline-block mt-1 text-[9px] uppercase tracking-[0.14em] text-[#8C6D4F] dark:text-[#D1B89D] font-medium">
                      • Готовый образ внутри
                    </span>
                  )}
                </div>

                {/* Delete button (show on hover, but never allow deleting the last one) */}
                {threads.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(thread.id);
                    }}
                    title="Удалить диалог"
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-[#8A7F73] hover:text-[#991B1B] transition-opacity absolute right-2.5 top-3.5"
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
