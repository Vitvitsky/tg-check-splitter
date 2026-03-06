const CURRENCY_SYMBOLS: Record<string, string> = {
  RUB: "₽",
  USD: "$",
  EUR: "€",
  GBP: "£",
  TRY: "₺",
  KZT: "₸",
};

export function currencySymbol(code: string): string {
  return CURRENCY_SYMBOLS[code] ?? code;
}

export function formatMoney(amount: number, currency: string): string {
  return `${amount.toLocaleString("ru-RU")} ${currencySymbol(currency)}`;
}
