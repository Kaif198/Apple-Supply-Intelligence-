"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Scroll-triggered reveal — the Apple.com signature effect.
 *
 * Uses a single `IntersectionObserver` to fade + lift children into
 * view the first time they cross the viewport. Honors
 * `prefers-reduced-motion`: when the user has motion disabled the
 * child renders at its final state immediately.
 *
 * Stagger children inside a single `<Reveal>` by nesting more
 * `<Reveal delay={n * 80}>` siblings.
 */

interface RevealProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Milliseconds to wait before starting the animation. */
  delay?: number;
  /** How far (px) the child lifts from on its way in. */
  distance?: number;
  /** Animation duration in ms. */
  duration?: number;
  /** Only fire the animation once (default true). */
  once?: boolean;
  /** Render as a semantic element other than `<div>`. */
  as?: "div" | "section" | "article" | "li" | "span";
}

export function Reveal({
  delay = 0,
  distance = 24,
  duration = 820,
  once = true,
  as = "div",
  className,
  style,
  children,
  ...rest
}: RevealProps) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setVisible(true);
      return;
    }

    // Support older Safari versions lacking IntersectionObserver.
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            if (once) observer.unobserve(entry.target);
          } else if (!once) {
            setVisible(false);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [once]);

  const Component = as as "div";
  return (
    <Component
      ref={ref as React.Ref<HTMLDivElement>}
      className={cn("will-change-transform", className)}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : `translateY(${distance}px)`,
        transition: `opacity ${duration}ms cubic-bezier(0.22,1,0.36,1) ${delay}ms, transform ${duration}ms cubic-bezier(0.22,1,0.36,1) ${delay}ms`,
        ...style,
      }}
      {...rest}
    >
      {children}
    </Component>
  );
}
