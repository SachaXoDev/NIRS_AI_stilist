import type { ClothingCategory } from '../types';

// Match whole garment words, not brand fragments. More than one slot is ambiguous.
const GARMENT_WORDS: Record<ClothingCategory, RegExp> = {
  shoes: /^(?:обувь|кроссовк[а-я]*|кроссовок|кед[аы]?|туфл[а-я]*|лофер[а-я]*|лодочки|балетк[а-я]*|ботин[а-я]*|ботильон[а-я]*|сапог[а-я]*|сандал[а-я]*|босоножк[а-я]*|мокасин[а-я]*|shoes?|sneakers?|trainers?|boots?|sandals?|loafers?)$/iu,
  outerwear: /^(?:верхн[а-я]+ одежд[а-я]*|пальто|тренч[а-я]*|плащ[а-я]*|куртк[а-я]*|парка|пуховик[а-я]*|ветровк[а-я]*|жакет[а-я]*|блейзер[а-я]*|пиджак[а-я]*|бомбер[а-я]*|джинсовк[а-я]*|coats?|jackets?|blazers?|parkas?)$/iu,
  tops: /^(?:верх|футболк[а-я]*|топы?|майк[а-я]*|рубашк[а-я]*|блуз[а-я]*|свитер[а-я]*|худи|джемпер[а-я]*|кардиган[а-я]*|свитшот[а-я]*|водолазк[а-я]*|shirts?|blouses?|sweaters?|hoodies?|cardigans?|tops?)$/iu,
  bottoms: /^(?:брюк[а-я]*|джинсы|юбк[а-я]*|шорт[а-я]*|штан[а-я]*|лег[г]?инс[а-я]*|jeans|trousers|pants|skirts?|shorts|leggings)$/iu,
  accessories: /^(?:аксессуар[а-я]*|сумк[а-я]*|рюкзак[а-я]*|шарф[а-я]*|платок|платк[а-я]*|ремень|ремни|шапк[а-я]*|кепк[а-я]*|головн[а-я]+ убор[а-я]*|шляп[а-я]*|bags?|backpacks?|scar(?:f|ves)|belts?|hats?|caps?)$/iu,
};

export function categoryFromTitle(title: string): ClothingCategory | undefined {
  const words = title.match(/\p{L}+/gu) ?? [];
  const matches = (Object.keys(GARMENT_WORDS) as ClothingCategory[]).filter((category) =>
    words.some((word, i) => GARMENT_WORDS[category].test(word) ||
      (i > 0 && GARMENT_WORDS[category].test(`${words[i - 1]} ${word}`))),
  );
  return matches.length === 1 ? matches[0] : undefined;
}
