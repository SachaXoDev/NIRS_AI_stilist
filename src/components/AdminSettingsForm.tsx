import { useState } from 'react';
import type { FormEvent } from 'react';
import type { RetrievalMode } from '../types';
import { saveAdminSettings } from '../services/adminApi';
import type { AdminSettings } from '../services/adminApi';

const inputClass = 'w-full px-3 py-2 text-xs bg-[#FAF8F5] dark:bg-night-field border border-[#DFD9CF] dark:border-night-outline rounded-lg text-[#1E1B18] dark:text-night-fg';
const modes: Record<RetrievalMode, string> = {
  bm25: 'BM25 — по ключевым словам',
  dense: 'Dense — по смыслу',
  hybrid: 'Hybrid — BM25 + Dense',
  visual: 'Visual — поиск по изображениям',
  multimodal: 'Multimodal — текст + изображения',
};

interface AdminSettingsFormProps {
  tab: 'rag' | 'prompt';
  config: AdminSettings;
  onSaved: (config: AdminSettings) => void;
  onSaving: (saving: boolean) => void;
}

export function AdminSettingsForm({ tab, config, onSaved, onSaving }: AdminSettingsFormProps) {
  const [draft, setDraft] = useState(config.settings);
  const [token, setToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ text: string; error: boolean }>();
  const builtin = config.retriever === 'builtin-bm25';
  const disabled = !config.editable || saving;
  const canSave = Boolean(token.trim()) && (tab === 'rag' || draft.personaPrompt.trim().length >= 10);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || !canSave) return;
    setSaving(true);
    onSaving(true);
    setNotice(undefined);
    try {
      const patch = tab === 'prompt'
        ? { personaPrompt: draft.personaPrompt.trim() }
        : {
          ...(builtin ? {} : { mode: draft.mode, alpha: draft.alpha, visualWeight: draft.visualWeight }),
          temperature: draft.temperature,
        };
      const updated = await saveAdminSettings(patch, token.trim());
      setDraft(updated.settings);
      onSaved(updated);
      setNotice({ text: 'Настройки сохранены на сервере.', error: false });
    } catch (error) {
      setNotice({ text: error instanceof Error ? error.message : 'Не удалось сохранить настройки.', error: true });
    } finally {
      setSaving(false);
      onSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="max-w-3xl p-6 rounded-xl border border-[#DFD9CF] dark:border-night-divider bg-white dark:bg-night-panel space-y-4">
      <div>
        <h2 className="text-base font-semibold">{tab === 'rag' ? 'Поиск и генерация' : 'Тон голоса стилиста'}</h2>
        <p className="mt-1 text-xs text-[#6F675C] dark:text-night-muted">
          Модель: {config.llmModel} ({config.llmProvider}) · Движок поиска: {config.retriever}.
        </p>
      </div>
      {tab === 'rag' ? (
        <>
          {builtin && <p className="text-xs text-amber-800 dark:text-amber-300">Встроенный BM25 не использует эмбеддинги. Режим и веса поиска доступны с wardrobe_rag.</p>}
          {config.llmProvider === 'mock' && <p className="text-xs text-amber-800 dark:text-amber-300">Тестовый генератор не использует температуру и промпт.</p>}
          <fieldset disabled={disabled || builtin} className="space-y-4 disabled:opacity-60">
            <label className="block text-xs">
              <span className="block mb-1">Режим поиска</span>
              <select value={draft.mode} onChange={(e) => setDraft({ ...draft, mode: e.target.value as RetrievalMode })} className={inputClass}>
                {Object.entries(modes).map(([value, title]) => <option key={value} value={value}>{title}</option>)}
              </select>
            </label>
            <label className="block text-xs">
              <span className="block mb-1">Вес Dense (α): {draft.alpha.toFixed(2)}</span>
              <input type="range" min="0" max="1" step="0.01" value={draft.alpha} onChange={(e) => setDraft({ ...draft, alpha: e.target.valueAsNumber })} className="w-full accent-current" />
            </label>
            <label className="block text-xs">
              <span className="block mb-1">Вес визуального поиска (β): {draft.visualWeight.toFixed(2)}</span>
              <input type="range" min="0" max="1" step="0.01" value={draft.visualWeight} onChange={(e) => setDraft({ ...draft, visualWeight: e.target.valueAsNumber })} className="w-full accent-current" />
            </label>
          </fieldset>
          <label className="block text-xs">
            <span className="block mb-1">Температура генерации: {draft.temperature.toFixed(2)}</span>
            <input type="range" min="0" max="2" step="0.01" value={draft.temperature} disabled={disabled} onChange={(e) => setDraft({ ...draft, temperature: e.target.valueAsNumber })} className="w-full accent-current" />
          </label>
        </>
      ) : (
        <label className="block text-xs">
          <span className="block mb-1">Промпт стилиста (10–4000 символов)</span>
          <textarea rows={8} minLength={10} maxLength={4000} required disabled={disabled} value={draft.personaPrompt} onChange={(e) => setDraft({ ...draft, personaPrompt: e.target.value })} className={inputClass} />
        </label>
      )}
      {config.editable ? (
        <>
          <label className="block text-xs">
            <span className="block mb-1">Токен куратора</span>
            <input type="password" autoComplete="off" required disabled={saving} value={token} onChange={(e) => setToken(e.target.value)} className={inputClass} />
          </label>
          <button type="submit" disabled={disabled || !canSave} className="px-5 py-2.5 bg-[#1E1B18] text-white dark:bg-night-accent dark:text-night-ink text-xs uppercase tracking-wider font-medium rounded-lg disabled:opacity-50">
            {saving ? 'Сохраняем…' : 'Сохранить настройки'}
          </button>
        </>
      ) : <p className="text-xs text-[#6F675C] dark:text-night-muted">Только чтение: на сервере не задан ADMIN_TOKEN.</p>}
      {notice && <p role={notice.error ? 'alert' : 'status'} className={notice.error ? 'text-xs text-red-700 dark:text-red-300' : 'text-xs text-emerald-700 dark:text-emerald-300'}>{notice.text}</p>}
    </form>
  );
}
