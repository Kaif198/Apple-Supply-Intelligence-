"use client";

import * as React from "react";

import { PageShell } from "@/components/layout/PageShell";
import { PageHero } from "@/components/layout/PageHero";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/layout/Reveal";
import { FeatureCard } from "@/components/ui/FeatureCard";
import { Badge } from "@/components/ui/Badge";
import { FreshnessStrip } from "@/components/ui/FreshnessStrip";
import { ImpactChain } from "@/components/ui/ImpactChain";
import { ErrorState, LoadingRows, EmptyState } from "@/components/common/States";
import { useEvents } from "@/lib/hooks";
import { fmtCurrencyCompact, fmtDate, fmtRelative } from "@/lib/format";
import type { Severity } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Events page — the disruption stream. Apple-style hero, then a single
 * full-bleed feature card with severity filter pills and a chronological
 * list. Each row shows severity, headline, source, impact, and time.
 */

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

export default function EventsPage() {
  const [severity, setSeverity] = React.useState<Severity | null>(null);
  const events = useEvents(severity ?? undefined, 100);

  return (
    <PageShell>
      <PageHero
        eyebrow="Events"
        title={
          <>
            Every disruption.{" "}
            <span className="text-accent-muted">In one stream.</span>
          </>
        }
        subtitle="Every ingestion source funnels into a single typed log — scored, time-stamped, and cross-referenced against the margin elasticity model so each line carries a bps figure, not just a headline."
      />

      <Section spacing="default">
        <Container width="wide">
          <Reveal>
            <FeatureCard padded={false} className="p-5 md:p-6">
              <div className="flex flex-wrap items-center gap-2">
                <FilterChip
                  active={severity === null}
                  onClick={() => setSeverity(null)}
                  label="All"
                />
                {SEVERITIES.map((s) => (
                  <FilterChip
                    key={s}
                    active={severity === s}
                    onClick={() => setSeverity(s)}
                    label={s}
                  />
                ))}
                <span className="ml-auto text-xs text-fg-subtle">
                  {events.data?.count ?? 0} event
                  {(events.data?.count ?? 0) === 1 ? "" : "s"}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-fg-subtle leading-relaxed">
                  The bps figure is the estimated gross-margin impact if the shock persists for 12 months. Negative bps = margin headwind for Apple.
                </p>
                {events.data?.as_of && (
                  <FreshnessStrip
                    items={[{ label: "Events", as_of: events.data.as_of, source: "Ingestion pipeline" }]}
                  />
                )}
              </div>
            </FeatureCard>
          </Reveal>

          <Reveal delay={120}>
            <FeatureCard className="mt-3" padded={false}>
              <p className="px-7 pt-5 text-xs text-fg-subtle leading-relaxed md:px-10">
                Events are scored by an LLM classifier fine-tuned on supply-chain filings, cross-referenced against the commodity elasticity model. Critical = p ≥ 0.85 that the impact is material.
              </p>
              {events.isLoading ? (
                <div className="p-8">
                  <LoadingRows rows={8} />
                </div>
              ) : events.error ? (
                <div className="p-8">
                  <ErrorState
                    error={events.error}
                    onRetry={() => events.mutate()}
                  />
                </div>
              ) : events.data?.events.length ? (
                <ul className="flex flex-col divide-y divide-border-subtle">
                  {events.data.events.map((e) => (
                    <li
                      key={e.id}
                      className={cn(
                        "grid grid-cols-12 items-start gap-4 px-7 py-5 transition-colors hover:bg-bg-raised/40 md:px-10 md:py-6",
                        e.severity === "critical" &&
                          "bg-severity-critical/5",
                      )}
                    >
                      <div className="col-span-12 flex flex-col gap-2 md:col-span-2">
                        <Badge variant={e.severity}>{e.severity}</Badge>
                        <span className="text-xs text-fg-subtle">
                          {fmtDate(e.as_of_ts)}
                        </span>
                        <span className="text-xs text-fg-subtle">
                          {fmtRelative(e.as_of_ts)}
                        </span>
                      </div>
                      <div className="col-span-12 flex flex-col gap-1.5 md:col-span-7">
                        <span className="text-[15px] font-medium text-fg md:text-base">
                          {e.title}
                        </span>
                        {e.summary && (
                          <span className="text-sm text-fg-muted">
                            {e.summary}
                          </span>
                        )}
                        <span className="text-xs text-fg-subtle">
                          {e.event_type} · {e.source_name}
                          {e.source_url && (
                            <>
                              {" · "}
                              <a
                                href={e.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="underline-offset-2 hover:text-accent-muted hover:underline"
                              >
                                source
                              </a>
                            </>
                          )}
                        </span>
                      </div>
                      <div className="col-span-12 flex flex-col items-end gap-1 md:col-span-3">
                        <span className="text-base font-semibold tabular-nums text-fg">
                          {fmtCurrencyCompact(e.impact_usd)}
                        </span>
                        {e.margin_delta_bps != null && (
                          <span className="text-sm tabular-nums text-signal-neg">
                            {e.margin_delta_bps > 0 ? "+" : ""}
                            {e.margin_delta_bps} bps
                          </span>
                        )}
                        {e.ev_delta_usd != null && (
                          <span className="text-xs text-fg-subtle">
                            EV Δ {fmtCurrencyCompact(e.ev_delta_usd)}
                          </span>
                        )}
                      </div>
                      {e.margin_delta_bps != null && (
                        <div className="col-span-12 pt-1 pb-2">
                          <ImpactChain
                            values={{
                              eventTitle: e.title,
                              marginDeltaBps: e.margin_delta_bps,
                            }}
                          />
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  title="No events"
                  description="No disruption events match the current filter."
                />
              )}
            </FeatureCard>
          </Reveal>
        </Container>
      </Section>
    </PageShell>
  );
}

function FilterChip({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wider transition-colors",
        active
          ? "border-accent bg-accent text-accent-foreground"
          : "border-border-subtle text-fg-muted hover:text-fg",
      )}
    >
      {label}
    </button>
  );
}