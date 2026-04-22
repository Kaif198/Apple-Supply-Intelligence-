import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Max-width content container tuned for apple.com-style layouts.
 *
 * Default width caps at 1200px (Apple's marketing grid); `wide` bumps
 * to 1440px for dashboard-density pages that want more breathing room
 * without going full-bleed.
 */

interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: "default" | "wide" | "narrow";
}

const widthClass: Record<NonNullable<ContainerProps["width"]>, string> = {
  narrow: "max-w-[880px]",
  default: "max-w-[1200px]",
  wide: "max-w-[1440px]",
};

export function Container({
  width = "default",
  className,
  children,
  ...rest
}: ContainerProps) {
  return (
    <div
      className={cn("mx-auto w-full px-5 md:px-8", widthClass[width], className)}
      {...rest}
    >
      {children}
    </div>
  );
}
