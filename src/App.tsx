import { useState, useEffect } from 'react';
import type { WardrobeItem, ChatMessage } from './types';
import { INITIAL_WARDROBE } from './data/initialWardrobe';
import { askStylist } from './services/stylistApi';
import { WardrobeSidebar } from './components/WardrobeSidebar';
import { ChatArea } from './components/ChatArea';
import { AddItemModal } from './components/AddItemModal';
import { ItemDetailModal } from './components/ItemDetailModal';
import { ThemeProvider } from './context/ThemeContext';
import { MessageSquare, Shirt, Sparkles } from 'lucide-react';

// Versioned key to guarantee new vector illustrations load
const STORAGE_KEY = 'closet_wardrobe_v3_illustrations';

function MainApp() {
  const [wardrobe, setWardrobe] = useState<WardrobeItem[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
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

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-msg',
      sender: 'assistant',
      timestamp: 'Сегодня',
      text: 'Добро пожаловать в персональный гардеробный сервис.\n\nВ вашей капсуле сейчас ' +
        INITIAL_WARDROBE.length +
        ' предметов. Напишите, какой образ вы хотите составить: укажите повод, погоду или выберите конкретную вещь из гардероба — и я предложу гармоничный аутфит с советами по стайлингу.',
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<WardrobeItem | null>(null);
  const [mobileTab, setMobileTab] = useState<'chat' | 'wardrobe'>('chat');

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(wardrobe));
  }, [wardrobe]);

  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text,
    };

    setMessages((prev) => [...prev, userMsg]);
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
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      console.error(error);
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: 'Не удалось получить ответ стилиста. Пожалуйста, повторите запрос.',
      };
      setMessages((prev) => [...prev, errorMsg]);
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

  const handleResetChat = () => {
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        sender: 'assistant',
        timestamp: 'Только что',
        text: 'Готов собрать новый аутфит. Для какого случая или настроения подбираем образ?',
      },
    ]);
  };

  const handleAskAboutItem = (item: WardrobeItem) => {
    const prompt = `Подбери законченный стильный образ с вещью «${item.title}». С чем из моего гардероба она смотрится гармоничнее всего?`;
    setMobileTab('chat');
    handleSendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-gradient-to-br from-rose-50/60 via-amber-50/40 to-violet-50/50 dark:from-stone-950 dark:via-stone-900 dark:to-stone-950 text-stone-900 dark:text-stone-100 overflow-hidden font-sans transition-colors duration-200">
      {/* Top Navbar */}
      <header className="h-14 border-b border-rose-200/60 dark:border-stone-800 bg-white/80 dark:bg-stone-900/75 backdrop-blur-md px-5 sm:px-8 flex items-center justify-between shrink-0 shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-rose-700 to-amber-700 flex items-center justify-center text-white shadow-xs">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-serif-luxury text-xl tracking-wider font-semibold bg-gradient-to-r from-stone-900 via-rose-900 to-amber-900 dark:from-stone-100 dark:via-rose-200 dark:to-amber-200 bg-clip-text text-transparent">
            L'ARMOIRE
          </span>
          <span className="text-[10px] tracking-widest uppercase font-semibold px-2.5 py-0.5 rounded-full bg-rose-100/80 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60">
            AI STYLIST
          </span>
        </div>

        {/* Mobile Tab Switcher */}
        <div className="flex lg:hidden bg-rose-50/80 dark:bg-stone-800 p-0.5 rounded-xl border border-rose-200/70 dark:border-stone-700">
          <button
            onClick={() => setMobileTab('chat')}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              mobileTab === 'chat'
                ? 'bg-gradient-to-r from-rose-700 to-amber-700 text-white shadow-xs'
                : 'text-stone-600 hover:text-stone-900 dark:text-stone-400'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Чат</span>
          </button>
          <button
            onClick={() => setMobileTab('wardrobe')}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              mobileTab === 'wardrobe'
                ? 'bg-gradient-to-r from-rose-700 to-amber-700 text-white shadow-xs'
                : 'text-stone-600 hover:text-stone-900 dark:text-stone-400'
            }`}
          >
            <Shirt className="w-3.5 h-3.5" />
            <span>Гардероб ({wardrobe.length})</span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-2 text-xs font-medium px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-800/50">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Гардероб активен ({wardrobe.length})</span>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div
          className={`${
            mobileTab === 'wardrobe' ? 'flex' : 'hidden'
          } lg:flex w-full lg:w-96 shrink-0 h-full overflow-hidden`}
        >
          <WardrobeSidebar
            wardrobe={wardrobe}
            onOpenAddModal={() => setIsAddModalOpen(true)}
            onDeleteItem={handleDeleteItem}
            onItemClick={(item) => setSelectedItem(item)}
          />
        </div>

        {/* Chat Area */}
        <div
          className={`${
            mobileTab === 'chat' ? 'flex' : 'hidden'
          } lg:flex flex-1 h-full overflow-hidden`}
        >
          <ChatArea
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            onResetChat={handleResetChat}
            onSelectItem={(item) => setSelectedItem(item)}
          />
        </div>
      </div>

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
