import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

/**
 * Global test setup.
 *
 * - Wires @testing-library/jest-dom matchers onto Vitest's `expect`.
 * - Auto-cleans the DOM between tests so state from one test can't leak
 *   into another.
 * - Stubs browser APIs jsdom doesn't implement (IntersectionObserver,
 *   ResizeObserver, matchMedia) so the Reveal component and charts
 *   don't throw on mount.
 */

afterEach(() => {
  cleanup();
});

class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin: string = "";
  readonly thresholds: ReadonlyArray<number> = [];
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

class MockResizeObserver implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

globalThis.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;
globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
