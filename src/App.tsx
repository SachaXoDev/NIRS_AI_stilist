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

export type ActiveTab = 'chat' | 'wardrobe';

function HeaderContent({
  activeTab,
  onTabChange,
  wardrobeCount,
  threadsCount,
}: {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  wardrobeCount: number;
  threadsCount: number;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 sm:h-16 border-b border-[#D8CFC2] dark:border-[#2D2A26] bg-[#FAF7F2]/95 dark:bg-[#161412]/95 backdrop-blur-md px-4 sm:px-8 flex items-center justify-between shrink-0 z-20">
      {/* Brand Logo */}
      <div className="flex items-center gap-3 sm:gap-4">
        <span className="font-serif-luxury text-xl sm:text-2xl tracking-[0.16em] sm:tracking-[0.18em] font-medium text-[#111111] dark:text-[#FFFFFF] uppercase select-none">
          12 STOREEZ
        </span>
        <span className="w-px h-3.5 sm:h-4 bg-[#B5A898] dark:border-[#423C34]" />
        <span className="text-[10px] sm:text-[11px] tracking-[0.2em] uppercase font-semibold text-[#544B3F] dark:text-[#C5BBAE]">
          AI ATELIER
        </span>
      </div>

      {/* Clean Top Navigation */}
      <div className="flex items-center gap-2 sm:gap-6">
        <nav className="flex items-center border border-[#C5BBAE] dark:border-[#3E3830] p-1 bg-[#EFE9DF]/80 dark:bg-[#221F1C]">
          <button
            onClick={() => onTabChange('chat')}
            className={`flex items-center gap-2 px-3 sm:px-4 py-1.5 text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-semibold transition-all ${
              activeTab === 'chat'
                ? 'bg-[#111111] dark:bg-[#FFFFFF] text-white dark:text-[#111111] shadow-xs'
                : 'text-[#4A4135] dark:text-[#D5CCC0] hover:text-[#111111] dark:hover:text-[#FFFFFF]'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Стилист</span>
            <span className="text-[9px] opacity-80">({threadsCount})</span>
          </button>

          <button
            onClick={() => onTabChange('wardrobe')}
            className={`flex items-center gap-2 px-3 sm:px-4 py-1.5 text-[10px] sm:text-[11px] uppercase tracking-[0.14em] font-semibold transition-all ${
              activeTab === 'wardrobe'
                ? 'bg-[#111111] dark:bg-[#FFFFFF] text-white dark:text-[#111111] shadow-xs'
                : 'text-[#4A4135] dark:text-[#D5CCC0] hover:text-[#111111] dark:hover:text-[#FFFFFF]'
            }`}
          >
            <Shirt className="w-3.5 h-3.5" />
            <span>Капсула</span>
            <span className="text-[9px] opacity-80">({wardrobeCount})</span>
          </button>
        </nav>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'light' ? 'Включить вечерний режим' : 'Включить дневной режим'}
          className="p-2 text-[#4A4135] hover:text-[#111111] dark:text-[#D5CCC0] dark:hover:text-[#FFFFFF] transition-colors"
        >
          {theme === 'light' ? <Moon className="w-4 h-4 text-[#111111]" /> : <Sun className="w-4 h-4 text-[#FFFFFF]" />}
        </button>
      </div>
    </header>
  );
}

function MainApp() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('chat');

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

  // Mobile state inside "Стилист" tab:
  const [mobileViewingList, setMobileViewingList] = useState(false);

  // Sync with localStorage
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
    setActiveTab('chat');
    setMobileViewingList(false);
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
    setMobileViewingList(false);
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
    <div className="flex flex-col h-[100dvh] w-screen bg-[#F5F2EB] dark:bg-[#141210] text-[#111111] dark:text-[#FFFFFF] overflow-hidden font-sans transition-colors duration-300">
      {/* Top Header */}
      <HeaderContent
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setMobileViewingList(false);
        }}
        wardrobeCount={wardrobe.length}
        threadsCount={threads.length}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex overflow-hidden">
        {/* VIEW 1: ЧАТ СО СТИЛИСТОМ */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex w-full h-full overflow-hidden">
            {/* Left Column: Telegram-style Chat List */}
            <div
              className={`${
                mobileViewingList ? 'flex' : 'hidden md:flex'
              } w-full md:w-[320px] lg:w-[360px] xl:w-[400px] shrink-0 h-full border-r border-[#D8CFC2] dark:border-[#2D2A26] bg-[#F9F7F2] dark:bg-[#1A1816] overflow-hidden`}
            >
              <ChatListSidebar
                threads={threads}
                activeThreadId={activeThreadId}
                onSelectThread={handleSelectThread}
                onCreateThread={() => handleCreateNewThread()}
                onDeleteThread={handleDeleteThread}
              />
            </div>

            {/* Right Column: Active Conversation */}
            <div
              className={`${
                mobileViewingList ? 'hidden md:flex' : 'flex'
              } flex-1 h-full overflow-hidden`}
            >
              {activeThread ? (
                <ChatArea
                  chatTitle={activeThread.title}
                  messages={activeThread.messages}
                  isLoading={isLoading}
                  onSendMessage={handleSendMessage}
                  onCreateNewChat={() => handleCreateNewThread()}
                  onSelectItem={(item) => setSelectedItem(item)}
                  showBackButton={true}
                  onOpenChatListModal={() => setMobileViewingList(true)}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center p-8 text-[#544B3F]">
                  <p className="font-serif-luxury text-lg italic font-medium">Выберите диалог или создайте новый</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 2: ВАША КАПСУЛА (Полноэкранный красивый гардероб) */}
        {activeTab === 'wardrobe' && (
          <div className="flex-1 flex flex-col w-full h-full max-w-7xl mx-auto overflow-hidden px-3 sm:px-8 py-3 sm:py-6">
            <WardrobeSidebar
              wardrobe={wardrobe}
              onOpenAddModal={() => setIsAddModalOpen(true)}
              onDeleteItem={handleDeleteItem}
              onItemClick={(item) => setSelectedItem(item)}
            />
          </div>
        )}
      </main>

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
