import { useState } from 'react';
import type { UserAccount } from '../types';
import { registerUser } from '../services/authService';
import { X, ArrowRight } from 'lucide-react';

interface GuestExitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmExitWithoutSave: () => void;
  onRegisterSuccess: (newUser: UserAccount) => void;
  itemsCount: number;
  chatsCount: number;
}

export function GuestExitModal({
  isOpen,
  onClose,
  onConfirmExitWithoutSave,
  onRegisterSuccess,
  itemsCount,
}: GuestExitModalProps) {
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Укажите ваше имя');
      return;
    }
    if (!email.trim()) {
      setError('Укажите адрес электронной почты');
      return;
    }
    if (!password || password.length < 6) {
      setError('Пароль должен содержать от 6 символов');
      return;
    }
    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    const res = registerUser(name, email, password, 'user');
    if (res.success && res.user) {
      onRegisterSuccess(res.user);
    } else {
      setError(res.error || 'Не удалось завершить регистрацию');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-[#FAF9F6] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#2E2A26] p-7 sm:p-8 shadow-2xl relative text-[#1E1B18] dark:text-[#F7F5F0]">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {!showRegisterForm ? (
          <div>
            {/* 12 STOREEZ Brand Mark */}
            <div className="text-[10px] uppercase tracking-[0.22em] text-[#8A8175] dark:text-[#A69D92] mb-3">
              12 STOREEZ • Личный визит
            </div>

            <h3 className="text-base sm:text-lg font-normal tracking-[0.04em] uppercase text-[#1E1B18] dark:text-[#F7F5F0] mb-3 leading-snug">
              Сохранить созданную капсулу?
            </h3>

            <p className="text-xs text-[#6B6359] dark:text-[#A69D92] font-light leading-relaxed mb-6">
              Вы находитесь в гостевом режиме. При выходе подобранные образы и добавленные вещи ({itemsCount} шт.) не сохранятся. Создайте персональный аккаунт, чтобы вернуться к гардеробу в любой момент.
            </p>

            <div className="space-y-3 pt-2 border-t border-[#DFD9CF] dark:border-[#2E2A26]">
              {/* Primary 12 STOREEZ Action */}
              <button
                onClick={() => setShowRegisterForm(true)}
                className="w-full py-3 px-4 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.16em] font-normal transition-colors cursor-pointer text-center"
              >
                Сохранить капсулу и создать профиль
              </button>

              {/* Secondary Subdued Actions */}
              <button
                onClick={onConfirmExitWithoutSave}
                className="w-full py-2.5 px-4 text-xs tracking-[0.1em] uppercase text-[#8A8175] hover:text-black dark:hover:text-white border border-[#DFD9CF] dark:border-[#2E2A26] hover:border-[#1E1B18] dark:hover:border-white transition-colors cursor-pointer text-center"
              >
                Выйти без сохранения
              </button>

              <button
                onClick={onClose}
                className="w-full py-2 text-xs text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer text-center font-light"
              >
                Остаться в ателье
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleRegister}>
            <div className="text-[10px] uppercase tracking-[0.22em] text-[#8A8175] dark:text-[#A69D92] mb-3">
              12 STOREEZ • Новый профиль
            </div>

            <h3 className="text-base font-normal tracking-[0.04em] uppercase text-[#1E1B18] dark:text-[#F7F5F0] mb-2">
              Регистрация в AI Lookbook
            </h3>

            <p className="text-xs text-[#6B6359] dark:text-[#A69D92] font-light leading-relaxed mb-5">
              Ваш текущий выбор будет аккуратно перенесен в постоянную гардеробную комнату.
            </p>

            {error && (
              <div className="p-3 mb-4 text-xs bg-transparent border border-red-400 text-red-600 dark:text-red-400 font-light">
                {error}
              </div>
            )}

            <div className="space-y-3.5 mb-6">
              <div>
                <label className="block text-[10px] uppercase tracking-[0.14em] text-[#8A8175] dark:text-[#A69D92] mb-1">
                  Имя
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="Елена"
                  className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-[0.14em] text-[#8A8175] dark:text-[#A69D92] mb-1">
                  Электронная почта
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="elena@example.com"
                  className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-[0.14em] text-[#8A8175] dark:text-[#A69D92] mb-1">
                    Пароль
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[10px] uppercase tracking-[0.14em] text-[#8A8175] dark:text-[#A69D92] mb-1">
                    Повтор
                  </label>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 text-xs bg-[#EFECE6] dark:bg-[#25221F] border border-[#DFD9CF] dark:border-[#2E2A26] text-[#1E1B18] dark:text-[#F7F5F0] focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2.5">
              <button
                type="submit"
                className="w-full py-3 px-4 bg-[#1E1B18] hover:bg-[#322E2A] dark:bg-[#F7F5F0] dark:hover:bg-[#EBE7DF] text-[#F7F5F0] dark:text-[#1E1B18] text-xs uppercase tracking-[0.16em] font-normal transition-colors cursor-pointer flex items-center justify-center gap-2"
              >
                <span>Завершить регистрацию</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={() => setShowRegisterForm(false)}
                className="w-full py-2 text-xs text-[#8A8175] hover:text-[#1E1B18] dark:hover:text-[#F7F5F0] transition-colors cursor-pointer text-center font-light"
              >
                ← Назад к вариантам
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
