/** ATI body type IDs */
export const BODY_TYPES: Record<string, number> = {
  "контейнер": 100,
  "тентованный": 200,
  "рефрижератор": 300,
  "реф. с перегородкой": 310,
  "реф. мультирежимный": 312,
  "изотермический": 400,
  "фургон": 500,
  "цельнометаллический": 600,
  "открытый": 700,
  "бортовой": 1100,
  "площадка": 1200,
  "низкорамный": 1300,
  "трал": 1400,
  "самосвал": 1500,
  "цистерна": 1700,
  "автовоз": 1900,
};

/** ATI loading type IDs */
export const LOADING_TYPES: Record<string, number> = {
  "верхняя": 1,
  "боковая": 2,
  "задняя": 4,
  "с полной растентовкой": 8,
  "боковая с 2-х сторон": 4096,
  "налив": 8192,
};

/** ATI unloading type IDs */
export const UNLOADING_TYPES: Record<string, number> = {
  "верхняя": 1,
  "боковая": 2,
  "задняя": 4,
  "с полной растентовкой": 8,
  "боковая с 2-х сторон": 4096,
  "гидроборт": 256,
};

/**
 * Determine body type from cargo description.
 * Matches the logic from Python's select_body_type().
 */
export function selectBodyType(cargoType: string, description = ""): number {
  const text = `${cargoType} ${description}`.toLowerCase();

  if (/мебель|бытовая техника|электроника|одежда/.test(text)) return 500; // фургон
  if (/продукты|мясо|рыба|молоко|заморозка/.test(text)) return 300; // рефрижератор
  if (/металл|трубы|профиль|арматура|пиломатериал|доски/.test(text)) return 1100; // бортовой
  if (/контейнер/.test(text)) return 100; // контейнер

  return 200; // тентованный (default)
}
