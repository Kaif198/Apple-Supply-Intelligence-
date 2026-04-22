import * as React from "react";
import { Reveal } from "@/components/layout/Reveal";
import { cn } from "@/lib/utils";

/**
 * Centered eyebrow + headline + sub-copy used above each page section.
 *
 * Mirrors Apple's marketing anatomy: small color accent, a 38–56px
 * headline, and a 17–20px sub-line that sets up the content below.
 */

interface SectionHeaderProps {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  align?: "center" | "left";
  className?: string;
  size?: "md" | "lg";
}

export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  align = "center",
  size = "md",
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4",
        align === "center" ? "items-center text-center" : "items-start",
        className,
      )}
    >
      {eyebrow && (
        <Reveal>
          <span className="eyebrow">{eyebrow}</span>
        </Reveal>
      )}
      <Reveal delay={80}>
        <h2
          className={cn(
            "text-gradient h-headline font-semibold",
            size === "lg"
              ? "text-3xl md:text-4xl lg:text-5xl"
              : "text-2xl md:text-3xl lg:text-4xl",
            align === "center" ? "max-w-3xl" : "max-w-4xl",
          )}
        >
          {title}
        </h2>
      </Reveal>
      {subtitle && (
        <Reveal delay={160}>
          <p
            className={cn(
              "max-w-2xl text-md text-fg-muted md:text-lg",
              align === "center" ? "mx-auto" : "",
            )}
          >
            {subtitle}
          </p>
        </Reveal>
      )}
    </div>
  );
}
