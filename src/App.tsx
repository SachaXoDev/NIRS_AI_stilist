import { useState, useEffect } from 'react';
import type { WardrobeItem, ChatMessage } from './types';
import { INITIAL_WARDROBE } from './data/initialWardrobe';
import { askStylist } from './services/stylistApi';
import { WardrobeSidebar } from './components/WardrobeSidebar';
import { ChatArea } from './components/ChatArea';
import { AddItemModal } from './components/AddItemModal';
import { ItemDetailModal } from './components/ItemDetailModal';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { MessageSquare, Shirt, Sun, Moon } from 'lucide-react';

const STORAGE_KEY = 'closet_wardrobe_v4_12storeez';

function HeaderContent({ wardrobeCount }: { wardrobeCount: number }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 sm:h-16 border-b border-[#E3DCD1] dark:border-[#2F2C28] bg-[#F7F4EE]/95 dark:bg-[#1C1A18]/95 backdrop-blur-md px-4 sm:px-10 flex items-center justify-between shrink-0 z-20">
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
        <div className="hidden sm:flex items-center gap-2 text-xs tracking-wider font-light text-[#8A7F73] dark:text-[#A89C8F]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#B29377]" />
          <span className="uppercase tracking-[0.14em] text-[10px]">Личная капсула ({wardrobeCount})</span>
        </div>

        {/* Theme button in header for quick mobile access */}
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
      text: 'Добро пожаловать в персональный сервис капсульного гардероба.\n\nВ вашей коллекции сейчас ' +
        INITIAL_WARDROBE.length +
        ' продуманных вещей. Опишите повод, погоду или выберите вещь, вокруг которой хотите выстроить образ — я предложу законченный аутфит с точными рекомендациями по слоям и деталям.',
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
        text: 'Готов собрать новый образ. Для какого случая или настроения подбираем комплект?',
      },
    ]);
  };

  const handleAskAboutItem = (item: WardrobeItem) => {
    const prompt = `Подбери законченный образ в эстетике 12 STOREEZ с вещью «${item.title}». С чем из моей капсулы она комбинируется гармоничнее всего?`;
    setMobileTab('chat');
    handleSendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-[100dvh] w-screen bg-[#F7F4EE] dark:bg-[#1C1A18] text-[#2C2926] dark:text-[#EAE6DF] overflow-hidden font-sans transition-colors duration-300">
      {/* Top Navbar */}
      <HeaderContent wardrobeCount={wardrobe.length} />

      {/* Main Layout Area */}
      <div className="flex-1 flex overflow-hidden pb-14 lg:pb-0">
        {/* Wardrobe Sidebar */}
        <div
          className={`${
            mobileTab === 'wardrobe' ? 'flex' : 'hidden'
          } lg:flex w-full lg:w-[410px] shrink-0 h-full overflow-hidden`}
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

      {/* Mobile Native-Style Bottom Navigation Bar */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 h-14 bg-[#F7F4EE]/95 dark:bg-[#1C1A18]/95 backdrop-blur-md border-t border-[#E3DCD1] dark:border-[#2F2C28] flex items-center justify-around px-4 z-30 pb-safe">
        <button
          onClick={() => setMobileTab('chat')}
          className={`flex flex-col items-center justify-center flex-1 h-full py-1 transition-all ${
            mobileTab === 'chat'
              ? 'text-[#2C2926] dark:text-[#F3EEE5] font-medium'
              : 'text-[#8A7F73] dark:text-[#6F665C]'
          }`}
        >
          <MessageSquare className="w-4 h-4 mb-1" />
          <span className="text-[10px] tracking-[0.14em] uppercase">Стилист</span>
        </button>

        <button
          onClick={() => setMobileTab('wardrobe')}
          className={`flex flex-col items-center justify-center flex-1 h-full py-1 transition-all ${
            mobileTab === 'wardrobe'
              ? 'text-[#2C2926] dark:text-[#F3EEE5] font-medium'
              : 'text-[#8A7F73] dark:text-[#6F665C]'
          }`}
        >
          <Shirt className="w-4 h-4 mb-1" />
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
