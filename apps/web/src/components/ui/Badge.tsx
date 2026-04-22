import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Inline severity / classification chip.
 *
 * Apple-style pill: fully rounded, single-weight font, gentle tint
 * backgrounds so several variants can sit side-by-side without
 * fighting for attention.
 */

const badgeVariants = cva(
  "inline-flex h-6 items-center gap-1 rounded-full border px-2.5 text-[11px] font-medium uppercase tracking-[0.1em]",
  {
    variants: {
      variant: {
        neutral:
          "border-border-subtle bg-bg-raised/60 text-fg-muted",
        accent:
          "border-accent/30 bg-accent/10 text-accent-muted",
        low:
          "border-severity-low/30 bg-severity-low/10 text-severity-low",
        medium:
          "border-severity-medium/40 bg-severity-medium/10 text-severity-medium",
        high:
          "border-severity-high/40 bg-severity-high/15 text-severity-high",
        critical:
          "border-severity-critical/50 bg-severity-critical/15 text-severity-critical",
        positive:
          "border-signal-pos/30 bg-signal-pos/10 text-signal-pos",
        negative:
          "border-signal-neg/30 bg-signal-neg/10 text-signal-neg",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "neutral"
    | "accent"
    | "low"
    | "medium"
    | "high"
    | "critical"
    | "positive"
    | "negative";
}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export const severityVariant = (
  severity: "low" | "medium" | "high" | "critical",
): VariantProps<typeof badgeVariants>["variant"] => severity;
