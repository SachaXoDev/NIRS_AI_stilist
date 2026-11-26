import type { ClothingCategory, WardrobeRecognitionResponse } from '../types';
import { BACKEND_URL } from './backendConfig';
import { cleanMaterialDetails } from './materialDetails';
import { isClothingSeason } from './wardrobeSeason';

export const WARDROBE_PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp';
const MAX_SOURCE_BYTES = 30 * 1024 * 1024;
const MAX_PREVIEW_LENGTH = Math.ceil(96 * 1024 / 3) * 4 + 'data:image/jpeg;base64,'.length;
const CATEGORIES: Record<ClothingCategory, true> = {
  tops: true, bottoms: true, outerwear: true, shoes: true, accessories: true,
};

async function isSupportedImage(file: File) {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const matches = (offset: number, signature: number[]) =>
    signature.every((byte, index) => bytes[offset + index] === byte);
  return matches(0, [0xff, 0xd8, 0xff]) ||
    matches(0, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]) ||
    (matches(0, [0x52, 0x49, 0x46, 0x46]) && matches(8, [0x57, 0x45, 0x42, 0x50]));
}

export async function prepareWardrobePhoto(file: File, signal: AbortSignal, makeUpload: boolean) {
  if (!file.size) throw new Error('Файл пуст. Выберите другое фото.');
  if (file.size > MAX_SOURCE_BYTES) throw new Error('Фото больше 30 МБ. Выберите файл меньшего размера.');
  if (!await isSupportedImage(file)) throw new Error('Выберите фото в формате JPEG, PNG или WebP.');
  signal.throwIfAborted();

  const source = URL.createObjectURL(file);
  const image = new Image();
  const cancelDecode = () => image.removeAttribute('src');
  signal.addEventListener('abort', cancelDecode, { once: true });
  try {
    image.src = source;
    try {
      await image.decode();
    } catch {
      throw new Error('Не удалось открыть фото. Возможно, файл повреждён.');
    }
    signal.throwIfAborted();

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Не удалось подготовить фото в этом браузере.');

    // Browser decoding applies the source orientation; re-encoding also removes EXIF metadata.
    const draw = (maxSide: number) => {
      const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      context.fillStyle = '#fff';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
    };
    let upload: Blob | null = null;
    if (makeUpload) {
      draw(1600);
      const { promise, resolve } = Promise.withResolvers<Blob | null>();
      canvas.toBlob(resolve, 'image/jpeg', 0.92);
      upload = await promise;
      signal.throwIfAborted();
      if (!upload) throw new Error('Не удалось подготовить фото для распознавания.');
    }
    for (const [maxSide, quality] of [[768, 0.8], [512, 0.72], [320, 0.65]]) {
      draw(maxSide);
      const preview = canvas.toDataURL('image/jpeg', quality);
      if (preview.startsWith('data:image/jpeg;base64,') && preview.length <= MAX_PREVIEW_LENGTH) return { preview, upload };
    }
    throw new Error('Не удалось уменьшить фото. Выберите другой файл.');
  } finally {
    signal.removeEventListener('abort', cancelDecode);
    URL.revokeObjectURL(source);
  }
}

// Null here means the recognizer is unavailable; a null suggestion means it found no evidence.
export async function recognizeWardrobePhoto(upload: Blob, signal: AbortSignal, labelOnly: boolean): Promise<WardrobeRecognitionResponse | null> {
  const timeout = AbortSignal.timeout(60_000);
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/api/wardrobe/recognize${labelOnly ? '?label_only=true' : ''}`, {
      method: 'POST',
      headers: { 'Content-Type': 'image/jpeg' },
      body: upload,
      signal: AbortSignal.any([signal, timeout]),
    });
  } catch {
    signal.throwIfAborted();
    if (timeout.aborted) throw new Error('Не дождались ответа сервера.');
    return null;
  }
  if (response.status === 503) return null;
  if (response.status === 413) throw new Error('Сервер отклонил фото из-за размера.');
  if (response.status === 422) throw new Error('Сервер не смог обработать фото.');
  if (!response.ok) throw new Error(`Сервер не вернул подсказку (HTTP ${response.status}).`);

  const result: unknown = await response.json();
  if (result && typeof result === 'object' && 'suggestion' in result) {
    const { suggestion } = result;
    if (suggestion === null) return { suggestion: null };
    if (suggestion && typeof suggestion === 'object') {
      const { title, category, season, color, material, materialDetails, brand } = suggestion as Record<string, unknown>;
      if ((title === null || typeof title === 'string') &&
        (category === null || (typeof category === 'string' && Object.hasOwn(CATEGORIES, category))) &&
        (color === null || typeof color === 'string') &&
        (material === null || typeof material === 'string') &&
        (brand === null || typeof brand === 'string')) {
        return {
          suggestion: {
            title: title?.trim() || null,
            category: category as ClothingCategory | null,
            season: isClothingSeason(season) ? season : null,
            color: color?.trim() || null,
            material: material?.trim() || null,
            materialDetails: cleanMaterialDetails(materialDetails),
            brand: brand?.trim() || null,
          },
        };
      }
    }
  }
  throw new Error('Сервер вернул неверный формат подсказки.');
}
