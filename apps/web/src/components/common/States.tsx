"use client";

import * as React from "react";
import { AlertOctagon, Loader2, PackageOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiError } from "@/lib/api";

/**
 * Loading / error / empty helpers — every page wraps SWR queries in
 * one of these. Styled to sit inside the new FeatureCard surfaces:
 * pill-rounded skeletons, soft tinted error tray, dashed-edge empty.
 */

export function LoadingRows({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-2.5", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-7 w-full"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}

export function InlineSpinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      className="inline-flex items-center gap-2 text-xs text-fg-muted"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const detail =
    error instanceof ApiError
      ? error.problem.detail ?? error.problem.title
      : error instanceof Error
        ? error.message
        : "Unknown error";
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-2xl border border-signal-neg/30 bg-signal-neg/5 p-4 text-sm text-fg",
        className,
      )}
    >
      <AlertOctagon
        className="mt-0.5 h-4 w-4 shrink-0 text-signal-neg"
        aria-hidden
      />
      <div className="flex-1">
        <div className="font-medium text-signal-neg">Request failed</div>
        <div className="mt-1 text-xs text-fg-muted">{detail}</div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full border border-border-strong px-3 py-1 text-[11px] font-medium uppercase tracking-[0.1em] text-fg-muted transition-colors hover:border-accent hover:text-fg"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title = "No data",
  description,
  className,
}: {
  title?: string;
  description?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border-subtle bg-bg-raised/30 p-10 text-center",
        className,
      )}
    >
      <PackageOpen className="h-7 w-7 text-fg-subtle" aria-hidden />
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-fg-muted">
        {title}
      </div>
      {description && <p className="max-w-sm text-xs text-fg-subtle">{description}</p>}
    </div>
  );
}
