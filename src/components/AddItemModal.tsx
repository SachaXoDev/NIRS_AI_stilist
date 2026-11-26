import { useLayoutEffect, useRef, useState } from 'react';
import type { ClothingCategory, WardrobeItem, WardrobeRecognitionResponse } from '../types';
import { Camera, Check, FileText, X } from 'lucide-react';
import { USE_REAL_BACKEND } from '../services/backendConfig';
import { prepareWardrobePhoto, recognizeWardrobePhoto, WARDROBE_PHOTO_ACCEPT } from '../services/wardrobeRecognition';

interface AddItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: WardrobeItem) => void;
}

const CATEGORY_OPTIONS: { value: ClothingCategory; label: string }[] = [
  { value: 'tops', label: 'Верх' },
  { value: 'bottoms', label: 'Брюки и юбки' },
  { value: 'outerwear', label: 'Верхняя одежда' },
  { value: 'shoes', label: 'Обувь' },
  { value: 'accessories', label: 'Аксессуары' },
];

type PhotoStatus = 'idle' | 'pending' | 'success' | 'uncertain' | 'error' | 'offline';
type ItemFields = { title: string; category: ClothingCategory | ''; color: string; material: string; brand: string };
const IDLE_PHOTO_STATUS: { state: PhotoStatus; message: string } = { state: 'idle', message: '' };
const FIELD_LABEL = 'mb-1 block text-xs text-[#6B6258] dark:text-[#BFB3A6]';
const FIELD_INPUT = 'h-11 w-full min-w-0 rounded-lg border border-[#DFD9CF] bg-[#EFECE6] px-3 text-base text-[#1E1B18] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8A8175] sm:text-sm dark:border-[#38332E] dark:bg-[#25221F] dark:text-[#F7F5F0]';
const UPLOAD_ROW = 'flex min-w-0 items-center rounded-lg border border-[#DFD9CF] bg-[#F6F4F0] dark:border-[#38332E] dark:bg-[#22201D]';
const UPLOAD_ACTION = 'relative flex min-h-11 min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium text-[#1E1B18] hover:bg-black/5 focus-within:outline-2 focus-within:outline-[#8A8175] dark:text-[#F7F5F0] dark:hover:bg-white/5';
const ICON_BUTTON = 'flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-lg text-[#6B6258] hover:text-[#1E1B18] focus-visible:outline-2 focus-visible:outline-[#8A8175] dark:text-[#BFB3A6] dark:hover:text-white';
const UPLOAD_STATUS = 'mt-1 text-xs text-[#6B6258] empty:hidden dark:text-[#BFB3A6]';

export const AddItemModal = ({ isOpen, ...props }: AddItemModalProps) =>
  isOpen ? <AddItemForm {...props} /> : null;

const AddItemForm = ({ onClose, onAdd }: Omit<AddItemModalProps, 'isOpen'>) => {
  const [fields, setFields] = useState<Partial<ItemFields>>({});
  const [suggestion, setSuggestion] = useState<WardrobeRecognitionResponse['suggestion']>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoStatus, setPhotoStatus] = useState(IDLE_PHOTO_STATUS);
  const [labelSuggestion, setLabelSuggestion] = useState<WardrobeRecognitionResponse['suggestion']>(null);
  const [labelStatus, setLabelStatus] = useState(IDLE_PHOTO_STATUS);
  const request = useRef<AbortController | null>(null);

  useLayoutEffect(() => () => request.current?.abort(), []);

  const editField = <K extends keyof ItemFields,>(key: K, value: ItemFields[K]) => {
    setFields((current) => ({ ...current, [key]: value }));
  };

  const clearPhoto = () => {
    request.current?.abort();
    request.current = null;
    setPhotoPreview(null);
    setSuggestion(null);
    setPhotoStatus(IDLE_PHOTO_STATUS);
    setLabelSuggestion(null);
    setLabelStatus(IDLE_PHOTO_STATUS);
  };

  const handlePhotoUpload = (labelOnly: boolean) => async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.currentTarget.files?.[0];
    e.currentTarget.value = '';
    if (!file) return;

    if (labelOnly) {
      request.current?.abort();
      setLabelSuggestion(null);
    } else {
      clearPhoto();
    }
    const setStatus = labelOnly ? setLabelStatus : setPhotoStatus;
    const setResult = labelOnly ? setLabelSuggestion : setSuggestion;
    const controller = new AbortController();
    request.current = controller;
    const { signal } = controller;
    setStatus({ state: 'pending', message: 'Готовим фото…' });

    try {
      const { preview, upload } = await prepareWardrobePhoto(file, signal, USE_REAL_BACKEND && navigator.onLine);
      if (signal.aborted) return;
      if (!labelOnly) setPhotoPreview(preview);
      if (!upload) {
        setStatus({ state: 'offline', message: 'Распознавание недоступно.' });
        return;
      }

      setStatus({ state: 'pending', message: labelOnly ? 'Читаем текст…' : 'Распознаём вещь…' });
      const result = await recognizeWardrobePhoto(upload, signal, labelOnly);
      if (signal.aborted) return;
      if (!result) {
        setStatus({ state: 'offline', message: 'Распознавание недоступно.' });
      } else if (!result.suggestion) {
        setStatus({ state: 'uncertain', message: labelOnly ? 'Не нашли характеристики.' : 'Не распознали вещь.' });
      } else {
        setResult(result.suggestion);
        setStatus({ state: 'success', message: '' });
      }
    } catch (error) {
      if (signal.aborted) return;
      const message = error instanceof Error ? error.message : 'Не удалось обработать фото.';
      setStatus({ state: 'error', message });
    } finally {
      if (request.current === controller) request.current = null;
    }
  };

  const handleClose = () => {
    request.current?.abort();
    onClose();
  };

  // Even an intentionally cleared field takes precedence over a late suggestion.
  const title = fields.title ?? labelSuggestion?.title ?? suggestion?.title ?? '';
  const category = fields.category ?? labelSuggestion?.category ?? suggestion?.category ?? '';
  const color = fields.color ?? labelSuggestion?.color ?? suggestion?.color ?? '';
  const material = fields.material ?? labelSuggestion?.material ?? suggestion?.material ?? '';
  const brand = fields.brand ?? labelSuggestion?.brand ?? suggestion?.brand ?? '';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !category) return;

    let defaultImage = '/clothes/shirt.svg';
    if (category === 'bottoms') defaultImage = '/clothes/palazzo.svg';
    if (category === 'outerwear') defaultImage = '/clothes/blazer.svg';
    if (category === 'shoes') defaultImage = '/clothes/loafers.svg';
    if (category === 'accessories') defaultImage = '/clothes/tote.svg';

    const newItem: WardrobeItem = {
      id: `custom-${Date.now()}`,
      title: title.trim(),
      category,
      color: color.trim(),
      season: 'all',
      style: [],
      tags: [category, color.trim().toLowerCase(), material.trim().toLowerCase()].filter(Boolean),
      brand: brand.trim(),
      material: material.trim(),
      imageUrl: photoPreview || defaultImage,
      uploadedAt: new Date().toISOString(),
    };

    onAdd(newItem);
    handleClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs">
      <div role="dialog" aria-modal="true" aria-labelledby="add-item-heading" className="relative max-h-full w-full max-w-md overflow-y-auto rounded-xl border border-[#DFD9CF] bg-[#FCFAF7] p-4 shadow-2xl sm:p-5 dark:border-[#2E2A26] dark:bg-[#1C1A18]">
        <div className="mb-3 flex items-center justify-between">
          <h3 id="add-item-heading" className="text-base font-medium text-[#1E1B18] dark:text-[#F7F5F0]">
            Новая вещь
          </h3>
          <button type="button" aria-label="Закрыть" onClick={handleClose} className={`${ICON_BUTTON} -mr-2`}>
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="mb-4 space-y-2">
          <div>
            <div className={UPLOAD_ROW}>
              <label htmlFor="add-item-photo" className={UPLOAD_ACTION}>
                <input
                  id="add-item-photo"
                  type="file"
                  accept={WARDROBE_PHOTO_ACCEPT}
                  className="sr-only"
                  aria-label={photoPreview ? 'Заменить фото вещи' : 'Добавить фото вещи'}
                  aria-describedby="add-item-photo-status"
                  onChange={handlePhotoUpload(false)}
                />
                {photoPreview ? (
                  <img src={photoPreview} alt="" className="size-8 shrink-0 rounded object-contain" />
                ) : <Camera className="size-4 shrink-0" aria-hidden="true" />}
                {photoPreview ? 'Заменить фото' : 'Фото вещи'}
              </label>
              {(photoPreview || photoStatus.state === 'pending') && (
                <button type="button" onClick={clearPhoto} aria-label="Удалить фото вещи" className={ICON_BUTTON}>
                  <X className="size-4" aria-hidden="true" />
                </button>
              )}
            </div>
            <p id="add-item-photo-status" role="status" data-status={photoStatus.state} className={UPLOAD_STATUS}>{photoStatus.message}</p>
          </div>
          {USE_REAL_BACKEND && photoPreview && (
            <div>
              <div className={UPLOAD_ROW}>
                <label htmlFor="add-item-label" className={`${UPLOAD_ACTION} has-disabled:cursor-not-allowed has-disabled:opacity-50`}>
                  <input
                    id="add-item-label"
                    type="file"
                    accept={WARDROBE_PHOTO_ACCEPT}
                    className="sr-only"
                    aria-label={labelStatus.state === 'idle' ? 'Добавить бирку или скриншот' : 'Заменить бирку или скриншот'}
                    aria-describedby="add-item-label-status"
                    disabled={photoStatus.state === 'pending'}
                    onChange={handlePhotoUpload(true)}
                  />
                  {labelStatus.state === 'success' ? <Check className="size-4 shrink-0" aria-hidden="true" /> : <FileText className="size-4 shrink-0" aria-hidden="true" />}
                  {labelStatus.state === 'idle' ? 'Бирка или скриншот' : 'Заменить бирку или скриншот'}
                </label>
                {labelStatus.state !== 'idle' && (
                  <button type="button" aria-label="Удалить бирку или скриншот" className={ICON_BUTTON} onClick={() => {
                    request.current?.abort();
                    request.current = null;
                    setLabelSuggestion(null);
                    setLabelStatus(IDLE_PHOTO_STATUS);
                  }}>
                    <X className="size-4" aria-hidden="true" />
                  </button>
                )}
              </div>
              <p id="add-item-label-status" role="status" data-status={labelStatus.state} className={UPLOAD_STATUS}>{labelStatus.message}</p>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="add-item-title" className={FIELD_LABEL}>
              Название
            </label>
            <input
              id="add-item-title"
              type="text"
              required
              value={title}
              onChange={(e) => editField('title', e.target.value)}
              className={FIELD_INPUT}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="add-item-category" className={FIELD_LABEL}>
                Категория
              </label>
              <select
                id="add-item-category"
                required
                value={category}
                onChange={(e) => editField('category', e.target.value as ItemFields['category'])}
                className={FIELD_INPUT}
              >
                <option value="">Выбрать</option>
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="add-item-color" className={FIELD_LABEL}>
                Цвет
              </label>
              <input
                id="add-item-color"
                type="text"
                value={color}
                onChange={(e) => editField('color', e.target.value)}
                className={FIELD_INPUT}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="add-item-material" className={FIELD_LABEL}>
                Материал
              </label>
              <input
                id="add-item-material"
                type="text"
                value={material}
                onChange={(e) => editField('material', e.target.value)}
                className={FIELD_INPUT}
              />
            </div>

            <div>
              <label htmlFor="add-item-brand" className={FIELD_LABEL}>
                Бренд
              </label>
              <input
                id="add-item-brand"
                type="text"
                value={brand}
                onChange={(e) => editField('brand', e.target.value)}
                className={FIELD_INPUT}
              />
            </div>
          </div>

          <div className="pt-1">
            <button
              type="submit"
              disabled={!title.trim() || !category}
              className="min-h-11 w-full rounded-lg bg-[#1E1B18] px-5 text-sm font-medium text-[#F7F5F0] transition-colors hover:bg-[#322E2A] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8A8175] enabled:cursor-pointer disabled:opacity-45 dark:bg-[#F7F5F0] dark:text-[#1E1B18] dark:hover:bg-[#EBE7DF]"
            >
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};