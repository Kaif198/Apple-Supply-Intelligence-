import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono } from "next/font/google";

import "@/app/globals.css";
import { Providers } from "@/components/providers/Providers";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
  weight: ["400", "500", "600", "700"],
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: {
    default: "ASCIIP — Apple Supply Chain Intelligence",
    template: "%s · ASCIIP",
  },
  description:
    "Real-time control tower quantifying how external supply chain signals flow through to Apple's operations and valuation.",
  applicationName: "ASCIIP",
  metadataBase: new URL("https://asciip.app"),
  icons: {
    icon: "/favicon.svg",
    apple: "/favicon.svg",
  },
  openGraph: {
    title: "ASCIIP",
    description: "Apple Supply Chain Impact Intelligence Platform",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
  colorScheme: "dark",
};

/**
 * Blocking inline script that sets the theme attribute *before* React
 * hydrates, so the user's saved preference paints on the very first
 * frame. Without this the first click of the theme toggle appears to be
 * a no-op because React state and the DOM are out of sync.
 */
const THEME_INIT_SCRIPT = `
(function(){
  try {
    var s = localStorage.getItem('asciip-theme');
    var t = (s === 'light' || s === 'dark' || s === 'system') ? s : 'system';
    var resolved = t === 'system'
      ? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
      : t;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
  } catch (e) {
    document.documentElement.dataset.theme = 'dark';
  }
})();
`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${jetBrainsMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-dvh bg-bg-canvas font-sans text-fg antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
