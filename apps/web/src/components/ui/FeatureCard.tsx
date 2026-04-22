import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Large rounded card used across landing / interior pages.
 *
 * Apple leans on big `rounded-[28px]` tiles with a subtle inner
 * highlight and a soft drop shadow. The card is `relative` so
 * children can place absolute-positioned art.
 */

interface FeatureCardProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: "div" | "article" | "section";
  padded?: boolean;
  tone?: "default" | "inverted" | "accent";
  hover?: boolean;
}

const toneClass: Record<NonNullable<FeatureCardProps["tone"]>, string> = {
  default: "bg-bg-panel/80",
  inverted: "bg-white text-fg-inverted",
  accent:
    "bg-gradient-to-br from-accent/20 via-accent/5 to-transparent border-accent/25",
};

export function FeatureCard({
  as = "div",
  padded = true,
  tone = "default",
  hover = false,
  className,
  children,
  ...rest
}: FeatureCardProps) {
  const Component = as as "div";
  return (
    <Component
      className={cn(
        "relative overflow-hidden rounded-3xl border border-border-subtle backdrop-blur-xl",
        "shadow-elevated",
        toneClass[tone],
        padded && "p-7 md:p-10",
        hover && "card-hover",
        className,
      )}
      {...rest}
    >
      {children}
    </Component>
  );
}
