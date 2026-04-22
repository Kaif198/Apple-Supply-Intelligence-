import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Loading placeholder with a subtle shimmer.
 *
 * Uses the raised panel colour with rounded-md edges so it sits
 * comfortably inside the new glass cards without feeling boxy.
 */

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse-subtle rounded-md bg-bg-raised/80",
        className,
      )}
      aria-hidden="true"
      {...props}
    />
  );
}
