import { useState, useEffect } from 'react';
import type { WardrobeItem, ChatMessage } from './types';
import { INITIAL_WARDROBE } from './data/initialWardrobe';
import { askStylist } from './services/stylistApi';
import { WardrobeSidebar } from './components/WardrobeSidebar';
import { ChatArea } from './components/ChatArea';
import { AddItemModal } from './components/AddItemModal';
import { ItemDetailModal } from './components/ItemDetailModal';
import { ThemeProvider } from './context/ThemeContext';
import { MessageSquare, Shirt } from 'lucide-react';

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
    <div className="flex flex-col h-screen w-screen bg-[#FAF9F6] dark:bg-stone-950 text-stone-900 dark:text-stone-100 overflow-hidden font-sans transition-colors duration-200">
      {/* Top Navbar */}
      <header className="h-14 border-b border-stone-200/90 dark:border-stone-800 bg-white/70 dark:bg-stone-900/60 backdrop-blur-md px-5 sm:px-8 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="font-serif-luxury text-xl tracking-wider font-semibold text-stone-900 dark:text-stone-100">
            L'ARMOIRE
          </span>
          <span className="text-[10px] tracking-widest uppercase font-medium px-2 py-0.5 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 border border-stone-200 dark:border-stone-700">
            AI STYLIST
          </span>
        </div>

        {/* Mobile Tab Switcher */}
        <div className="flex lg:hidden bg-stone-150 dark:bg-stone-800 p-0.5 rounded-xl border border-stone-200 dark:border-stone-700">
          <button
            onClick={() => setMobileTab('chat')}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              mobileTab === 'chat'
                ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                : 'text-stone-500 hover:text-stone-900 dark:text-stone-400'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Чат</span>
          </button>
          <button
            onClick={() => setMobileTab('wardrobe')}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              mobileTab === 'wardrobe'
                ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                : 'text-stone-500 hover:text-stone-900 dark:text-stone-400'
            }`}
          >
            <Shirt className="w-3.5 h-3.5" />
            <span>Гардероб ({wardrobe.length})</span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-2 text-xs text-stone-400 dark:text-stone-500">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>Гардероб оцифрован</span>
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
