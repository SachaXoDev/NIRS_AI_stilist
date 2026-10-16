import { useState } from 'react';
import type { UserAccount } from '../types';
import { loginUser, registerUser } from '../services/authService';
import { ArrowRight, Lock, Mail, User } from 'lucide-react';

interface AuthViewProps {
  onSuccess: (user: UserAccount) => void;
  onContinueAsGuest?: () => void;
}

export function AuthView({ onSuccess, onContinueAsGuest }: AuthViewProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'login') {
      if (!email.trim()) {
        setError('Введите адрес электронной почты');
        return;
      }
      const res = loginUser(email, password);
      if (res.success && res.user) {
        onSuccess(res.user);
      } else {
        setError(res.error || 'Ошибка входа');
      }
    } else {
      if (!name.trim()) {
        setError('Пожалуйста, укажите ваше имя');
        return;
      }
      if (!email.trim()) {
        setError('Пожалуйста, укажите адрес электронной почты');
        return;
      }
      if (!password) {
        setError('Придумайте пароль для входа');
        return;
      }
      if (password.length < 6) {
        setError('Пароль должен содержать не менее 6 символов');
        return;
      }
      if (password !== confirmPassword) {
        setError('Пароли не совпадают');
        return;
      }

      // Любой регистрирующийся пользователь всегда регистрируется как Клиент ('user')
      const res = registerUser(name, email, password, 'user');
      if (res.success && res.user) {
        onSuccess(res.user);
      } else {
        setError(res.error || 'Ошибка регистрации');
      }
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 sm:p-10 bg-[#F6F4F0] dark:bg-[#181614] overflow-y-auto">
      <div className="w-full max-w-lg bg-[#FAF9F6] dark:bg-[#1C1A18] border border-[#DFD9CF] dark:border-[#332E2A] rounded-2xl shadow-xl overflow-hidden text-[#1E1B18] dark:text-[#F7F5F0] transition-colors">
        {/* Brand Banner */}
        <div className="px-8 pt-9 pb-6 border-b border-[#DFD9CF] dark:border-[#2D2925] bg-[#F2EFE9] dark:bg-[#23201D]">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[11px] uppercase tracking-[0.25em] font-semibold text-[#8C8275] dark:text-[#A89E91]">
              12 STOREEZ • АВТОРИЗАЦИЯ
            </span>
          </div>
          <h1 className="text-2xl font-normal tracking-tight text-[#1E1B18] dark:text-[#FFFFFF]">
            {mode === 'login' ? 'Вход в аккаунт' : 'Регистрация в AI Lookbook'}
          </h1>
          <p className="text-xs text-[#6F675C] dark:text-[#B3AAA0] mt-1.5 leading-relaxed font-light">
            {mode === 'login'
              ? 'Войдите со своим адресом электронной почты для доступа к гардеробу.'
              : 'Создайте персональный профиль для подбора индивидуальных капсул.'}
          </p>
        </div>

        {/* Regular Login / Register Form */}
        <form onSubmit={handleSubmit} className="p-8 space-y-5">
          {error && (
            <div className="p-3 text-xs rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 space-y-2">
              <div>{error}</div>
              {mode === 'login' && error.includes('не найден') && (
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setMode('register');
                  }}
                  className="text-xs font-semibold underline text-[#1E1B18] dark:text-white hover:opacity-80 block cursor-pointer"
                >
                  Зарегистрироваться с этим email →
                </button>
              )}
            </div>
          )}

          {mode === 'register' && (
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-[#6F675C] dark:text-[#A89E91] mb-1.5">
                ФИО / Имя
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C8275]" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Дарья Романова"
                  className="w-full pl-9 pr-3 py-2.5 text-xs bg-white dark:bg-[#262320] border border-[#DFD9CF] dark:border-[#38332E] rounded-lg text-[#1E1B18] dark:text-[#FFFFFF] placeholder:text-[#9A9084] focus:outline-none focus:ring-1 focus:ring-[#1E1B18] dark:focus:ring-white"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[#6F675C] dark:text-[#A89E91] mb-1.5">
              Электронная почта
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C8275]" />
              <input
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="name@example.com"
                className="w-full pl-10 pr-4 py-3 text-xs bg-white dark:bg-[#262320] border border-[#DFD9CF] dark:border-[#38332E] rounded-lg text-[#1E1B18] dark:text-[#FFFFFF] placeholder:text-[#9A9084] focus:outline-none focus:ring-1 focus:ring-[#1E1B18] dark:focus:ring-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-[#6F675C] dark:text-[#A89E91] mb-1.5">
              {mode === 'login' ? 'Пароль' : 'Придумайте пароль'}
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C8275]" />
              <input
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-3 text-xs bg-white dark:bg-[#262320] border border-[#DFD9CF] dark:border-[#38332E] rounded-lg text-[#1E1B18] dark:text-[#FFFFFF] placeholder:text-[#9A9084] focus:outline-none focus:ring-1 focus:ring-[#1E1B18] dark:focus:ring-white"
              />
            </div>
          </div>

          {mode === 'register' && (
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-[#6F675C] dark:text-[#A89E91] mb-1.5">
                Повторите пароль
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C8275]" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-3 text-xs bg-white dark:bg-[#262320] border border-[#DFD9CF] dark:border-[#38332E] rounded-lg text-[#1E1B18] dark:text-[#FFFFFF] placeholder:text-[#9A9084] focus:outline-none focus:ring-1 focus:ring-[#1E1B18] dark:focus:ring-white"
                />
              </div>
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              className="w-full py-3 px-4 bg-[#1E1B18] hover:bg-black text-white dark:bg-[#FFFFFF] dark:text-[#181614] dark:hover:bg-[#EAE5DE] text-xs uppercase tracking-[0.16em] font-medium rounded-lg transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
            >
              <span>{mode === 'login' ? 'Войти в аккаунт' : 'Завершить регистрацию'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs text-[#6F675C] dark:text-[#A89E91]">
            <button
              type="button"
              onClick={() => {
                setError(null);
                setPassword('');
                setConfirmPassword('');
                setMode(mode === 'login' ? 'register' : 'login');
              }}
              className="underline hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer"
            >
              {mode === 'login'
                ? 'Создать аккаунт'
                : 'Уже зарегистрированы? Войти'}
            </button>
            {onContinueAsGuest && (
              <button
                type="button"
                onClick={onContinueAsGuest}
                className="text-[#8C8275] hover:text-[#1E1B18] dark:hover:text-white transition-colors cursor-pointer"
              >
                Войти как гость
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
