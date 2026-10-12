import { useState, useEffect } from 'react';
import type { WardrobeItem, ChatMessage, ChatThread } from './types';
import { INITIAL_WARDROBE } from './data/initialWardrobe';
import { INITIAL_CHAT_THREADS } from './data/initialChats';
import { askStylist } from './services/stylistApi';
import { WardrobeSidebar } from './components/WardrobeSidebar';
import { ChatListSidebar } from './components/ChatListSidebar';
import { ChatArea } from './components/ChatArea';
import { AddItemModal } from './components/AddItemModal';
import { ItemDetailModal } from './components/ItemDetailModal';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { MessageSquare, Shirt, Sun, Moon } from 'lucide-react';

const WARDROBE_STORAGE_KEY = 'closet_wardrobe_v4_12storeez';
const THREADS_STORAGE_KEY = 'closet_threads_v1_tg';

function HeaderContent({
  wardrobeCount,
  activeThreadTitle,
}: {
  wardrobeCount: number;
  activeThreadTitle?: string;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 sm:h-16 border-b border-[#E3DCD1] dark:border-[#2F2C28] bg-[#F7F4EE]/95 dark:bg-[#1C1A18]/95 backdrop-blur-md px-4 sm:px-8 flex items-center justify-between shrink-0 z-20">
      <div className="flex items-center gap-3 sm:gap-4">
        <span className="font-serif-luxury text-xl sm:text-2xl tracking-[0.16em] sm:tracking-[0.18em] font-light text-[#2C2926] dark:text-[#F3EEE5] uppercase">
          12 STOREEZ
        </span>
        <span className="w-px h-3.5 sm:h-4 bg-[#D6CDC0] dark:bg-[#3D3833]" />
        <span className="text-[10px] sm:text-[11px] tracking-[0.2em] uppercase font-light text-[#8A7F73] dark:text-[#A89C8F]">
          AI ATELIER
        </span>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        {activeThreadTitle && (
          <div className="hidden md:flex items-center gap-2 text-xs text-[#8A7F73] dark:text-[#A89C8F]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#B29377]" />
            <span className="truncate max-w-[200px] font-light">{activeThreadTitle}</span>
          </div>
        )}

        <div className="hidden sm:flex items-center gap-2 text-xs tracking-wider font-light text-[#8A7F73] dark:text-[#A89C8F]">
          <span className="uppercase tracking-[0.14em] text-[10px]">Капсула ({wardrobeCount})</span>
        </div>

        {/* Theme button */}
        <button
          onClick={toggleTheme}
          title={theme === 'light' ? 'Включить вечерний режим' : 'Включить дневной режим'}
          className="p-2 text-[#8A7F73] hover:text-[#2C2926] dark:hover:text-[#F3EEE5] transition-colors"
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
}

function MainApp() {
  const [wardrobe, setWardrobe] = useState<WardrobeItem[]>(() => {
    const saved = localStorage.getItem(WARDROBE_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {
        console.error('Failed to parse wardrobe', e);
      }
    }
    return INITIAL_WARDROBE;
  });

  const [threads, setThreads] = useState<ChatThread[]>(() => {
    const saved = localStorage.getItem(THREADS_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {
        console.error('Failed to parse chat threads', e);
      }
    }
    return INITIAL_CHAT_THREADS;
  });

  const [activeThreadId, setActiveThreadId] = useState<string>(() => {
    return threads[0]?.id || 'thread-active';
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<WardrobeItem | null>(null);

  // Mobile navigation views:
  // 'chats' = list of all threads (Telegram style)
  // 'chat'  = inside the selected conversation
  // 'wardrobe' = personal clothing capsule
  const [mobileView, setMobileView] = useState<'chats' | 'chat' | 'wardrobe'>('chats');

  // Save changes to localStorage
  useEffect(() => {
    localStorage.setItem(WARDROBE_STORAGE_KEY, JSON.stringify(wardrobe));
  }, [wardrobe]);

  useEffect(() => {
    localStorage.setItem(THREADS_STORAGE_KEY, JSON.stringify(threads));
  }, [threads]);

  const activeThread = threads.find((t) => t.id === activeThreadId) || threads[0];

  const handleCreateNewThread = (customPrompt?: string) => {
    const newId = `thread-${Date.now()}`;
    const newThread: ChatThread = {
      id: newId,
      title: customPrompt ? customPrompt.slice(0, 32) + '...' : 'Новый диалог',
      createdAt: 'Только что',
      updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      messages: [
        {
          id: `welcome-${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: 'Слушаю вас. Для какого случая или настроения подбираем образ сегодня?',
        },
      ],
    };

    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(newId);
    setMobileView('chat');
  };

  const handleDeleteThread = (threadId: string) => {
    setThreads((prev) => {
      const remaining = prev.filter((t) => t.id !== threadId);
      if (activeThreadId === threadId && remaining.length > 0) {
        setActiveThreadId(remaining[0].id);
      }
      return remaining;
    });
  };

  const handleSelectThread = (threadId: string) => {
    setActiveThreadId(threadId);
    setMobileView('chat');
  };

  const handleSendMessage = async (text: string) => {
    const currentId = activeThreadId;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: timeStr,
      text,
    };

    // Auto-update thread title if it's the first real question
    setThreads((prev) =>
      prev.map((t) => {
        if (t.id === currentId) {
          const isInitialTitle = t.title === 'Новый диалог' || t.title === 'Консультация стилиста';
          const newTitle = isInitialTitle ? (text.length > 32 ? text.slice(0, 32) + '...' : text) : t.title;
          return {
            ...t,
            title: newTitle,
            updatedAt: timeStr,
            messages: [...t.messages, userMsg],
          };
        }
        return t;
      })
    );

    setIsLoading(true);

    try {
      const response = await askStylist(text, wardrobe);
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: response.text,
        suggestedOutfit: response.suggestedOutfit,
        referencedItemIds: response.referencedItemIds,
      };

      setThreads((prev) =>
        prev.map((t) => {
          if (t.id === currentId) {
            return {
              ...t,
              updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              messages: [...t.messages, aiMsg],
            };
          }
          return t;
        })
      );
    } catch (error) {
      console.error(error);
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: 'Не удалось получить ответ стилиста. Пожалуйста, повторите запрос.',
      };
      setThreads((prev) =>
        prev.map((t) => (t.id === currentId ? { ...t, messages: [...t.messages, errorMsg] } : t))
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddItem = (item: WardrobeItem) => {
    setWardrobe((prev) => [item, ...prev]);
  };

  const handleDeleteItem = (id: string) => {
    setWardrobe((prev) => prev.filter((i) => i.id !== id));
  };

  const handleAskAboutItem = (item: WardrobeItem) => {
    const prompt = `Подбери законченный образ в эстетике 12 STOREEZ с вещью «${item.title}». С чем из моей капсулы она комбинируется гармоничнее всего?`;
    handleCreateNewThread(`Образ: ${item.title}`);
    setTimeout(() => {
      handleSendMessage(prompt);
    }, 100);
  };

  return (
    <div className="flex flex-col h-[100dvh] w-screen bg-[#F7F4EE] dark:bg-[#1C1A18] text-[#2C2926] dark:text-[#EAE6DF] overflow-hidden font-sans transition-colors duration-300">
      {/* Top Navbar */}
      <HeaderContent wardrobeCount={wardrobe.length} activeThreadTitle={activeThread?.title} />

      {/* Main 3-Column Experience:
          1. Wardrobe (Desktop left)
          2. Telegram-style Chats List (Desktop middle)
          3. Active Conversation (Desktop right)
      */}
      <div className="flex-1 flex overflow-hidden pb-14 lg:pb-0">
        {/* Wardrobe (Left column on widescreen) */}
        <div
          className={`${
            mobileView === 'wardrobe' ? 'flex' : 'hidden'
          } lg:flex w-full lg:w-[360px] xl:w-[390px] shrink-0 h-full overflow-hidden`}
        >
          <WardrobeSidebar
            wardrobe={wardrobe}
            onOpenAddModal={() => setIsAddModalOpen(true)}
            onDeleteItem={handleDeleteItem}
            onItemClick={(item) => setSelectedItem(item)}
          />
        </div>

        {/* Telegram-style Chats List (Middle column on desktop) */}
        <div
          className={`${
            mobileView === 'chats' ? 'flex' : 'hidden'
          } lg:flex w-full lg:w-[300px] xl:w-[330px] shrink-0 h-full overflow-hidden`}
        >
          <ChatListSidebar
            threads={threads}
            activeThreadId={activeThreadId}
            onSelectThread={handleSelectThread}
            onCreateThread={() => handleCreateNewThread()}
            onDeleteThread={handleDeleteThread}
          />
        </div>

        {/* Active Dialogue View (Right column on desktop) */}
        <div
          className={`${
            mobileView === 'chat' ? 'flex' : 'hidden'
          } lg:flex flex-1 h-full overflow-hidden`}
        >
          {activeThread ? (
            <ChatArea
              chatTitle={activeThread.title}
              messages={activeThread.messages}
              isLoading={isLoading}
              onSendMessage={handleSendMessage}
              onCreateNewChat={() => handleCreateNewThread()}
              onSelectItem={(item) => setSelectedItem(item)}
              showBackButton={mobileView === 'chat'}
              onOpenChatListModal={() => setMobileView('chats')}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 text-[#8A7F73]">
              <p className="font-serif-luxury text-lg italic">Выберите диалог или создайте новый</p>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Bottom Navigation Bar (Telegram / 12 STOREEZ style) */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 h-14 bg-[#F7F4EE]/95 dark:bg-[#1C1A18]/95 backdrop-blur-md border-t border-[#E3DCD1] dark:border-[#2F2C28] flex items-center justify-around px-4 z-30 pb-safe">
        <button
          onClick={() => setMobileView('chats')}
          className={`flex flex-col items-center justify-center flex-1 h-full py-1 transition-all ${
            mobileView === 'chats' || mobileView === 'chat'
              ? 'text-[#2C2926] dark:text-[#F3EEE5] font-medium'
              : 'text-[#8A7F73] dark:text-[#6F665C]'
          }`}
        >
          <div className="relative">
            <MessageSquare className="w-4 h-4 mb-0.5" />
            <span className="absolute -top-1 -right-2 text-[8px] px-1 bg-[#2C2926] dark:bg-[#EAE6DF] text-white dark:text-[#1C1A18] font-bold">
              {threads.length}
            </span>
          </div>
          <span className="text-[10px] tracking-[0.14em] uppercase">Диалоги</span>
        </button>

        <button
          onClick={() => setMobileView('wardrobe')}
          className={`flex flex-col items-center justify-center flex-1 h-full py-1 transition-all ${
            mobileView === 'wardrobe'
              ? 'text-[#2C2926] dark:text-[#F3EEE5] font-medium'
              : 'text-[#8A7F73] dark:text-[#6F665C]'
          }`}
        >
          <Shirt className="w-4 h-4 mb-0.5" />
          <span className="text-[10px] tracking-[0.14em] uppercase">
            Капсула ({wardrobe.length})
          </span>
        </button>
      </nav>

      {/* Modals */}
      <AddItemModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddItem}
      />

      <ItemDetailModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onAskAboutItem={handleAskAboutItem}
      />
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <MainApp />
    </ThemeProvider>
  );
}

export default App;
