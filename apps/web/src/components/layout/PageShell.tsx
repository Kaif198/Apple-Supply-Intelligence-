import * as React from "react";
import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { cn } from "@/lib/utils";

/**
 * Top-level page frame: frosted nav → main → footer.
 *
 * Replaces the old sidebar-based AppShell. Every marketing-style page
 * gets the same chrome so navigation is consistent and the content can
 * go full-bleed when it wants to.
 */

interface PageShellProps {
  children: React.ReactNode;
  className?: string;
  /** Set to false on pages that provide their own footer. */
  withFooter?: boolean;
}

export function PageShell({
  children,
  className,
  withFooter = true,
}: PageShellProps) {
  return (
    <div className="relative flex min-h-dvh flex-col bg-bg-canvas text-fg">
      <TopNav />
      <main className={cn("flex-1", className)}>{children}</main>
      {withFooter && <Footer />}
    </div>
  );
}
