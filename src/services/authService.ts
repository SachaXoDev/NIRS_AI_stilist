import type { UserAccount, UserRole } from '../types';

const CURRENT_USER_KEY = 'closet_current_user_v3';
const USERS_LIST_KEY = 'closet_users_list_v3';

export const INITIAL_USERS: UserAccount[] = [
  {
    id: 'user-elena',
    name: 'Елена Воронова',
    email: 'elena@12storeez.com',
    role: 'user',
    password: 'password123',
    vipStatus: 'VIP Atelier Member',
    createdAt: '15 января 2026',
  },
  {
    id: 'admin-alex',
    name: 'Александр Смирнов',
    email: 'admin@12storeez.com',
    role: 'admin',
    password: 'adminpassword',
    vipStatus: 'RAG Lead Architect',
    createdAt: '01 декабря 2025',
  },
  {
    id: 'user-daria',
    name: 'Дарья Романова',
    email: 'daria@12storeez.com',
    role: 'user',
    password: 'password123',
    vipStatus: 'Client',
    createdAt: '02 марта 2026',
  },
];

export function getUsers(): UserAccount[] {
  try {
    const raw = localStorage.getItem(USERS_LIST_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch (e) {
    console.error('Failed to read users list', e);
  }
  localStorage.setItem(USERS_LIST_KEY, JSON.stringify(INITIAL_USERS));
  return INITIAL_USERS;
}

export function saveUsers(users: UserAccount[]): void {
  localStorage.setItem(USERS_LIST_KEY, JSON.stringify(users));
}

export function getCurrentUser(): UserAccount | null {
  try {
    const raw = localStorage.getItem(CURRENT_USER_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    console.error('Failed to read current user', e);
  }
  return null;
}

export function setCurrentUser(user: UserAccount | null): void {
  if (user) {
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(CURRENT_USER_KEY);
  }
}

export function loginUser(
  email: string,
  password?: string
): { success: boolean; user?: UserAccount; error?: string } {
  const users = getUsers();
  const normalizedEmail = email.trim().toLowerCase();

  if (!password || !password.trim()) {
    return { success: false, error: 'Пожалуйста, введите пароль' };
  }

  const found = users.find((u) => u.email.toLowerCase() === normalizedEmail);

  if (!found) {
    return {
      success: false,
      error: 'Пользователь с таким email не найден. Проверьте адрес или создайте новый аккаунт.',
    };
  }

  // Строгая проверка пароля
  if (found.password && found.password !== password) {
    return { success: false, error: 'Неверный пароль. Пожалуйста, попробуйте еще раз.' };
  }

  setCurrentUser(found);
  return { success: true, user: found };
}

export function registerUser(
  name: string,
  email: string,
  password?: string,
  role: UserRole = 'user'
): { success: boolean; user?: UserAccount; error?: string } {
  const users = getUsers();
  const normalizedEmail = email.trim().toLowerCase();

  if (!password || password.length < 6) {
    return { success: false, error: 'Пароль должен быть не короче 6 символов' };
  }

  const existing = users.find((u) => u.email.toLowerCase() === normalizedEmail);
  if (existing) {
    return { success: false, error: 'Пользователь с таким email уже зарегистрирован' };
  }

  const newUser: UserAccount = {
    id: `${role}-${Date.now()}`,
    name: name.trim() || (role === 'admin' ? 'Администратор' : 'Клиент'),
    email: normalizedEmail,
    role,
    password,
    vipStatus: role === 'admin' ? 'Curator RAG' : 'Client Club',
    createdAt: 'Сегодня',
  };

  const updated = [newUser, ...users];
  saveUsers(updated);
  setCurrentUser(newUser);
  return { success: true, user: newUser };
}

export function logoutUser(): void {
  localStorage.removeItem(CURRENT_USER_KEY);
}

export function quickLogin(role: UserRole): UserAccount {
  const users = getUsers();
  const target =
    users.find((u) => u.role === role) ||
    (role === 'admin' ? INITIAL_USERS[1] : INITIAL_USERS[0]);
  setCurrentUser(target);
  return target;
}

export function updateUserRole(userId: string, newRole: UserRole): UserAccount[] {
  const users = getUsers().map((u) => (u.id === userId ? { ...u, role: newRole } : u));
  saveUsers(users);
  const current = getCurrentUser();
  if (current && current.id === userId) {
    setCurrentUser({ ...current, role: newRole });
  }
  return users;
}
