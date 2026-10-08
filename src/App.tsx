import { useState, useEffect } from 'react';
import type { WardrobeItem, ChatMessage } from './types';
import { INITIAL_WARDROBE } from './data/initialWardrobe';
import { askStylist } from './services/stylistApi';
import { WardrobeSidebar } from './components/WardrobeSidebar';
import { ChatArea } from './components/ChatArea';
import { AddItemModal } from './components/AddItemModal';
import { ItemDetailModal } from './components/ItemDetailModal';
import { Shirt, MessageSquare, BookOpen } from 'lucide-react';

const STORAGE_KEY = 'ai_stylist_wardrobe_v1';

export function App() {
  const [wardrobe, setWardrobe] = useState<WardrobeItem[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse saved wardrobe', e);
      }
    }
    return INITIAL_WARDROBE;
  });

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-msg',
      sender: 'assistant',
      timestamp: 'Только что',
      text: 'Здравствуйте! Я ваш персональный **AI-стилист** на основе RAG.\n\nЯ проанализировал ваш цифровой гардероб (в нем сейчас ' +
        INITIAL_WARDROBE.length +
        ' предметов). Спросите меня о чем угодно: подбор аутфита на свидание, погоду, деловую встречу или покажите конкретную вещь, к которой нужен гармоничный комплект!',
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
        text: 'Произошла ошибка при обращении к модели стилиста. Пожалуйста, попробуйте еще раз.',
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
        text: 'Диалог начат заново. Чем могу помочь сегодня? Подберем что-то стильное из гардероба?',
      },
    ]);
  };

  const handleAskAboutItem = (item: WardrobeItem) => {
    const prompt = `Подбери стильный завершенный аутфит вокруг этой вещи: "${item.title}". С чем из моего гардероба её лучше всего надеть?`;
    setMobileTab('chat');
    handleSendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-neutral-950 text-neutral-100 overflow-hidden font-sans">
      {/* Top Main Navigation Bar */}
      <header className="h-14 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-rose-500 to-amber-500 flex items-center justify-center font-black text-white shadow-md shadow-rose-500/20">
            👗
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5 m-0 p-0">
              CLOSET.AI
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                RAG Edition
              </span>
            </h1>
          </div>
        </div>

        {/* Mobile View Toggle */}
        <div className="flex lg:hidden bg-neutral-800 p-0.5 rounded-xl border border-neutral-700">
          <button
            onClick={() => setMobileTab('chat')}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              mobileTab === 'chat'
                ? 'bg-rose-500 text-white'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Чат</span>
          </button>
          <button
            onClick={() => setMobileTab('wardrobe')}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
              mobileTab === 'wardrobe'
                ? 'bg-rose-500 text-white'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Shirt className="w-3.5 h-3.5" />
            <span>Гардероб ({wardrobe.length})</span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-4 text-xs text-neutral-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            База знаний активна
          </span>
          <a
            href="#docs"
            onClick={(e) => {
              e.preventDefault();
              alert(
                'SDD Документация проекта доступна в каталогах /spec/product/ и /spec/tech/ текущего репозитория.'
              );
            }}
            className="hover:text-neutral-200 transition-colors flex items-center gap-1"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>SDD Спецификация</span>
          </a>
        </div>
      </header>

      {/* Main App Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Wardrobe Sidebar (Desktop or when tab is active on Mobile) */}
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

        {/* Chat Main Area (Desktop or when tab is active on Mobile) */}
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

export default App;
