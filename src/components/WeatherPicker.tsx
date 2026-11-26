import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { CloudDrizzle, LocateFixed, X } from 'lucide-react';
import {
  fetchCurrentWeather, locateForWeather, readSavedWeatherCity, saveWeatherCity, searchWeatherPlaces, weatherSummary,
} from '../services/currentWeather';
import type { CurrentWeather, WeatherPlace } from '../services/currentWeather';

const BUTTON = 'px-2.5 py-1.5 border border-[#DFD9CF] dark:border-night-outline disabled:opacity-40 enabled:cursor-pointer';

type WeatherState =
  | { kind: 'idle' }
  | { kind: 'loading'; message: string }
  | { kind: 'error'; message: string }
  | { kind: 'places'; places: WeatherPlace[] }
  | { kind: 'weather'; place?: WeatherPlace; weather: CurrentWeather };

interface WeatherPickerProps {
  disabled: boolean;
  onUse: (text: string) => void;
  children: ReactNode;
}

export function WeatherPicker({ disabled, onUse, children }: WeatherPickerProps) {
  const [open, setOpen] = useState(false);
  const [savedCity, setSavedCity] = useState(readSavedWeatherCity);
  const [city, setCity] = useState('');
  const [state, setState] = useState<WeatherState>({ kind: 'idle' });
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  const start = (message: string) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setState({ kind: 'loading', message });
    return controller.signal;
  };

  const close = () => {
    request.current?.abort();
    setOpen(false);
    setState({ kind: 'idle' });
  };

  const loadWeather = async (place?: WeatherPlace) => {
    const signal = start(place ? 'Загружаем погоду…' : 'Определяем местоположение…');
    let coordinates;
    try {
      coordinates = place ?? await locateForWeather();
    } catch (error) {
      if (!signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : 'Выберите город.' });
      return;
    }
    if (signal.aborted) return;
    setState({ kind: 'loading', message: 'Загружаем погоду…' });
    try {
      const weather = await fetchCurrentWeather(coordinates, signal);
      if (!signal.aborted) setState({ kind: 'weather', weather, place });
    } catch {
      if (!signal.aborted) setState({ kind: 'error', message: 'Погода недоступна. Можно указать температуру в сообщении.' });
    }
  };

  const selectCity = (place: WeatherPlace) => {
    saveWeatherCity(place);
    setSavedCity(place);
    setCity('');
    void loadWeather(place);
  };

  const findCity = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || city.trim().length < 2) return;
    const signal = start('Ищем город…');
    try {
      const places = await searchWeatherPlaces(city.trim(), signal);
      if (!signal.aborted) setState(places.length ? { kind: 'places', places }
        : { kind: 'error', message: 'Город не найден. Проверьте название.' });
    } catch {
      if (!signal.aborted) setState({ kind: 'error', message: 'Поиск города недоступен. Можно указать температуру в сообщении.' });
    }
  };

  return (
    <>
      {open && (
        <section id="weather-picker" aria-label="Текущая погода" className="relative mb-2 space-y-2 border border-[#DFD9CF] bg-[#FCFAF7] px-3 py-2 text-xs text-[#1E1B18] dark:border-night-divider dark:bg-night-panel dark:text-night-fg">
          <button type="button" onClick={close} aria-label="Закрыть погоду" className="absolute right-2 top-2 cursor-pointer p-1">
            <X className="size-4" aria-hidden="true" />
          </button>
          <div className="flex flex-wrap gap-2 pr-7">
            <button type="button" onClick={() => void loadWeather()} disabled={disabled || state.kind === 'loading'} className={`${BUTTON} flex items-center gap-1`}>
              <LocateFixed className="size-3.5" aria-hidden="true" /> Моё местоположение
            </button>
            <form onSubmit={findCity} className="flex min-w-0 flex-[1_1_9rem] gap-1">
              <input aria-label="Город" placeholder="Город" value={city} maxLength={100}
                onChange={(event) => setCity(event.target.value)} className={`${BUTTON} min-w-0 flex-1 dark:bg-night-field dark:placeholder-night-muted`} />
              <button type="submit" disabled={disabled || city.trim().length < 2} className={BUTTON}>Найти</button>
            </form>
          </div>
          <div role="status" className="empty:hidden">
            {(state.kind === 'loading' || state.kind === 'error') && state.message}
            {state.kind === 'weather' && (
              <p><span className="font-medium">{state.place?.name ?? 'Рядом с вами'}</span>: {weatherSummary(state.weather)}</p>
            )}
          </div>
          {state.kind === 'places' && (
            <ul aria-label="Найденные города" className="max-h-24 space-y-1 overflow-y-auto">
              {state.places.map((place) => (
                <li key={place.id}>
                  <button type="button" disabled={disabled} onClick={() => selectCity(place)} className={`${BUTTON} w-full text-left`}>
                    {place.name}{place.detail && ` · ${place.detail}`}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {state.kind === 'weather' && (
            <button type="button" disabled={disabled} className={`${BUTTON} bg-[#EFECE6] dark:bg-night-hover`} onClick={() => {
              const where = state.place ? ` (${state.place.name})` : '';
              onUse(`Подбери образ на текущую погоду${where}: ${weatherSummary(state.weather)}.`);
              close();
            }}>
              Вставить в сообщение
            </button>
          )}
        </section>
      )}
      <div role="group" aria-label="Быстрые подсказки" tabIndex={0}
        className="flex min-w-0 items-center gap-1.5 overflow-x-auto overscroll-x-contain pb-1">
        <button type="button" disabled={disabled} aria-expanded={open} aria-controls={open ? 'weather-picker' : undefined}
          onClick={() => {
            if (open) close();
            else {
              setOpen(true);
              if (savedCity) void loadWeather(savedCity);
            }
          }}
          className="flex shrink-0 cursor-pointer items-center gap-1.5 whitespace-nowrap border border-[#1E1B18]/30 bg-[#E5DFD5] px-3 py-1.5 text-[11px] font-medium text-[#1E1B18] disabled:opacity-40 dark:border-night-outline dark:bg-night-hover dark:text-night-fg">
          <CloudDrizzle className="size-3.5" aria-hidden="true" /> По погоде
        </button>
        {children}
      </div>
    </>
  );
}
