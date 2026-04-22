import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * `cn` — terse class-name joiner with Tailwind conflict resolution.
 *
 * Use everywhere instead of template strings: keeps conditional classes
 * readable and de-dupes Tailwind utilities with the same atomic group.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Return `value` clamped to [min, max]. */
export const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max);

/** Linear interpolation between two values. */
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

/** Stable hash for memoization keys (not cryptographic). */
export function fingerprint(obj: unknown): string {
  const json = JSON.stringify(obj, Object.keys(obj ?? {}).sort());
  let hash = 0;
  for (let i = 0; i < json.length; i++) {
    hash = (hash * 31 + json.charCodeAt(i)) | 0;
  }
  return hash.toString(36);
}
