"use client";

import * as React from "react";
import { SWRConfig } from "swr";

import { swrFetcher } from "@/lib/api";

type Theme = "system" | "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  resolved: "light" | "dark";
  setTheme: (t: Theme) => void;
}

const ThemeContext = React.createContext<ThemeContextValue>({
  theme: "system",
  resolved: "dark",
  setTheme: () => undefined,
});

export function useTheme() {
  return React.useContext(ThemeContext);
}

const STORAGE_KEY = "asciip-theme";

/**
 * Read the saved preference synchronously on first render.
 * This runs on the client only — `useState` lazy initialiser guarantees
 * it fires before the first paint so toggling responds on one click.
 */
function readInitialTheme(): Theme {
  if (typeof window === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    /* localStorage may be disabled — fall through */
  }
  return "system";
}

function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme;
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

function applyTheme(resolved: "light" | "dark") {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
}

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(readInitialTheme);
  const [resolved, setResolved] = React.useState<"light" | "dark">(() =>
    resolveTheme(readInitialTheme()),
  );

  // Apply whenever preference changes.
  React.useEffect(() => {
    const next = resolveTheme(theme);
    setResolved(next);
    applyTheme(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  // Follow OS changes while in "system" mode.
  React.useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => {
      const next: "light" | "dark" = mq.matches ? "light" : "dark";
      setResolved(next);
      applyTheme(next);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = React.useCallback((t: Theme) => setThemeState(t), []);

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, resolved, setTheme }),
    [theme, resolved, setTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

/**
 * Top-level client providers. Wraps SWR (shared cache, fetcher, dedupe)
 * and the theme context.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <SWRConfig
        value={{
          fetcher: swrFetcher,
          revalidateOnFocus: false,
          dedupingInterval: 30_000,
          onErrorRetry: (err, _key, _cfg, revalidate, { retryCount }) => {
            if (retryCount >= 3) return;
            setTimeout(() => revalidate({ retryCount }), 1_000 * 2 ** retryCount);
          },
        }}
      >
        {children}
      </SWRConfig>
    </ThemeProvider>
  );
}
