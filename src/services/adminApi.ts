import type { RetrievalMode } from '../types';
import { BACKEND_URL } from './backendConfig';

export interface RuntimeSettings {
  mode: RetrievalMode;
  alpha: number;
  visualWeight: number;
  temperature: number;
  personaPrompt: string;
}

export interface AdminSettings {
  settings: RuntimeSettings;
  llmProvider: string;
  llmModel: string;
  retriever: string;
  editable: boolean;
}

export async function fetchAdminSettings(signal: AbortSignal): Promise<AdminSettings> {
  const response = await fetch(`${BACKEND_URL}/api/admin/settings`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error(`Сервер не вернул настройки (HTTP ${response.status}).`);
  return response.json();
}

export async function saveAdminSettings(patch: Partial<RuntimeSettings>, token: string): Promise<AdminSettings> {
  const response = await fetch(`${BACKEND_URL}/api/admin/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
    body: JSON.stringify(patch),
    signal: AbortSignal.timeout(10_000),
  });
  if (response.status === 401) throw new Error('Неверный токен куратора. Проверьте его и повторите попытку.');
  if (response.status === 403) throw new Error('Редактирование настроек отключено на сервере.');
  if (!response.ok) throw new Error(`Сервер не сохранил настройки (HTTP ${response.status}).`);
  return response.json();
}
