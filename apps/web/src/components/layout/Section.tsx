import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Vertical rhythm wrapper. Apple's marketing pages use generous
 * section spacing (96–160px top/bottom) to let each idea breathe;
 * this primitive enforces that with a `tight` / `default` / `loose`
 * knob so we rarely need bespoke padding utilities in page code.
 */

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  spacing?: "tight" | "default" | "loose";
  as?: "section" | "div" | "article";
}

const spacingClass: Record<NonNullable<SectionProps["spacing"]>, string> = {
  tight: "py-14 md:py-20",
  default: "py-20 md:py-28",
  loose: "py-24 md:py-36",
};

export function Section({
  spacing = "default",
  as = "section",
  className,
  children,
  ...rest
}: SectionProps) {
  const Component = as as "section";
  return (
    <Component className={cn(spacingClass[spacing], className)} {...rest}>
      {children}
    </Component>
  );
}
