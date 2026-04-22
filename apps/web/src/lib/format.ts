/**
 * Display formatters.
 *
 * Centralised so every number / date in the app renders identically.
 * Uses Intl.NumberFormat with tabular widths and no implicit locale
 * fallback — pass the user's locale through a provider when i18n lands.
 */

const LOCALE = "en-US";

export const fmtInt = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });

export const fmtNumber = (value: number, decimals = 2): string =>
  new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);

export const fmtCurrency = (value: number, decimals = 2, code = "USD"): string =>
  new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: code,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);

/** Compact currency (e.g. $2.6T, $408B). */
export const fmtCurrencyCompact = (value: number): string =>
  new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);

export const fmtPercent = (value: number, decimals = 2): string =>
  new Intl.NumberFormat(LOCALE, {
    style: "percent",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);

/** Signed percent change (e.g. +1.24%, -0.87%). */
export const fmtDelta = (value: number, decimals = 2): string => {
  const sign = value > 0 ? "+" : value < 0 ? "" : "";
  return `${sign}${fmtPercent(value, decimals)}`;
};

/** Basis-point helper — accepts either raw bps (120) or a fraction (0.012). */
export const fmtBps = (value: number, asFraction = false): string => {
  const bps = asFraction ? value * 10_000 : value;
  const sign = bps > 0 ? "+" : bps < 0 ? "" : "";
  return `${sign}${Math.round(bps)} bps`;
};

export const fmtDate = (input: string | Date, opts?: Intl.DateTimeFormatOptions): string => {
  const date = input instanceof Date ? input : new Date(input);
  return new Intl.DateTimeFormat(LOCALE, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    ...opts,
  }).format(date);
};

export const fmtTime = (input: string | Date): string => {
  const date = input instanceof Date ? input : new Date(input);
  return new Intl.DateTimeFormat(LOCALE, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
};

export const fmtRelative = (input: string | Date): string => {
  const date = input instanceof Date ? input : new Date(input);
  const delta = Math.round((date.getTime() - Date.now()) / 1000);
  const abs = Math.abs(delta);
  const fmt = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });
  if (abs < 60) return fmt.format(delta, "second");
  if (abs < 3600) return fmt.format(Math.round(delta / 60), "minute");
  if (abs < 86_400) return fmt.format(Math.round(delta / 3600), "hour");
  if (abs < 2_592_000) return fmt.format(Math.round(delta / 86_400), "day");
  return fmt.format(Math.round(delta / 2_592_000), "month");
};

/** Pick the signal colour token for a delta sign. */
export const signalClass = (value: number): string =>
  value > 0 ? "text-signal-pos" : value < 0 ? "text-signal-neg" : "text-fg-muted";
