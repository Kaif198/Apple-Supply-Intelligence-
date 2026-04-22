"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import { useTheme } from "@/components/providers/Providers";

/**
 * Frosted-glass global navigation — Apple.com style.
 *
 * Sticky at the top, uses `backdrop-filter: blur` to float over the
 * content beneath. A thin accent indicator underlines the active
 * section; the right side surfaces a live system-health dot so the
 * dashboard's "freshness" is always one glance away.
 */

interface NavEntry {
  href: string;
  label: string;
}

const NAV: NavEntry[] = [
  { href: "/", label: "Overview" },
  { href: "/commodities", label: "Commodities" },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/network", label: "Network" },
  { href: "/events", label: "Events" },
  { href: "/valuation", label: "Valuation" },
  { href: "/macro", label: "Macro" },
  { href: "/simulate", label: "Simulate" },
];

type Theme = "system" | "light" | "dark";
const THEME_CYCLE: Theme[] = ["system", "light", "dark"];

function ThemeIcon({ theme }: { theme: Theme }) {
  if (theme === "light") {
    return (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 fill-current" aria-hidden>
        <circle cx="8" cy="8" r="3" />
        <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.22 3.22l1.42 1.42M11.36 11.36l1.42 1.42M11.36 4.64l-1.42 1.42M4.64 11.36l-1.42 1.42" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" />
      </svg>
    );
  }
  if (theme === "dark") {
    return (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 fill-current" aria-hidden>
        <path d="M13.5 10.5A6 6 0 0 1 5.5 2.5a6 6 0 1 0 8 8z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 fill-none stroke-current" strokeWidth="1.5" strokeLinecap="round" aria-hidden>
      <rect x="1" y="3" width="14" height="9" rx="1.5" />
      <path d="M5 14h6M8 12v2" />
    </svg>
  );
}

export function TopNav() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => { setMounted(true); }, []);

  function cycleTheme() {
    const idx = THEME_CYCLE.indexOf(theme);
    setTheme(THEME_CYCLE[(idx + 1) % THEME_CYCLE.length] ?? "system");
  }
  return (
    <header className="glass-nav sticky top-0 z-50 w-full">
      <div className="mx-auto flex h-12 max-w-[1200px] items-center gap-6 px-5 text-sm">
        {/* Brand mark */}
        <Link
          href="/"
          className="group flex items-center gap-2 font-semibold tracking-tight text-fg transition-opacity hover:opacity-80"
          aria-label="Apple Inc — Supply Chain Intelligence"
        >
          <svg
            aria-hidden
            viewBox="0 0 814 1000"
            className="h-5 w-5 fill-current text-fg"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M788.1 340.9c-5.8 4.5-108.2 62.2-108.2 190.5 0 148.4 130.3 200.9 134.2 202.2-.6 3.2-20.7 71.9-68.7 141.9-42.8 61.6-87.5 123.1-155.5 123.1s-85.5-39.5-164-39.5c-76 0-103.7 40.8-165.9 40.8s-105-57.8-155.5-127.4C46 790.7 0 663 0 541.8c0-207.5 135.4-317.3 269-317.3 71 0 130.1 46.4 174.5 46.4 42.7 0 109.5-49.1 189.2-49.1 30.8 0 130.3 2.6 198.3 99.2zm-234-181.5c31.1-36.9 53.1-88.1 53.1-139.3 0-7.1-.6-14.3-1.9-20.1-50.6 1.9-110.8 33.7-147.1 75.8-28.5 32.4-55.1 83.6-55.1 135.5 0 7.8 1.3 15.6 1.9 18.1 3.2.6 8.4 1.3 13.6 1.3 45.4 0 102.5-30.4 135.5-71.3z" />
          </svg>
          <span className="text-[13px] font-medium tracking-wide">Apple Inc</span>
        </Link>

        {/* Primary nav */}
        <nav className="hidden flex-1 items-center justify-center gap-1 md:flex">
          {NAV.map((entry) => {
            const isActive =
              entry.href === "/"
                ? pathname === "/"
                : pathname.startsWith(entry.href);
            return (
              <Link
                key={entry.href}
                href={entry.href}
                className={cn(
                  "relative rounded-full px-3 py-1 text-[13px] font-normal transition-colors duration-300",
                  "text-fg-muted hover:text-fg",
                  isActive && "text-fg",
                )}
              >
                {entry.label}
                {isActive && (
                  <span
                    aria-hidden
                    className="absolute left-3 right-3 -bottom-[11px] h-[2px] rounded-full bg-accent"
                  />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right cluster */}
        <div className="ml-auto flex items-center gap-3">
          <button
            type="button"
            aria-label="Toggle theme"
            onClick={cycleTheme}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full text-fg-muted transition-colors hover:bg-bg-raised hover:text-fg"
            suppressHydrationWarning
          >
            {mounted ? <ThemeIcon theme={theme} /> : <ThemeIcon theme="system" />}
          </button>
          <button
            type="button"
            aria-label="Search"
            className="hidden h-7 w-7 items-center justify-center rounded-full text-fg-muted transition-colors hover:bg-bg-raised hover:text-fg md:inline-flex"
          >
            <Search className="h-3.5 w-3.5" aria-hidden />
          </button>
          <span className="hidden font-mono text-[10px] tracking-widest text-fg-subtle sm:inline">
            Designed by Kaif Ahmed
          </span>
        </div>
      </div>
    </header>
  );
}