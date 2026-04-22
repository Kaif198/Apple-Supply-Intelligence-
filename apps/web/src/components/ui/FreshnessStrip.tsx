"use client";

import * as React from "react";
import { fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

interface FreshnessItem {
  label: string;
  as_of: string | Date | null | undefined;
  source?: string;
}

interface FreshnessStripProps {
  items: FreshnessItem[];
  className?: string;
}

export function FreshnessStrip({ items, className }: FreshnessStripProps) {
  const valid = items.filter((i) => i.as_of);
  if (!valid.length) return null;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-fg-subtle",
        className,
      )}
    >
      {valid.map((item, idx) => (
        <span key={idx} className="flex items-center gap-1">
          <span className="font-medium text-fg-subtle">{item.label}</span>
          <span className="text-border-strong">·</span>
          <span>{fmtRelative(item.as_of!)}</span>
          {item.source && (
            <>
              <span className="text-border-strong">·</span>
              <span className="font-mono uppercase tracking-wider">{item.source}</span>
            </>
          )}
        </span>
      ))}
    </div>
  );
}
