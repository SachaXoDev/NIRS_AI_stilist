import type { ChatThread } from '../types';
import { INITIAL_WARDROBE } from './initialWardrobe';

const shirt = INITIAL_WARDROBE.find((i) => i.id === 'item-1')!;
const blazer = INITIAL_WARDROBE.find((i) => i.id === 'item-2')!;
const palazzo = INITIAL_WARDROBE.find((i) => i.id === 'item-4')!;
const sweater = INITIAL_WARDROBE.find((i) => i.id === 'item-5')!;
const trench = INITIAL_WARDROBE.find((i) => i.id === 'item-6')!;
const sneakers = INITIAL_WARDROBE.find((i) => i.id === 'item-7')!;
const loafers = INITIAL_WARDROBE.find((i) => i.id === 'item-8')!;
const tote = INITIAL_WARDROBE.find((i) => i.id === 'item-9')!;
const scarf = INITIAL_WARDROBE.find((i) => i.id === 'item-10')!;

export const INITIAL_CHAT_THREADS: ChatThread[] = [
  {
    id: 'thread-active',
    title: 'Консультация стилиста',
    createdAt: 'Сегодня, 14:30',
    updatedAt: '14:30',
    messages: [
      {
        id: 'welcome-msg',
        sender: 'assistant',
        timestamp: '14:30',
        text: 'Добро пожаловать в персональный сервис капсульного гардероба 12 STOREEZ.\n\nВ вашей коллекции сейчас 10 продуманных вещей. Опишите повод, погоду или выберите вещь, вокруг которой хотите выстроить образ — я предложу законченный аутфит с точными рекомендациями по слоям и деталям.',
      },
    ],
  },
  {
    id: 'thread-office',
    title: 'Деловая встреча в офисе',
    createdAt: 'Вчера',
    updatedAt: 'Вчера, 17:15',
    messages: [
      {
        id: 'user-office-1',
        sender: 'user',
        timestamp: 'Вчера, 17:10',
        text: 'Подбери сдержанный, статусный образ для встречи с партнерами в офисе. Хочу выглядеть уверенно и элегантно.',
      },
      {
        id: 'ai-office-1',
        sender: 'assistant',
        timestamp: 'Вчера, 17:15',
        text: 'Для деловой встречи идеально подойдет структурированный ансамбль с акцентом на чистые линии костюмной шерсти и органического хлопка.',
        suggestedOutfit: {
          id: 'look-office',
          title: 'Статусная капсула: шерсть и шелк',
          description: 'Комплект из структурированного блейзера прямого кроя, свободных брюк палаццо и акцентного шелкового платка.',
          occasion: 'Деловая встреча / Переговоры',
          items: [blazer, shirt, palazzo, loafers, tote, scarf],
          stylistReasoning: 'Классическое сочетание угольного жакета и жемчужно-серой шерсти палаццо создает безупречный силуэт. Белая рубашка добавляет лицу свежести, а платок каре цвета охры служит деликатным визуальным якорем.',
          matchScore: 97,
          confidenceTips: [
            'Оставьте рубашку заправленной в брюки, слегка приподняв воротник блейзера.',
            'Шелковый платок можно свободно завязать французским узлом или обернуть вокруг ручки сумки.',
            'Массивные лоферы уравновешивают свободный объем брюк палаццо.',
          ],
        },
        referencedItemIds: ['item-2', 'item-1', 'item-4', 'item-8', 'item-9', 'item-10'],
      },
    ],
  },
  {
    id: 'thread-weekend',
    title: 'Выходные в городе (Casual)',
    createdAt: '8 мар',
    updatedAt: '8 мар',
    messages: [
      {
        id: 'user-weekend-1',
        sender: 'user',
        timestamp: '8 мар, 12:20',
        text: 'Что надеть на прогулку по набережной и в кофейню? Обещают прохладу, нужен уютный монохромный образ.',
      },
      {
        id: 'ai-weekend-1',
        sender: 'assistant',
        timestamp: '8 мар, 12:22',
        text: 'Собрал расслабленный многослойный аутфит в теплых природных оттенках экрю и бежевого габардина.',
        suggestedOutfit: {
          id: 'look-weekend',
          title: 'Уютный кашемир и тренчкот',
          description: 'Молочный джемпер из 100% кашемира, прямой деним и классический двубортный тренч.',
          occasion: 'Выходные в городе / Бранч',
          items: [trench, sweater, palazzo, sneakers, tote],
          stylistReasoning: 'Тактильный кашемир в тандеме с ветрозащитным габардином обеспечит комфорт при переменчивой погоде. Мягкая бежево-песочная гамма выглядит утонченно и свежо.',
          matchScore: 94,
          confidenceTips: [
            'Пояс тренча завяжите узлом сзади, чтобы пальто оставалось распахнутым.',
            'Белые кожаные кеды придают образу легкость и современный темп.',
          ],
        },
        referencedItemIds: ['item-6', 'item-5', 'item-4', 'item-7', 'item-9'],
      },
    ],
  },
];
