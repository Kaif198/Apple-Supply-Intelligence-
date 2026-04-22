import * as React from "react";
import Link from "next/link";

/**
 * Minimal Apple-style footer.
 *
 * Thin legal line, a grid of disclosure links, and a courtesy note that
 * ASCIIP is not affiliated with Apple Inc. — this is a research /
 * portfolio project using only public data.
 */

const COLUMNS: { heading: string; items: { label: string; href: string }[] }[] = [
  {
    heading: "Platform",
    items: [
      { label: "Overview", href: "/" },
      { label: "Commodities", href: "/commodities" },
      { label: "Suppliers", href: "/suppliers" },
      { label: "Network", href: "/network" },
    ],
  },
  {
    heading: "Intelligence",
    items: [
      { label: "Events", href: "/events" },
      { label: "Valuation", href: "/valuation" },
      { label: "Macro & Causal", href: "/macro" },
      { label: "Simulate", href: "/simulate" },
    ],
  },
  {
    heading: "Build",
    items: [
      { label: "Architecture", href: "/" },
      { label: "Data sources", href: "/" },
      { label: "Model cards", href: "/" },
      { label: "Changelog", href: "/" },
    ],
  },
  {
    heading: "Legal",
    items: [
      { label: "Disclaimer", href: "/" },
      { label: "Privacy", href: "/" },
      { label: "Terms", href: "/" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="mt-30 border-t border-border-subtle bg-bg-inset/40">
      <div className="mx-auto max-w-[1200px] px-5 py-14">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-4">
          {COLUMNS.map((col) => (
            <div key={col.heading} className="flex flex-col gap-2.5">
              <h4 className="text-xs font-medium uppercase tracking-[0.14em] text-fg-subtle">
                {col.heading}
              </h4>
              <ul className="flex flex-col gap-1.5">
                {col.items.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="text-[13px] text-fg-muted transition-colors hover:text-fg"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="hairline mt-12" />

        <div className="mt-6 flex flex-col gap-3 text-xs text-fg-subtle md:flex-row md:items-center md:justify-between">
          <p className="max-w-2xl leading-relaxed">
            ASCIIP is an independent research platform built on free, public
            data sources. Not affiliated with, endorsed by, or sponsored by
            Apple Inc. All trademarks belong to their respective owners.
          </p>
          <div className="flex flex-col items-end gap-1">
            <p className="font-mono tracking-wider">
              © {new Date().getFullYear()} ASCIIP · Built with restraint.
            </p>
            <p className="text-xs text-fg-subtle tracking-wide">
              Designed by Kaif Ahmed
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}