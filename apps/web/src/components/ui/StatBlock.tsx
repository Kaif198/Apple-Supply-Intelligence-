import * as React from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { fmtDelta } from "@/lib/format";

/**
 * Apple-marketing-style stat readout — giant number, small label.
 *
 * Replaces the dense terminal-era `MetricTile` for hero / overview
 * surfaces. Works at multiple sizes; wrap inside a `FeatureCard` or
 * use bare on full-bleed dark sections.
 */

interface StatBlockProps {
  label: React.ReactNode;
  value: React.ReactNode;
  unit?: React.ReactNode;
  deltaFraction?: number | null;
  deltaLabel?: string;
  helper?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  align?: "left" | "center";
  tone?: "default" | "positive" | "negative" | "warn";
  className?: string;
}

const valueSize: Record<NonNullable<StatBlockProps["size"]>, string> = {
  sm: "text-2xl md:text-3xl",
  md: "text-3xl md:text-4xl",
  lg: "text-4xl md:text-5xl lg:text-6xl",
};

const toneClass: Record<NonNullable<StatBlockProps["tone"]>, string> = {
  default: "text-fg",
  positive: "text-signal-pos",
  negative: "text-signal-neg",
  warn: "text-signal-warn",
};

export function StatBlock({
  label,
  value,
  unit,
  deltaFraction,
  deltaLabel,
  helper,
  size = "md",
  align = "left",
  tone = "default",
  className,
}: StatBlockProps) {
  const [copied, setCopied] = React.useState(false);

  function handleCopy() {
    const text = typeof value === "string" || typeof value === "number" ? String(value) : "";
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }).catch(() => undefined);
  }

  const Trend =
    deltaFraction == null
      ? null
      : deltaFraction > 0
        ? TrendingUp
        : deltaFraction < 0
          ? TrendingDown
          : null;
  const deltaClass =
    deltaFraction == null
      ? "text-fg-subtle"
      : deltaFraction > 0
        ? "text-signal-pos"
        : deltaFraction < 0
          ? "text-signal-neg"
          : "text-fg-subtle";

  return (
    <div
      className={cn(
        "flex flex-col gap-2",
        align === "center" ? "items-center text-center" : "items-start",
        className,
      )}
    >
      <span className="text-xs font-medium uppercase tracking-[0.14em] text-fg-subtle">
        {label}
      </span>
      <div
        className={cn(
          "group flex cursor-pointer items-baseline gap-1.5 font-semibold tracking-tight tabular-nums",
          valueSize[size],
          toneClass[tone],
        )}
        onClick={handleCopy}
        title="Click to copy"
      >
        <span>{copied ? <span className="text-signal-pos text-sm">Copied</span> : value}</span>
        {unit && !copied && <span className="text-base text-fg-muted">{unit}</span>}
      </div>
      <div className="flex items-center gap-3 text-sm">
        {deltaFraction != null && (
          <span
            className={cn(
              "inline-flex items-center gap-1 tabular-nums",
              deltaClass,
            )}
          >
            {Trend && <Trend className="h-3.5 w-3.5" aria-hidden />}
            {fmtDelta(deltaFraction)}
            {deltaLabel && (
              <span className="text-fg-subtle"> · {deltaLabel}</span>
            )}
          </span>
        )}
        {helper && <span className="text-fg-muted">{helper}</span>}
      </div>
    </div>
  );
}
