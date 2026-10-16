import { useState } from 'react';
import type { ChatThread } from '../types';
import { Plus, Search, Trash2, Pencil, Check, X } from 'lucide-react';

interface ChatListSidebarProps {
  threads: ChatThread[];
  activeThreadId: string;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
  onRenameThread?: (threadId: string, newTitle: string) => void;
}

export const ChatListSidebar = ({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onRenameThread,
}: ChatListSidebarProps) => {
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [deletingThread, setDeletingThread] = useState<ChatThread | null>(null);

  const handleStartRename = (e: React.MouseEvent, thread: ChatThread) => {
    e.stopPropagation();
    setEditingId(thread.id);
    setEditingTitle(thread.title);
  };

  const handleSaveRename = (e: React.MouseEvent | React.FormEvent, threadId: string) => {
    e.stopPropagation();
    if (editingTitle.trim() && onRenameThread) {
      onRenameThread(threadId, editingTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

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
                  {editingId === thread.id ? (
                    <div className="flex items-center gap-1 w-full" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(e, thread.id);
                          if (e.key === 'Escape') setEditingId(null);
                        }}
                        autoFocus
                        className="flex-1 text-xs px-1.5 py-0.5 bg-white dark:bg-[#1E1C19] border border-[#1E1B18] dark:border-white rounded text-[#1E1B18] dark:text-white focus:outline-none"
                      />
                      <button
                        onClick={(e) => handleSaveRename(e, thread.id)}
                        className="p-1 hover:text-emerald-600 transition-colors cursor-pointer"
                        title="Сохранить"
                      >
                        <Check className="w-3 h-3" />
                      </button>
                      <button
                        onClick={handleCancelRename}
                        className="p-1 hover:text-red-600 transition-colors cursor-pointer"
                        title="Отмена"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <>
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
                    </>
                  )}
                </div>

                <p className="text-xs text-[#6B6359] dark:text-[#A69D92] truncate font-normal leading-normal">
                  {lastMsg?.sender === 'assistant' ? 'Стилист: ' : 'Вы: '}
                  {lastMsg?.text?.slice(0, 50) || 'Новый диалог'}
                </p>

                {editingId !== thread.id && (
                  <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 absolute right-3 bottom-2.5 transition-opacity bg-[#EFECE6]/90 dark:bg-[#1D1B18]/90 pl-1">
                    {onRenameThread && (
                      <button
                        onClick={(e) => handleStartRename(e, thread)}
                        title="Переименовать"
                        className="p-1 text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                    )}
                    {threads.length > 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingThread(thread);
                        }}
                        title="Удалить диалог"
                        className="p-1 text-[#8A8175] hover:text-red-600 dark:hover:text-red-400 transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Delete Confirmation Modal in 12 STOREEZ Style */}
      {deletingThread && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={() => setDeletingThread(null)}
        >
          <div
            className="w-full max-w-sm bg-[#FCFAF7] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#2E2A26] p-6 shadow-2xl relative text-[#1E1B18] dark:text-[#F7F5F0]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#8A8175] dark:text-[#A69D92] mb-2 font-normal">
              12 STOREEZ • Диалог
            </div>

            <h3 className="text-sm uppercase tracking-[0.06em] font-medium text-[#1E1B18] dark:text-[#F7F5F0] mb-2">
              Удалить этот диалог?
            </h3>

            <p className="text-xs text-[#6B6359] dark:text-[#A69D92] font-light leading-relaxed mb-5">
              Диалог «<strong>{deletingThread.title}</strong>» и все рекомендации стилиста внутри него будут удалены.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#EFECE6] dark:border-[#282420]">
              <button
                onClick={() => setDeletingThread(null)}
                className="px-3.5 py-2 text-xs text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer font-light"
              >
                Отмена
              </button>
              <button
                onClick={() => {
                  onDeleteThread(deletingThread.id);
                  setDeletingThread(null);
                }}
                className="px-4 py-2 bg-[#1E1B18] hover:bg-black dark:bg-[#F7F5F0] dark:hover:bg-white text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.12em] font-normal transition-colors cursor-pointer"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
