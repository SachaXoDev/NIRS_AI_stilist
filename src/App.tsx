import { useState, useEffect } from 'react';
import type { WardrobeItem, ChatMessage, ChatThread, UserAccount, OutfitLook } from './types';
import { INITIAL_WARDROBE } from './data/initialWardrobe';
import { INITIAL_CHAT_THREADS } from './data/initialChats';
import { askStylist } from './services/stylistApi';
import { getCurrentUser, logoutUser } from './services/authService';
import { WardrobeSidebar } from './components/WardrobeSidebar';
import { ChatListSidebar } from './components/ChatListSidebar';
import { ChatArea } from './components/ChatArea';
import { AddItemModal } from './components/AddItemModal';
import { ItemDetailModal } from './components/ItemDetailModal';
import { AuthView } from './components/AuthView';
import { AdminPanel } from './components/AdminPanel';
import { GuestExitModal } from './components/GuestExitModal';
import { SavedOutfitsView } from './components/SavedOutfitsView';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { Sun, Moon } from 'lucide-react';

const WARDROBE_STORAGE_PREFIX = 'closet_wardrobe_user_';
const THREADS_STORAGE_PREFIX = 'closet_threads_user_';
const SAVED_OUTFITS_PREFIX = 'closet_saved_outfits_user_';

function getUserSavedOutfitsKey(userId?: string | null): string {
  return `${SAVED_OUTFITS_PREFIX}${userId || 'anonymous'}`;
}

function loadUserSavedOutfits(user: UserAccount | null): OutfitLook[] {
  if (!user || user.id.startsWith('guest-')) return [];
  const key = getUserSavedOutfitsKey(user.id);
  const saved = localStorage.getItem(key);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) return parsed;
    } catch (e) {
      console.error('Failed to parse saved outfits', e);
    }
  }
  return [];
}

function getUserWardrobeKey(userId?: string | null): string {
  return `${WARDROBE_STORAGE_PREFIX}${userId || 'anonymous'}`;
}

function generateSmartTopic(prompt: string): string {
  const lower = prompt.toLowerCase();

  if (lower.includes('дожд') || lower.includes('прохлад') || lower.includes('погод') || lower.includes('ветер') || lower.includes('осень') || lower.includes('весна')) {
    return 'Образ по погоде';
  }
  if (lower.includes('офис') || lower.includes('работ') || lower.includes('встреч') || lower.includes('делов') || lower.includes('переговор')) {
    return 'Деловой Smart-Casual';
  }
  if (lower.includes('вечер') || lower.includes('ужин') || lower.includes('театр') || lower.includes('свидан') || lower.includes('ресторан')) {
    return 'Вечерний выход';
  }
  if (lower.includes('поездк') || lower.includes('самолет') || lower.includes('путешеств') || lower.includes('аэропорт') || lower.includes('чемодан')) {
    return 'Образ в поездку';
  }
  if (lower.includes('коктейл') || lower.includes('праздник') || lower.includes('вечеринк') || lower.includes('день рождени')) {
    return 'Коктейльный дресс-код';
  }
  if (lower.includes('кашемир') || lower.includes('шерст') || lower.includes('шелк')) {
    return 'Кашемир и шелк';
  }
  if (lower.includes('тренч') || lower.includes('пальто')) {
    return 'Верхняя одежда';
  }
  if (lower.includes('блейзер') || lower.includes('жакет')) {
    return 'Капсула с жакетом';
  }
  if (lower.includes('брюк') || lower.includes('палаццо')) {
    return 'Образ с брюками';
  }
  if (lower.includes('джинс') || lower.includes('деним')) {
    return 'Городской деним';
  }

  // Если запрос общий или абстрактный — очищаем от вводных слов и берем 2-3 ключевых слова
  const clean = prompt
    .replace(/^(подбери|собери|посоветуй|подскажи|что|надеть|как|сочетать|образ|лук|пожалуйста)\s+/i, '')
    .trim();

  const words = clean.split(/\s+/).filter(Boolean);
  if (words.length > 0 && words.length <= 4) {
    const formatted = words.join(' ');
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  }

  return 'Повседневный лук';
}

function getUserThreadsKey(userId?: string | null): string {
  return `${THREADS_STORAGE_PREFIX}${userId || 'anonymous'}`;
}

function loadUserWardrobe(user: UserAccount | null): WardrobeItem[] {
  if (!user) return [];

  // Гость всегда начинает с чистого гардероба (0 вещей)
  if (user.id.startsWith('guest-')) {
    return [];
  }

  // Для Елены (демо-пользователя) даем готовую капсулу
  if (user.email === 'elena@12storeez.com') {
    const key = getUserWardrobeKey(user.id);
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) return parsed;
      } catch (e) {
        console.error('Failed to parse wardrobe', e);
      }
    }
    return INITIAL_WARDROBE;
  }

  const key = getUserWardrobeKey(user.id);
  const saved = localStorage.getItem(key);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) return parsed;
    } catch (e) {
      console.error('Failed to parse wardrobe', e);
    }
  }

  return [];
}

function createDefaultThreadForUser(userName?: string): ChatThread {
  const greeting = userName && userName !== 'Гость' ? `Здравствуйте, ${userName}.` : 'Здравствуйте.';
  return {
    id: `thread-${Date.now()}`,
    title: 'Консультация стилиста',
    createdAt: 'Только что',
    updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    messages: [
      {
        id: `welcome-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: `${greeting} Рад приветствовать вас в 12 STOREEZ AI Lookbook. Опишите повод, погоду или выберите вещь из вашей коллекции — и я соберу законченный образ.`,
      },
    ],
  };
}

function loadUserThreads(user: UserAccount | null): ChatThread[] {
  if (!user) return [];
  const key = getUserThreadsKey(user.id);
  const saved = localStorage.getItem(key);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    } catch (e) {
      console.error('Failed to parse chat threads', e);
    }
  }

  // Для Елены (демо-пользователя) даем готовые демонстрационные диалоги
  if (user.email === 'elena@12storeez.com') {
    return INITIAL_CHAT_THREADS;
  }

  // Для новых зарегистрированных пользователей или гостей создаем их персональный чистый диалог
  return [createDefaultThreadForUser(user.name)];
}

export type MainScreen = 'atelier' | 'admin' | 'auth';
export type AtelierTab = 'chat' | 'wardrobe' | 'saved';

function HeaderContent({
  currentScreen,
  atelierTab,
  onAtelierTabChange,
  wardrobeCount,
  savedCount,
  currentUser,
  onLogout,
}: {
  currentScreen: MainScreen;
  atelierTab: AtelierTab;
  onAtelierTabChange: (tab: AtelierTab) => void;
  wardrobeCount: number;
  savedCount: number;
  currentUser: UserAccount | null;
  onLogout: () => void;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 sm:h-16 border-b border-[#DFD9CF] dark:border-[#2E2A26] bg-[#F6F4F0] dark:bg-[#181614] px-4 sm:px-8 flex items-center justify-between shrink-0 z-30 transition-colors relative">
      {/* 12 STOREEZ Brand */}
      <div className="flex items-center gap-3">
        <span className="text-sm sm:text-base tracking-[0.2em] font-medium text-[#1E1B18] dark:text-[#F7F5F0] uppercase select-none">
          12 STOREEZ
        </span>
        <span className="w-px h-3 bg-[#DFD9CF] dark:bg-[#3A3530]" />
        <span className="text-[10px] tracking-[0.22em] text-[#7C7469] dark:text-[#A69D92] uppercase font-normal">
          {currentScreen === 'admin' ? 'RAG ADMIN' : 'AI LOOKBOOK'}
        </span>
      </div>

      {/* Main Nav: Only in client atelier */}
      {currentScreen === 'atelier' && (
        <nav className="flex items-center gap-6 sm:gap-8">
          <button
            onClick={() => onAtelierTabChange('chat')}
            className={`text-xs uppercase tracking-[0.16em] py-2 transition-colors relative font-normal cursor-pointer ${
              atelierTab === 'chat'
                ? 'text-[#1E1B18] dark:text-[#F7F5F0] font-medium after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#1E1B18] dark:after:bg-[#F7F5F0]'
                : 'text-[#7C7469] dark:text-[#A69D92] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0]'
            }`}
          >
            Стилист
          </button>

          <button
            onClick={() => onAtelierTabChange('wardrobe')}
            className={`text-xs uppercase tracking-[0.16em] py-2 transition-colors relative font-normal cursor-pointer ${
              atelierTab === 'wardrobe'
                ? 'text-[#1E1B18] dark:text-[#F7F5F0] font-medium after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#1E1B18] dark:after:bg-[#F7F5F0]'
                : 'text-[#7C7469] dark:text-[#A69D92] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0]'
            }`}
          >
            Гардероб ({wardrobeCount})
          </button>

          <button
            onClick={() => onAtelierTabChange('saved')}
            className={`text-xs uppercase tracking-[0.16em] py-2 transition-colors relative font-normal cursor-pointer ${
              atelierTab === 'saved'
                ? 'text-[#1E1B18] dark:text-[#F7F5F0] font-medium after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#1E1B18] dark:after:bg-[#F7F5F0]'
                : 'text-[#7C7469] dark:text-[#A69D92] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0]'
            }`}
          >
            Лукбук ({savedCount})
          </button>
        </nav>
      )}

      {currentScreen === 'admin' && (
        <div className="absolute left-1/2 -translate-x-1/2 text-xs uppercase tracking-[0.2em] text-[#7C7469] dark:text-[#A69D92] font-medium pointer-events-none">
          Панель куратора RAG
        </div>
      )}

      {currentScreen === 'auth' && (
        <div className="absolute left-1/2 -translate-x-1/2 text-xs uppercase tracking-[0.22em] text-[#7C7469] dark:text-[#A69D92] font-normal pointer-events-none">
          Авторизация
        </div>
      )}

      {/* Right Controls: Theme Toggle & Logout */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title="Сменить тему"
          className="p-1.5 text-[#7C7469] hover:text-[#1E1B18] dark:text-[#A69D92] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer"
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>

        {/* User Info & Simple Clean Logout Button */}
        {currentUser && (
          <div className="flex items-center gap-2.5 pl-2 border-l border-[#DFD9CF] dark:border-[#38332E]">
            <div className="hidden md:flex flex-col items-end">
              <span className="text-xs font-medium text-[#1E1B18] dark:text-[#F7F5F0] max-w-[130px] truncate leading-tight">
                {currentUser.name}
              </span>
              <span className="text-[10px] text-[#7C7469] dark:text-[#9F9589] leading-tight">
                {currentUser.role === 'admin' ? 'Администратор' : 'Клиент'}
              </span>
            </div>

            {/* Строгая монограмма по первой букве имени для ВСЕХ пользователей */}
            <div className="w-7 h-7 rounded-full bg-[#E5DFD5] dark:bg-[#2C2824] border border-[#DFD9CF] dark:border-[#38332E] flex items-center justify-center text-[11px] font-medium text-[#1E1B18] dark:text-[#F7F5F0] select-none">
              {currentUser.name.trim().slice(0, 1).toUpperCase()}
            </div>

            <button
              onClick={onLogout}
              title="Завершить сессию"
              className="px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-[#7C7469] dark:text-[#A69D92] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer"
            >
              Выйти
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

function MainApp() {
  const [currentUser, setCurrentUser] = useState<UserAccount | null>(() => getCurrentUser());
  const [currentScreen, setCurrentScreen] = useState<MainScreen>(() => {
    const user = getCurrentUser();
    if (!user) return 'auth';
    return user.role === 'admin' ? 'admin' : 'atelier';
  });
  const [atelierTab, setAtelierTab] = useState<AtelierTab>('chat');

  const [wardrobe, setWardrobe] = useState<WardrobeItem[]>(() => {
    return loadUserWardrobe(currentUser);
  });

  const [threads, setThreads] = useState<ChatThread[]>(() => {
    return loadUserThreads(currentUser);
  });

  const [savedOutfits, setSavedOutfits] = useState<OutfitLook[]>(() => {
    return loadUserSavedOutfits(currentUser);
  });

  const [activeThreadId, setActiveThreadId] = useState<string>(() => {
    return threads[0]?.id || 'thread-active';
  });

  // При смене пользователя (логин/логаут/регистрация) загружаем именно его персональные данные
  useEffect(() => {
    if (currentUser) {
      const userWardrobe = loadUserWardrobe(currentUser);
      setWardrobe(userWardrobe);

      const userThreads = loadUserThreads(currentUser);
      setThreads(userThreads);
      setActiveThreadId(userThreads[0]?.id || 'thread-active');

      const userSaved = loadUserSavedOutfits(currentUser);
      setSavedOutfits(userSaved);
    }
  }, [currentUser]);

  const [isLoading, setIsLoading] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<WardrobeItem | null>(null);
  const [isGuestExitModalOpen, setIsGuestExitModalOpen] = useState(false);

  const [mobileViewingList, setMobileViewingList] = useState(false);

  // Сохраняем гардероб в ключ пользователя (кроме гостя — гость живет только в памяти сессии)
  useEffect(() => {
    if (currentUser && !currentUser.id.startsWith('guest-')) {
      const key = getUserWardrobeKey(currentUser.id);
      localStorage.setItem(key, JSON.stringify(wardrobe));
    }
  }, [wardrobe, currentUser]);

  // Сохраняем диалоги в ключ пользователя (кроме гостя — гость живет только в памяти сессии)
  useEffect(() => {
    if (currentUser && !currentUser.id.startsWith('guest-')) {
      const key = getUserThreadsKey(currentUser.id);
      localStorage.setItem(key, JSON.stringify(threads));
    }
  }, [threads, currentUser]);

  // Сохраняем избранные образы в ключ пользователя
  useEffect(() => {
    if (currentUser && !currentUser.id.startsWith('guest-')) {
      const key = getUserSavedOutfitsKey(currentUser.id);
      localStorage.setItem(key, JSON.stringify(savedOutfits));
    }
  }, [savedOutfits, currentUser]);

  const handleToggleSaveOutfit = (outfit: OutfitLook) => {
    setSavedOutfits((prev) => {
      const exists = prev.some((o) => o.id === outfit.id);
      if (exists) {
        return prev.filter((o) => o.id !== outfit.id);
      }
      return [outfit, ...prev];
    });
  };

  const handleRemoveSavedOutfit = (outfitId: string) => {
    setSavedOutfits((prev) => prev.filter((o) => o.id !== outfitId));
  };

  const handleRestoreDefaultCapsule = () => {
    setWardrobe(INITIAL_WARDROBE);
  };

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
    setCurrentScreen('atelier');
    setAtelierTab('chat');
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

  const handleRenameThread = (threadId: string, newTitle: string) => {
    setThreads((prev) =>
      prev.map((t) => (t.id === threadId ? { ...t, title: newTitle } : t))
    );
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
          // Если это был дефолтный диалог или новый чат — даем ему емкую тему по контексту
          const isInitialTitle =
            t.title === 'Новый диалог' ||
            t.title === 'Консультация стилиста' ||
            t.title.trim() === '';
          const smartTitle = isInitialTitle ? generateSmartTopic(text) : t.title;

          return {
            ...t,
            title: smartTitle,
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

  const handleUpdateItem = (updatedItem: WardrobeItem) => {
    setWardrobe((prev) => prev.map((item) => (item.id === updatedItem.id ? updatedItem : item)));
    setSelectedItem(updatedItem);
  };

  const handleAskAboutItem = async (item: WardrobeItem, occasion?: string) => {
    const contextPrompt = occasion
      ? `Подбери законченный образ для ${occasion} с вещью «${item.title}». С чем из моей капсулы она комбинируется гармоничнее всего?`
      : `Подбери законченный образ с вещью «${item.title}». С чем из моей капсулы она комбинируется гармоничнее всего?`;

    const newId = `thread-${Date.now()}`;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: timeStr,
      text: contextPrompt,
    };

    const newThread: ChatThread = {
      id: newId,
      title: `Образ: ${item.title}`,
      createdAt: 'Только что',
      updatedAt: timeStr,
      messages: [userMsg],
    };

    // Мгновенно переключаем экран в чат на созданный диалог
    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(newId);
    setCurrentScreen('atelier');
    setAtelierTab('chat');
    setMobileViewingList(false);
    setIsLoading(true);

    try {
      const response = await askStylist(contextPrompt, wardrobe);
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: response.text,
        suggestedOutfit: response.suggestedOutfit,
        referencedItemIds: response.referencedItemIds,
      };

      setThreads((prev) =>
        prev.map((t) => (t.id === newId ? { ...t, messages: [...t.messages, aiMsg] } : t))
      );
    } catch (e) {
      console.error(e);
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: 'Не удалось получить ответ стилиста. Пожалуйста, повторите запрос.',
      };
      setThreads((prev) =>
        prev.map((t) => (t.id === newId ? { ...t, messages: [...t.messages, errorMsg] } : t))
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogoutClick = () => {
    // Если выходит гость — спрашиваем подтверждение или предлагаем сохранить через регистрацию
    if (currentUser && currentUser.id.startsWith('guest-')) {
      setIsGuestExitModalOpen(true);
      return;
    }
    // Обычный зарегистрированный пользователь выходит напрямую
    executeDirectLogout();
  };

  const executeDirectLogout = () => {
    // Если гость согласился выйти без сохранения — чистим всё
    if (currentUser && currentUser.id.startsWith('guest-')) {
      const guestThreadKey = getUserThreadsKey(currentUser.id);
      const guestWardrobeKey = getUserWardrobeKey(currentUser.id);
      localStorage.removeItem(guestThreadKey);
      localStorage.removeItem(guestWardrobeKey);
      setWardrobe([]);
      setThreads([]);
    }

    logoutUser();
    setCurrentUser(null);
    setCurrentScreen('auth');
    setIsGuestExitModalOpen(false);
  };

  // Когда гость нажимает "Зарегистрироваться и сохранить всё" в модалке выхода
  const handleGuestConvertedToUser = (registeredUser: UserAccount) => {
    // Сохраняем текущий гардероб и текущие чаты гостя под ключом нового пользователя
    const userWardrobeKey = getUserWardrobeKey(registeredUser.id);
    const userThreadKey = getUserThreadsKey(registeredUser.id);

    localStorage.setItem(userWardrobeKey, JSON.stringify(wardrobe));
    localStorage.setItem(userThreadKey, JSON.stringify(threads));

    setCurrentUser(registeredUser);
    setIsGuestExitModalOpen(false);
  };

  return (
    <div className="flex flex-col h-[100dvh] w-screen bg-[#F6F4F0] dark:bg-[#181614] text-[#1E1B18] dark:text-[#F7F5F0] overflow-hidden font-sans transition-colors duration-150">
      {/* Authentic Luxury Header */}
      <HeaderContent
        currentScreen={currentScreen}
        atelierTab={atelierTab}
        onAtelierTabChange={(tab) => setAtelierTab(tab)}
        wardrobeCount={wardrobe.length}
        savedCount={savedOutfits.length}
        currentUser={currentUser}
        onLogout={handleLogoutClick}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex overflow-hidden">
        {/* VIEW 1: АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ */}
        {currentScreen === 'auth' && (
          <AuthView
            onSuccess={(user) => {
              setCurrentUser(user);
              if (user.role === 'admin') {
                setCurrentScreen('admin');
              } else {
                setCurrentScreen('atelier');
              }
            }}
            onContinueAsGuest={() => {
              const guestUser: UserAccount = {
                id: `guest-${Date.now()}`,
                name: 'Гость',
                email: 'guest@12storeez.com',
                role: 'user',
                vipStatus: 'Гостевой режим',
                createdAt: 'Только что',
              };
              setCurrentUser(guestUser);
              setCurrentScreen('atelier');
            }}
          />
        )}

        {/* VIEW 2: ПОЛНОЦЕННОЕ АТЕЛЬЕ (СТИЛИСТ + ГАРДЕРОБ) */}
        {currentScreen === 'atelier' && (
          <>
            {atelierTab === 'chat' ? (
              <div className="flex-1 flex w-full h-full overflow-hidden">
                {/* Left Column: Telegram-style list in warm cashmere */}
                <div
                  className={`${
                    mobileViewingList ? 'flex' : 'hidden md:flex'
                  } w-full md:w-[300px] lg:w-[340px] xl:w-[360px] shrink-0 h-full border-r border-[#DFD9CF] dark:border-[#2E2A26] bg-[#EFECE6] dark:bg-[#1D1B18] overflow-hidden`}
                >
                  <ChatListSidebar
                    threads={threads}
                    activeThreadId={activeThreadId}
                    onSelectThread={handleSelectThread}
                    onCreateThread={() => handleCreateNewThread()}
                    onDeleteThread={handleDeleteThread}
                    onRenameThread={handleRenameThread}
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
                      savedOutfitIds={savedOutfits.map((o) => o.id)}
                      onToggleSaveOutfit={handleToggleSaveOutfit}
                    />
                  ) : (
                    <div className="flex-1 flex items-center justify-center p-8 text-[#7C7469]">
                      <p className="text-sm font-normal">Выберите диалог или создайте новый</p>
                    </div>
                  )}
                </div>
              </div>
            ) : atelierTab === 'wardrobe' ? (
              <div className="flex-1 flex flex-col w-full h-full max-w-7xl mx-auto overflow-hidden px-4 sm:px-8 py-4 sm:py-6">
                <WardrobeSidebar
                  wardrobe={wardrobe}
                  onOpenAddModal={() => setIsAddModalOpen(true)}
                  onDeleteItem={handleDeleteItem}
                  onItemClick={(item) => setSelectedItem(item)}
                  onRestoreDefaultCapsule={handleRestoreDefaultCapsule}
                />
              </div>
            ) : (
              <SavedOutfitsView
                savedOutfits={savedOutfits}
                onRemoveOutfit={handleRemoveSavedOutfit}
                onSelectItem={(item) => setSelectedItem(item)}
                onGoToChat={() => setAtelierTab('chat')}
              />
            )}
          </>
        )}

        {/* VIEW 3: АДМИНИСТРАТИВНАЯ ПАНЕЛЬ RAG */}
        {currentScreen === 'admin' && currentUser && (
          <AdminPanel
            currentUser={currentUser}
            wardrobe={wardrobe}
            threadsCount={threads.length}
            onLogout={handleLogoutClick}
          />
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
        onUpdateItem={handleUpdateItem}
      />

      {/* Guest Exit Confirmation & Quick Registration Modal */}
      <GuestExitModal
        isOpen={isGuestExitModalOpen}
        onClose={() => setIsGuestExitModalOpen(false)}
        onConfirmExitWithoutSave={executeDirectLogout}
        onRegisterSuccess={handleGuestConvertedToUser}
        itemsCount={wardrobe.length}
        chatsCount={threads.length}
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
