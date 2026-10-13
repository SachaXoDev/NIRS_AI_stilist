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
import { Sun, Moon } from 'lucide-react';

const WARDROBE_STORAGE_KEY = 'closet_wardrobe_v5_pure';
const THREADS_STORAGE_KEY = 'closet_threads_v5_pure';

export type ActiveTab = 'chat' | 'wardrobe';

function HeaderContent({
  activeTab,
  onTabChange,
  wardrobeCount,
}: {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  wardrobeCount: number;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 sm:h-16 border-b border-[#E5E5E5] dark:border-[#262626] bg-[#FFFFFF] dark:bg-[#121212] px-4 sm:px-8 flex items-center justify-between shrink-0 z-20">
      {/* 12 STOREEZ Official Brand Mark */}
      <div className="flex items-center gap-3">
        <span className="text-sm sm:text-base tracking-[0.2em] font-medium text-[#111111] dark:text-[#FFFFFF] uppercase select-none">
          12 STOREEZ
        </span>
        <span className="w-px h-3 bg-[#E5E5E5] dark:bg-[#333333]" />
        <span className="text-[10px] tracking-[0.22em] text-[#767676] dark:text-[#888888] uppercase font-normal">
          AI ATELIER
        </span>
      </div>

      {/* Clean Segmented Navigation */}
      <div className="flex items-center gap-4 sm:gap-6">
        <nav className="flex items-center gap-6">
          <button
            onClick={() => onTabChange('chat')}
            className={`text-xs uppercase tracking-[0.15em] py-2 transition-colors relative font-normal ${
              activeTab === 'chat'
                ? 'text-[#111111] dark:text-[#FFFFFF] font-medium after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#111111] dark:after:bg-[#FFFFFF]'
                : 'text-[#767676] dark:text-[#888888] hover:text-[#111111] dark:hover:text-[#FFFFFF]'
            }`}
          >
            Стилист
          </button>

          <button
            onClick={() => onTabChange('wardrobe')}
            className={`text-xs uppercase tracking-[0.15em] py-2 transition-colors relative font-normal ${
              activeTab === 'wardrobe'
                ? 'text-[#111111] dark:text-[#FFFFFF] font-medium after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#111111] dark:after:bg-[#FFFFFF]'
                : 'text-[#767676] dark:text-[#888888] hover:text-[#111111] dark:hover:text-[#FFFFFF]'
            }`}
          >
            Гардероб ({wardrobeCount})
          </button>
        </nav>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'light' ? 'Переключить тему' : 'Переключить тему'}
          className="p-1.5 text-[#767676] hover:text-[#111111] dark:text-[#888888] dark:hover:text-[#FFFFFF] transition-colors"
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
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

  const [mobileViewingList, setMobileViewingList] = useState(false);

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
          text: 'Здравствуйте. Расскажите о ваших пожеланиях: для какого повода или погоды собираем образ?',
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

    setThreads((prev) =>
      prev.map((t) => {
        if (t.id === currentId) {
          const isInitialTitle = t.title === 'Новый диалог' || t.title === 'Консультация стилиста';
          const newTitle = isInitialTitle ? (text.length > 30 ? text.slice(0, 30) + '...' : text) : t.title;
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
    const prompt = `Подбери законченный образ с вещью «${item.title}». С чем из моей капсулы она комбинируется гармоничнее всего?`;
    handleCreateNewThread(`Образ: ${item.title}`);
    setTimeout(() => {
      handleSendMessage(prompt);
    }, 100);
  };

  return (
    <div className="flex flex-col h-[100dvh] w-screen bg-[#FFFFFF] dark:bg-[#121212] text-[#111111] dark:text-[#EDEDED] overflow-hidden font-sans transition-colors duration-150">
      {/* Header */}
      <HeaderContent
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setMobileViewingList(false);
        }}
        wardrobeCount={wardrobe.length}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex overflow-hidden">
        {/* VIEW 1: ЧАТ СО СТИЛИСТОМ */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex w-full h-full overflow-hidden">
            {/* Left Column: Telegram-style clean list */}
            <div
              className={`${
                mobileViewingList ? 'flex' : 'hidden md:flex'
              } w-full md:w-[300px] lg:w-[340px] xl:w-[360px] shrink-0 h-full border-r border-[#E5E5E5] dark:border-[#262626] bg-[#FAFAFA] dark:bg-[#161616] overflow-hidden`}
            >
              <ChatListSidebar
                threads={threads}
                activeThreadId={activeThreadId}
                onSelectThread={handleSelectThread}
                onCreateThread={() => handleCreateNewThread()}
                onDeleteThread={handleDeleteThread}
              />
            </div>

            {/* Right Column: Clean Conversation */}
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
                <div className="flex-1 flex items-center justify-center p-8 text-[#767676]">
                  <p className="text-sm font-normal">Выберите диалог или создайте новый</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 2: ГАРДЕРОБ */}
        {activeTab === 'wardrobe' && (
          <div className="flex-1 flex flex-col w-full h-full max-w-7xl mx-auto overflow-hidden px-4 sm:px-8 py-4 sm:py-6">
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
