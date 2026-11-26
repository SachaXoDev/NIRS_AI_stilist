interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface WeatherPlace extends Coordinates {
  id: number;
  name: string;
  detail: string;
}

export interface CurrentWeather {
  temperature: number;
  conditions: string[];
}

const SAVED_CITY_KEY = 'closet_weather_city';

function parseWeatherPlace(value: unknown): WeatherPlace | undefined {
  if (typeof value !== 'object' || value === null || !('id' in value) || !('name' in value)
    || !('latitude' in value) || !('longitude' in value)) return;
  const { id, name, latitude, longitude } = value;
  if (typeof id !== 'number' || !Number.isSafeInteger(id) || typeof name !== 'string' || !name.trim()
    || typeof latitude !== 'number' || !Number.isFinite(latitude) || Math.abs(latitude) > 90
    || typeof longitude !== 'number' || !Number.isFinite(longitude) || Math.abs(longitude) > 180) return;
  const parts = 'detail' in value ? [value.detail] : [
    'admin1' in value ? value.admin1 : undefined,
    'country' in value ? value.country : undefined,
  ];
  const detail = parts.filter((part): part is string => typeof part === 'string' && part !== name).join(', ');
  return { id, name, detail, latitude, longitude };
}

export function readSavedWeatherCity(): WeatherPlace | undefined {
  try {
    const saved = localStorage.getItem(SAVED_CITY_KEY);
    return saved ? parseWeatherPlace(JSON.parse(saved)) : undefined;
  } catch {
    return undefined;
  }
}

export function saveWeatherCity(place: WeatherPlace): void {
  // Only explicitly selected city centers, never coordinates returned by the device.
  try {
    localStorage.setItem(SAVED_CITY_KEY, JSON.stringify(place));
  } catch {
    // A blocked or full store must not stop the current weather request.
  }
}

export function locateForWeather(): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (!window.isSecureContext) {
      reject(new Error('Для геолокации откройте приложение через HTTPS или localhost. Или выберите город.'));
      return;
    }
    if (!navigator.geolocation) {
      reject(new Error('Браузер не поддерживает геолокацию. Выберите город.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude }),
      ({ code }) => {
        if (code === 1) {
          reject(new Error('Нет доступа к геолокации. Разрешите её для сайта в браузере или выберите город.'));
        } else if (code === 3) {
          reject(new Error('Браузер не вернул координаты. Выберите город — в следующий раз ждать не придётся.'));
        } else {
          reject(new Error('Браузер не получил координаты. Проверьте, включена ли геолокация для браузера в настройках устройства, или выберите город.'));
        }
      },
      { enableHighAccuracy: false, timeout: 5_000, maximumAge: 5 * 60_000 },
    );
  });
}

async function getJson(url: string, params: Record<string, string>, signal: AbortSignal): Promise<unknown> {
  const endpoint = new URL(url);
  endpoint.search = new URLSearchParams(params).toString();
  const response = await fetch(endpoint, { signal: AbortSignal.any([signal, AbortSignal.timeout(10_000)]) });
  if (!response.ok) throw new Error(`Weather service HTTP ${response.status}`);
  return response.json();
}

export async function searchWeatherPlaces(name: string, signal: AbortSignal): Promise<WeatherPlace[]> {
  const data = await getJson('https://geocoding-api.open-meteo.com/v1/search', {
    name, count: '5', language: 'ru', format: 'json',
  }, signal);
  if (typeof data !== 'object' || data === null || !('results' in data) || !Array.isArray(data.results)) return [];
  return data.results.flatMap((value: unknown) => {
    const place = parseWeatherPlace(value);
    return place ? [place] : [];
  });
}

function conditionLabel(code: number): string {
  if (code === 0) return 'ясно';
  if (code === 1 || code === 2) return 'переменная облачность';
  if (code === 3) return 'пасмурно';
  if (code === 45 || code === 48) return 'туман';
  if ([71, 73, 75, 77, 85, 86].includes(code)) return 'снег';
  if ([56, 57, 66, 67].includes(code)) return 'ледяной дождь';
  if ([95, 96, 99].includes(code)) return 'гроза, дождь';
  if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return 'дождь';
  return '';
}

export async function fetchCurrentWeather({ latitude, longitude }: Coordinates, signal: AbortSignal): Promise<CurrentWeather> {
  const data = await getJson('https://api.open-meteo.com/v1/forecast', {
    latitude: latitude.toFixed(2), longitude: longitude.toFixed(2),
    current: 'temperature_2m,weather_code,wind_speed_10m', temperature_unit: 'celsius', wind_speed_unit: 'kmh',
  }, signal);
  if (typeof data !== 'object' || data === null || !('current' in data)
    || typeof data.current !== 'object' || data.current === null || !('temperature_2m' in data.current)) {
    throw new Error('Missing current weather');
  }
  const temperature = data.current.temperature_2m;
  const code = 'weather_code' in data.current ? data.current.weather_code : undefined;
  const wind = 'wind_speed_10m' in data.current ? data.current.wind_speed_10m : undefined;
  if (typeof temperature !== 'number' || !Number.isFinite(temperature) || temperature < -80 || temperature > 65) {
    throw new Error('Invalid current temperature');
  }
  const conditions: string[] = [];
  const label = typeof code === 'number' ? conditionLabel(code) : '';
  if (label) conditions.push(label);
  if (typeof wind === 'number' && wind >= 30) conditions.push('сильный ветер');
  return { temperature: Math.round(temperature), conditions };
}

export function weatherSummary({ temperature, conditions }: CurrentWeather): string {
  return [`${temperature > 0 ? '+' : ''}${temperature} °C`, ...conditions].join(', ');
}
