"use client";

import * as React from "react";
import { Reveal } from "@/components/layout/Reveal";
import { ScrollHint } from "@/components/layout/ScrollHint";
import { Container } from "@/components/layout/Container";
import { cn } from "@/lib/utils";

/**
 * Apple-style page hero — eyebrow, oversized headline, sub-copy.
 *
 * A radial glow behind the headline gives the accent blue a soft
 * "product halo". Consumers can drop any React node into `footer` to
 * add CTAs or live stats beneath the copy.
 */

interface PageHeroProps {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  footer?: React.ReactNode;
  align?: "center" | "left";
  className?: string;
  /** Size of the glow. `subtle` for inner pages, `hero` for landing. */
  glow?: "none" | "subtle" | "hero";
}

export function PageHero({
  eyebrow,
  title,
  subtitle,
  footer,
  align = "center",
  glow = "subtle",
  className,
}: PageHeroProps) {
  return (
    <section
      className={cn(
        "relative overflow-hidden",
        glow !== "none" && "grain",
        className,
      )}
    >
      {glow !== "none" && (
        <div
          aria-hidden
          className={cn(
            "pointer-events-none absolute inset-x-0 top-0 -z-10 h-[80%]",
            glow === "hero" ? "hero-glow" : "hero-glow-soft",
          )}
        />
      )}

      <Container
        className={cn(
          "relative flex flex-col gap-6 pt-24 pb-16 md:pt-32 md:pb-24",
          align === "center" ? "items-center text-center" : "items-start",
        )}
      >
        {eyebrow && (
          <Reveal delay={0}>
            <span className="eyebrow">{eyebrow}</span>
          </Reveal>
        )}
        <Reveal delay={80}>
          <h1
            className={cn(
              "text-gradient h-display font-semibold",
              "text-4xl sm:text-5xl md:text-6xl lg:text-7xl",
              align === "center" ? "max-w-4xl" : "max-w-5xl",
            )}
          >
            {title}
          </h1>
        </Reveal>
        {subtitle && (
          <Reveal delay={180}>
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
        {footer && (
          <Reveal delay={280}>
            <div
              className={cn(
                "mt-2 flex flex-wrap items-center gap-3",
                align === "center" ? "justify-center" : "",
              )}
            >
              {footer}
            </div>
          </Reveal>
        )}
        <Reveal delay={400}>
          <ScrollHint className="mt-4" />
        </Reveal>
      </Container>
    </section>
  );
}