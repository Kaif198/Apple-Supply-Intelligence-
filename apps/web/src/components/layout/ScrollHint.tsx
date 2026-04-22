"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function ScrollHint({ className }: { className?: string }) {
  const [hidden, setHidden] = React.useState(false);

  React.useEffect(() => {
    const onScroll = () => {
      if (window.scrollY > 80) setHidden(true);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      aria-hidden
      className={cn(
        "flex flex-col items-center gap-1.5 select-none",
        "transition-opacity duration-500",
        hidden ? "opacity-0 pointer-events-none" : "opacity-100",
        className,
      )}
    >
      <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-fg-subtle">
        Scroll
      </span>
      <span className="flex flex-col items-center gap-0.5">
        {[0, 1, 2].map((i) => (
          <svg
            key={i}
            width="12"
            height="7"
            viewBox="0 0 12 7"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-fg-subtle"
            style={{
              animation: `scrollChevron 1.6s cubic-bezier(0.4,0,0.6,1) ${i * 180}ms infinite`,
            }}
          >
            <path
              d="M1 1l5 5 5-5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ))}
      </span>
      <style>{`
        @keyframes scrollChevron {
          0%, 100% { opacity: 0.2; transform: translateY(-3px); }
          50%       { opacity: 1;   transform: translateY(3px);  }
        }
      `}</style>
    </div>
  );
}
