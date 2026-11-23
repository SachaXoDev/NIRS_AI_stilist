import { useEffect, useState } from 'react';
import type { UserAccount, UserRole, WardrobeItem } from '../types';
import { getUsers, updateUserRole } from '../services/authService';
import { USE_REAL_BACKEND } from '../services/backendConfig';
import { fetchAdminSettings } from '../services/adminApi';
import type { AdminSettings } from '../services/adminApi';
import { AdminSettingsForm } from './AdminSettingsForm';
import {
  ShieldAlert,
  Users,
  Database,
  RefreshCw,
  Activity,
  Layers,
  ArrowUpRight,
  TrendingUp,
  Server,
  Zap,
  LogOut,
} from 'lucide-react';

interface AdminPanelProps {
  currentUser: UserAccount;
  wardrobe: WardrobeItem[];
  threadsCount: number;
  onLogout: () => void;
}

export function AdminPanel({
  currentUser,
  wardrobe,
  threadsCount,
  onLogout,
}: AdminPanelProps) {
  const [users, setUsers] = useState<UserAccount[]>(() => getUsers());
  const [config, setConfig] = useState<AdminSettings>();
  const [configError, setConfigError] = useState('');
  const [configVersion, setConfigVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [adminTab, setAdminTab] = useState<'overview' | 'users' | 'rag' | 'prompt'>('overview');

  useEffect(() => {
    if (!USE_REAL_BACKEND) return;
    const controller = new AbortController();
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(10_000)]);
    void fetchAdminSettings(signal)
      .then((loaded) => { if (!controller.signal.aborted) setConfig(loaded); })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setConfigError(error instanceof Error ? error.message : 'Не удалось загрузить настройки.');
        }
      });
    return () => { controller.abort(); };
  }, [configVersion]);

  const handleRoleToggle = (userId: string, currentRole: UserRole) => {
    const nextRole: UserRole = currentRole === 'admin' ? 'user' : 'admin';
    const updated = updateUserRole(userId, nextRole);
    setUsers(updated);
  };

  const reloadConfig = () => {
    setConfig(undefined);
    setConfigError('');
    setConfigVersion((version) => version + 1);
  };

  const connectionStatus = !USE_REAL_BACKEND ? 'Автономный режим' : config ? 'Сервер подключён' : configError ? 'Ошибка подключения' : 'Подключение…';

  return (
    <div className="flex-1 flex flex-col h-full bg-[#F6F4F0] dark:bg-[#181614] overflow-y-auto">
      {/* Top Banner */}
      <div className="px-6 py-5 border-b border-[#DFD9CF] dark:border-[#2E2A26] bg-[#EFECE6] dark:bg-[#1F1C19] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider uppercase bg-amber-500/15 text-amber-900 dark:text-amber-300 border border-amber-600/20">
              <ShieldAlert className="w-3 h-3" />
              Кабинет управления
            </span>
            <span className="text-[11px] text-[#7C7469] dark:text-[#9F9589]">
              12 STOREEZ ATELIER • УПРАВЛЕНИЕ АТЕЛЬЕ
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-medium tracking-tight text-[#1E1B18] dark:text-[#FFFFFF]">
            Центр управления стилистическим сервисом
          </h1>
          <p className="text-xs text-[#6F675C] dark:text-[#A89E91] mt-0.5">
            Куратор: <strong className="font-medium text-[#1E1B18] dark:text-white">{currentUser.name}</strong> ({currentUser.email}) — статус: <strong>Ведущий стилист-куратор</strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-[#2A2724] hover:bg-red-50 dark:hover:bg-red-950/20 text-red-600 dark:text-red-400 border border-[#DFD9CF] dark:border-[#38332E] rounded-lg tracking-wider uppercase font-medium transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Выйти</span>
          </button>
          {USE_REAL_BACKEND && (
            <button
              onClick={reloadConfig}
              disabled={saving || (!config && !configError)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#1E1B18] text-white dark:bg-white dark:text-[#181614] rounded-lg tracking-wider uppercase font-medium cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Обновить настройки
            </button>
          )}
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="px-6 border-b border-[#DFD9CF] dark:border-[#2E2A26] bg-[#F6F4F0] dark:bg-[#181614] flex gap-6">
        <button
          onClick={() => setAdminTab('overview')}
          disabled={saving}
          className={`py-3 text-xs uppercase tracking-[0.14em] font-medium border-b-2 transition-colors cursor-pointer ${
            adminTab === 'overview'
              ? 'border-[#1E1B18] text-[#1E1B18] dark:border-white dark:text-white'
              : 'border-transparent text-[#7C7469] dark:text-[#9E9487] hover:text-black dark:hover:text-white'
          }`}
        >
          Обзор сервиса
        </button>
        <button
          onClick={() => setAdminTab('users')}
          disabled={saving}
          className={`py-3 text-xs uppercase tracking-[0.14em] font-medium border-b-2 transition-colors cursor-pointer ${
            adminTab === 'users'
              ? 'border-[#1E1B18] text-[#1E1B18] dark:border-white dark:text-white'
              : 'border-transparent text-[#7C7469] dark:text-[#9E9487] hover:text-black dark:hover:text-white'
          }`}
        >
          Клиенты и доступ ({users.length})
        </button>
        <button
          onClick={() => setAdminTab('rag')}
          disabled={saving}
          className={`py-3 text-xs uppercase tracking-[0.14em] font-medium border-b-2 transition-colors cursor-pointer ${
            adminTab === 'rag'
              ? 'border-[#1E1B18] text-[#1E1B18] dark:border-white dark:text-white'
              : 'border-transparent text-[#7C7469] dark:text-[#9E9487] hover:text-black dark:hover:text-white'
          }`}
        >
          Правила подбора образов
        </button>
        <button
          onClick={() => setAdminTab('prompt')}
          disabled={saving}
          className={`py-3 text-xs uppercase tracking-[0.14em] font-medium border-b-2 transition-colors cursor-pointer ${
            adminTab === 'prompt'
              ? 'border-[#1E1B18] text-[#1E1B18] dark:border-white dark:text-white'
              : 'border-transparent text-[#7C7469] dark:text-[#9E9487] hover:text-black dark:hover:text-white'
          }`}
        >
          Тон голоса стилиста 12 STOREEZ
        </button>
      </div>

      {/* Tab Body */}
      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* VIEW 1: OVERVIEW */}
        {adminTab === 'overview' && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-[#DFD9CF] dark:border-[#2E2A26] bg-white dark:bg-[#1E1C19] shadow-xs">
                <div className="flex items-center justify-between text-xs text-[#7C7469] dark:text-[#A4998C] mb-2 uppercase tracking-wider">
                  <span>Активные пользователи</span>
                  <Users className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="text-2xl font-semibold text-[#1E1B18] dark:text-white">
                  {users.length}
                </div>
                <div className="mt-1 text-[11px] text-[#6E665A] dark:text-[#9E9487] flex items-center gap-1">
                  <TrendingUp className="w-3 h-3 text-emerald-600" />
                  <span>{users.filter(u => u.role === 'admin').length} админа, {users.filter(u => u.role === 'user').length} пользователей</span>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[#DFD9CF] dark:border-[#2E2A26] bg-white dark:bg-[#1E1C19] shadow-xs">
                <div className="flex items-center justify-between text-xs text-[#7C7469] dark:text-[#A4998C] mb-2 uppercase tracking-wider">
                  <span>Оцифровано вещей</span>
                  <Database className="w-4 h-4 text-blue-600" />
                </div>
                <div className="text-2xl font-semibold text-[#1E1B18] dark:text-white">
                  {wardrobe.length}
                </div>
                <div className="mt-1 text-[11px] text-[#6E665A] dark:text-[#9E9487]">
                  Каталог: <strong>Кашемир, шелк, деним, костюмы</strong>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[#DFD9CF] dark:border-[#2E2A26] bg-white dark:bg-[#1E1C19] shadow-xs">
                <div className="flex items-center justify-between text-xs text-[#7C7469] dark:text-[#A4998C] mb-2 uppercase tracking-wider">
                  <span>Консультаций стилиста</span>
                  <Activity className="w-4 h-4 text-amber-600" />
                </div>
                <div className="text-2xl font-semibold text-[#1E1B18] dark:text-white">
                  {threadsCount}
                </div>
                <div className="mt-1 text-[11px] text-[#6E665A] dark:text-[#9E9487]">
                  Сервис: <strong>{connectionStatus}</strong>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-[#DFD9CF] dark:border-[#2E2A26] bg-white dark:bg-[#1E1C19] shadow-xs">
                <div className="flex items-center justify-between text-xs text-[#7C7469] dark:text-[#A4998C] mb-2 uppercase tracking-wider">
                  <span>Движок поиска</span>
                  <Zap className="w-4 h-4 text-purple-600" />
                </div>
                <div className="text-sm font-semibold text-[#1E1B18] dark:text-white break-words">
                  {config?.retriever ?? '—'}
                </div>
                <div className="mt-1 text-[11px] text-[#6E665A] dark:text-[#9E9487]">
                  Модель: <strong>{config?.llmModel ?? '—'}</strong>
                </div>
              </div>
            </div>

            {/* Architecture diagram & Status */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 p-5 rounded-xl border border-[#DFD9CF] dark:border-[#2E2A26] bg-white dark:bg-[#1E1C19]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[#1E1B18] dark:text-white mb-3 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#8C8275]" />
                  Как работает персональный подбор 12 STOREEZ
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-lg border border-[#E5DFD5] dark:border-[#322D28] bg-[#FAF8F5] dark:bg-[#24211E]">
                    <div className="font-semibold text-[#1E1B18] dark:text-white mb-1">
                      1. Анализ гардероба
                    </div>
                    <p className="text-[#6F675C] dark:text-[#A89E91] text-[11px] leading-relaxed">
                      Считывание фасонов, тканей, цветотипа и посадки вещей клиентки из ее цифрового гардероба.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#E5DFD5] dark:border-[#322D28] bg-[#FAF8F5] dark:bg-[#24211E]">
                    <div className="font-semibold text-[#1E1B18] dark:text-white mb-1">
                      2. Подбор по контексту
                    </div>
                    <p className="text-[#6F675C] dark:text-[#A89E91] text-[11px] leading-relaxed">
                      Умный поиск идеальных сочетаний под повод: деловая встреча, ужин, прохладная погода или путешествие.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#E5DFD5] dark:border-[#322D28] bg-[#FAF8F5] dark:bg-[#24211E]">
                    <div className="font-semibold text-[#1E1B18] dark:text-white mb-1">
                      3. Готовый аутфит и совет
                    </div>
                    <p className="text-[#6F675C] dark:text-[#A89E91] text-[11px] leading-relaxed">
                      Подача законченного образа в премиальном стиле 12 STOREEZ с подсказками по стайлингу и акцентам.
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-[#DFD9CF] dark:border-[#2D2925] flex items-center justify-between text-xs text-[#7C7469] dark:text-[#9F9589]">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${config ? 'bg-emerald-500' : 'bg-[#8A8175]'}`} />
                    <span>{connectionStatus}</span>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="p-5 rounded-xl border border-[#DFD9CF] dark:border-[#2E2A26] bg-white dark:bg-[#1E1C19] flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-[#1E1B18] dark:text-white mb-3 flex items-center gap-2">
                    <Server className="w-4 h-4 text-[#8C8275]" />
                    Быстрые операции
                  </h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => setAdminTab('users')}
                      className="w-full py-2 px-3 text-xs text-left rounded-lg border border-[#DFD9CF] dark:border-[#322D28] hover:bg-[#FAF8F5] dark:hover:bg-[#25221F] text-[#1E1B18] dark:text-white flex items-center justify-between transition-colors cursor-pointer"
                    >
                      <span>Клиентская база и права доступа</span>
                      <ArrowUpRight className="w-3.5 h-3.5 text-[#8C8275]" />
                    </button>
                    <button
                      onClick={() => setAdminTab('rag')}
                      className="w-full py-2 px-3 text-xs text-left rounded-lg border border-[#DFD9CF] dark:border-[#322D28] hover:bg-[#FAF8F5] dark:hover:bg-[#25221F] text-[#1E1B18] dark:text-white flex items-center justify-between transition-colors cursor-pointer"
                    >
                      <span>Настройка правил комплектации</span>
                      <ArrowUpRight className="w-3.5 h-3.5 text-[#8C8275]" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 p-3 rounded-lg bg-[#FAF8F5] dark:bg-[#24211E] border border-[#E5DFD5] dark:border-[#332E29] text-[11px] text-[#6E665A] dark:text-[#A69B8E]">
                  Роли клиентов хранятся локально. Серверные настройки защищены отдельным токеном куратора.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: USERS LIST */}
        {adminTab === 'users' && (
          <div className="space-y-4 animate-in fade-in duration-200">
            <div>
              <h2 className="text-base font-semibold text-[#1E1B18] dark:text-white">
                Пользователи и уровни доступа (RBAC)
              </h2>
              <p className="text-xs text-[#6F675C] dark:text-[#A89E91]">
                Разграничение прав: переключение ролей Пользователь ↔ Администратор в 1 клик.
              </p>
            </div>

            <div className="border border-[#DFD9CF] dark:border-[#2E2A26] rounded-xl overflow-hidden bg-white dark:bg-[#1E1C19]">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#EFECE6] dark:bg-[#24211E] text-[#6F675C] dark:text-[#A89E91] uppercase tracking-wider border-b border-[#DFD9CF] dark:border-[#2E2A26]">
                    <tr>
                      <th className="py-3 px-4 font-medium">Пользователь</th>
                      <th className="py-3 px-4 font-medium">Email</th>
                      <th className="py-3 px-4 font-medium">Статус</th>
                      <th className="py-3 px-4 font-medium">Текущая роль</th>
                      <th className="py-3 px-4 font-medium">Дата регистрации</th>
                      <th className="py-3 px-4 font-medium text-right">Действие</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#DFD9CF] dark:divide-[#2E2A26] text-[#1E1B18] dark:text-white">
                    {users.map((user) => (
                      <tr key={user.id} className="hover:bg-[#FAF8F5] dark:hover:bg-[#23201D] transition-colors">
                        <td className="py-3 px-4 flex items-center gap-3">
                          <img
                            src={user.avatarUrl || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80'}
                            alt={user.name}
                            className="w-8 h-8 rounded-full object-cover border border-[#DFD9CF] dark:border-[#38332E]"
                          />
                          <div>
                            <div className="font-medium">{user.name}</div>
                            {user.id === currentUser.id && (
                              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">
                                (вы сейчас авторизованы)
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-[#5A534A] dark:text-[#C4BCB2]">
                          {user.email}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] uppercase font-medium bg-[#EFECE6] dark:bg-[#2B2724] text-[#5A534A] dark:text-[#D4CBC0]">
                            {user.vipStatus || 'Active'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                              user.role === 'admin'
                                ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/50'
                                : 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700/50'
                            }`}
                          >
                            {user.role === 'admin' ? 'Администратор' : 'Клиент'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[#7C7469] dark:text-[#9F9589]">
                          {user.createdAt}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleRoleToggle(user.id, user.role)}
                            className="px-2.5 py-1 text-[11px] uppercase tracking-wider font-medium border border-[#DFD9CF] dark:border-[#38332E] hover:border-[#1E1B18] dark:hover:border-white rounded-md transition-colors cursor-pointer"
                          >
                            {user.role === 'admin' ? 'Сделать Клиентом' : 'Назначить Админом'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {(adminTab === 'rag' || adminTab === 'prompt') && (
          config ? (
            <AdminSettingsForm key={adminTab} tab={adminTab} config={config} onSaved={setConfig} onSaving={setSaving} />
          ) : (
            <p role={configError ? 'alert' : 'status'} className="text-sm text-[#6F675C] dark:text-[#A89E91]">
              {!USE_REAL_BACKEND
                ? 'Серверные настройки недоступны в автономном режиме. Включите VITE_USE_REAL_BACKEND и запустите FastAPI.'
                : configError || 'Загружаем настройки сервера…'}
            </p>
          )
        )}
      </div>
    </div>
  );
}
