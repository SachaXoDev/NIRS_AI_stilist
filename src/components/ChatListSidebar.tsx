import { useState } from 'react';
import type { ChatThread } from '../types';
import { Plus, Search, Trash2 } from 'lucide-react';

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
    <div className="w-full h-full flex flex-col bg-[#EFECE6] dark:bg-[#1D1B18] select-none">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-[#DFD9CF] dark:border-[#2E2A26] flex items-center justify-between">
        <h3 className="text-xs uppercase tracking-[0.16em] font-medium text-[#1E1B18] dark:text-[#F7F5F0]">
          Диалоги
        </h3>

        <button
          onClick={onCreateThread}
          title="Новый диалог"
          className="flex items-center gap-1 text-[11px] uppercase tracking-[0.12em] font-medium text-[#1E1B18] dark:text-[#F7F5F0] hover:text-[#7C7469] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Новый</span>
        </button>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-[#DFD9CF] dark:border-[#2E2A26] bg-[#E8E4DC] dark:bg-[#24211E]">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8A8175]" />
          <input
            type="text"
            placeholder="Поиск..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-transparent border-none text-[#1E1B18] dark:text-[#F7F5F0] placeholder-[#8A8175] focus:outline-none"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#E4DDD2] dark:border-[#282420]">
        {filteredThreads.length === 0 ? (
          <div className="text-center py-12 px-4 text-[#7C7469]">
            <p className="text-xs">Диалогов не найдено</p>
          </div>
        ) : (
          filteredThreads.map((thread) => {
            const isActive = thread.id === activeThreadId;
            const lastMsg = thread.messages[thread.messages.length - 1];

            return (
              <div
                key={thread.id}
                onClick={() => onSelectThread(thread.id)}
                className={`group relative flex flex-col p-4 cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-[#FDFCFA] dark:bg-[#25221F] border-l-2 border-[#1E1B18] dark:border-[#F7F5F0]'
                    : 'hover:bg-[#EAE5DC] dark:hover:bg-[#221F1C]'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h4
                    className={`text-xs truncate tracking-normal ${
                      isActive
                        ? 'font-medium text-[#1E1B18] dark:text-[#F7F5F0]'
                        : 'font-normal text-[#38332E] dark:text-[#D8D1C7]'
                    }`}
                  >
                    {thread.title}
                  </h4>
                  <span className="text-[10px] text-[#8A8175] shrink-0 font-normal">
                    {thread.updatedAt}
                  </span>
                </div>

                <p className="text-xs text-[#6B6359] dark:text-[#A69D92] truncate font-normal leading-normal">
                  {lastMsg?.sender === 'assistant' ? 'Стилист: ' : 'Вы: '}
                  {lastMsg?.text?.slice(0, 50) || 'Новый диалог'}
                </p>

                {threads.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(thread.id);
                    }}
                    title="Удалить"
                    className="opacity-0 group-hover:opacity-100 p-1 text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-opacity absolute right-3 bottom-3"
                  >
                    <Trash2 className="w-3 h-3" />
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
