"use client";

import * as React from "react";
import Link from "next/link";
import { Activity, ArrowRight } from "lucide-react";

import { PageShell } from "@/components/layout/PageShell";
import { PageHero } from "@/components/layout/PageHero";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/layout/Reveal";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { FeatureCard } from "@/components/ui/FeatureCard";
import { StatBlock } from "@/components/ui/StatBlock";
import { Badge } from "@/components/ui/Badge";
import { Sparkline } from "@/components/charts/Sparkline";
import { LineChart } from "@/components/charts/LineChart";
import { ErrorState, LoadingRows, InlineSpinner } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import {
  useAaplHistory,
  useCommodityPrices,
  useEvents,
  useSignalOfDay,
  useSuppliers,
} from "@/lib/hooks";
import {
  fmtCurrency,
  fmtDelta,
  fmtNumber,
  fmtPercent,
  fmtRelative,
  signalClass,
} from "@/lib/format";
import type { Severity } from "@/lib/api";

/**
 * Landing page — rebuilt as an Apple-style scroll narrative.
 *
 * Hero → live control-tower stats → featured AAPL chart → live event
 * stream → severity summary → product grid → closing CTA. Each section
 * uses `<Reveal>` for staggered fade-in on scroll, and data is read
 * from the existing SWR hooks so the page degrades gracefully.
 */

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

function deltaOverLastN<T>(
  values: T[],
  mapFn: (v: T) => number,
  n = 20,
): number | null {
  if (values.length < 2) return null;
  const arr = values.slice(-n).map(mapFn).filter((v) => Number.isFinite(v));
  if (arr.length < 2) return null;
  return (arr[arr.length - 1]! - arr[0]!) / Math.abs(arr[0]!);
}

const PRODUCT_TILES = [
  {
    href: "/commodities",
    eyebrow: "Commodities",
    title: "Forecast metals and energy before the market does.",
    copy: "Ensemble of ARIMA, LightGBM and Prophet — weighted by inverse validation MAE and re-trained on every new feature-store watermark.",
  },
  {
    href: "/suppliers",
    eyebrow: "Suppliers",
    title: "A distress score for every tier-1 and tier-2.",
    copy: "Calibrated XGBoost classifier surfaces supplier stress with explainable driver features — OTD, on-balance-sheet liquidity, concentration.",
  },
  {
    href: "/valuation",
    eyebrow: "Valuation",
    title: "DCF, sensitivity and 10 000-trial Monte Carlo in under a second.",
    copy: "Move a slider and watch implied price, VaR and CVaR update live. The same model that runs in the API runs in your browser.",
  },
  {
    href: "/network",
    eyebrow: "Network",
    title: "The supply graph, force-simulated.",
    copy: "Apple sits at the centre; every tier-2 inherits the shortest-path risk of its tier-1 hubs. Drag, zoom, inspect.",
  },
];

export default function HomePage() {
  const commodities = useCommodityPrices(180);
  const aapl = useAaplHistory(180);
  const suppliers = useSuppliers();
  const events = useEvents(undefined, 10);
  const signalOfDay = useSignalOfDay();

  const aaplSeries = aapl.data?.series ?? [];
  const aaplLast = aaplSeries.at(-1);
  const aaplDelta = deltaOverLastN(aaplSeries, (p) => p.adj_close, 20);

  const distressCount =
    suppliers.data?.suppliers.filter(
      (s) => (s.distress_score ?? 0) >= 0.5,
    ).length ?? 0;
  const supplierTotal = suppliers.data?.count ?? 0;
  const distressFraction = supplierTotal ? distressCount / supplierTotal : 0;

  const copper = commodities.data?.commodities.find(
    (c) => c.entity_id === "copper",
  );
  const copperDelta = deltaOverLastN(
    copper?.series ?? [],
    (p) => p.price,
    30,
  );

  const severityCounts = SEVERITY_ORDER.map((sev) => ({
    sev,
    count:
      events.data?.events.filter((e) => e.severity === sev).length ?? 0,
  }));

  return (
    <PageShell>
      {/* ---------- hero ---------- */}
      <PageHero
        glow="hero"
        eyebrow="Apple Supply Chain Intelligence"
        title={
          <>
            See the shock.{" "}
            <span className="text-accent-muted">Quantify the impact.</span>
          </>
        }
        subtitle={
          signalOfDay ?? "ASCIIP is a real-time control tower that turns noisy external signals — commodity prices, freight disruption, supplier distress, macro regimes — into a single, auditable view of Apple's operational and financial exposure."
        }
        footer={
          <>
            <Link href="/valuation" className="pill-primary">
              Run a scenario
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
            <Link href="#live" className="pill">
              See it live
            </Link>
          </>
        }
      />

      {/* ---------- live stats strip ---------- */}
      <Section id="live" spacing="tight" className="relative">
        <Container>
          <Reveal>
            <div className="flex items-center justify-between text-xs text-fg-subtle">
              <span className="inline-flex items-center gap-2">
                <span className="relative inline-flex h-2 w-2 items-center justify-center">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-signal-pos/60" />
                  <span className="relative h-2 w-2 rounded-full bg-signal-pos" />
                </span>
                <span className="font-medium uppercase tracking-[0.14em]">
                  Live control tower
                </span>
              </span>
              <span className="font-mono tracking-wider">
                Snapshot · auto-refresh 30s
              </span>
            </div>
          </Reveal>

          <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Reveal delay={60}>
              <FeatureCard hover className="flex h-full flex-col gap-6">
                {aapl.isLoading ? (
                  <LoadingRows rows={3} />
                ) : aapl.error ? (
                  <ErrorState
                    error={aapl.error}
                    onRetry={() => aapl.mutate()}
                  />
                ) : (
                  <>
                    <StatBlock
                      label="AAPL · adj close"
                      value={aaplLast ? fmtCurrency(aaplLast.adj_close) : "—"}
                      deltaFraction={aaplDelta}
                      deltaLabel="20d"
                      size="md"
                    />
                    <Sparkline
                      values={aaplSeries.slice(-60).map((p) => p.adj_close)}
                      height={48}
                      strokeClassName="stroke-accent-muted"
                      fillClassName="text-accent-muted"
                      showLast
                    />
                  </>
                )}
              </FeatureCard>
            </Reveal>

            <Reveal delay={140}>
              <FeatureCard hover className="flex h-full flex-col gap-6">
                {commodities.isLoading ? (
                  <LoadingRows rows={3} />
                ) : commodities.error ? (
                  <ErrorState
                    error={commodities.error}
                    onRetry={() => commodities.mutate()}
                  />
                ) : (
                  <>
                    <StatBlock
                      label="Copper · USD / t"
                      value={
                        copper
                          ? fmtNumber(copper.series.at(-1)?.price ?? 0, 0)
                          : "—"
                      }
                      deltaFraction={copperDelta}
                      deltaLabel="30d"
                      size="md"
                      tone={
                        (copperDelta ?? 0) > 0.05
                          ? "warn"
                          : (copperDelta ?? 0) < -0.05
                            ? "negative"
                            : "default"
                      }
                    />
                    <Sparkline
                      values={(copper?.series ?? []).slice(-60).map((p) => p.price)}
                      height={48}
                      strokeClassName="stroke-signal-warn"
                      showLast
                    />
                  </>
                )}
              </FeatureCard>
            </Reveal>

            <Reveal delay={220}>
              <FeatureCard hover className="flex h-full flex-col gap-6">
                {suppliers.isLoading ? (
                  <LoadingRows rows={3} />
                ) : suppliers.error ? (
                  <ErrorState
                    error={suppliers.error}
                    onRetry={() => suppliers.mutate()}
                  />
                ) : (
                  <>
                    <StatBlock
                      label="Suppliers flagged"
                      value={fmtPercent(distressFraction, 1)}
                      helper={
                        <span>
                          {distressCount} of {supplierTotal} · tier-1 + tier-2
                        </span>
                      }
                      tone={
                        distressFraction > 0.2
                          ? "negative"
                          : distressFraction > 0.1
                            ? "warn"
                            : "positive"
                      }
                      size="md"
                    />
                    <div className="flex items-end gap-1.5">
                      {Array.from({ length: 16 }).map((_, i) => {
                        const h =
                          8 +
                          Math.round(
                            ((suppliers.data?.suppliers.at(i)?.distress_score ??
                              0.25) *
                              28),
                          );
                        return (
                          <span
                            key={i}
                            className="w-1.5 rounded-sm bg-signal-neg/70"
                            style={{ height: `${h}px` }}
                          />
                        );
                      })}
                    </div>
                  </>
                )}
              </FeatureCard>
            </Reveal>

            <Reveal delay={300}>
              <FeatureCard hover className="flex h-full flex-col gap-6">
                <StatBlock
                  label="Active events · 10-row window"
                  value={events.data?.count ?? 0}
                  helper={
                    severityCounts
                      .filter((s) => s.count > 0)
                      .map((s) => `${s.count} ${s.sev}`)
                      .join(" · ") || "—"
                  }
                  size="md"
                />
                <div className="flex flex-wrap gap-1.5">
                  {severityCounts.map(({ sev, count }) => (
                    <Badge
                      key={sev}
                      variant={sev}
                      className="tabular-nums"
                    >
                      {sev} · {count}
                    </Badge>
                  ))}
                </div>
              </FeatureCard>
            </Reveal>
          </div>

          <Reveal delay={380}>
            <div className="mt-5 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
              These four signals form the real-time aperture of Apple's margin exposure — equity performance, input cost pressure, supplier fragility, and event velocity. A simultaneous deterioration across all four is the leading pattern for a guidance revision.
            </div>
          </Reveal>
        </Container>
      </Section>

      {/* ---------- featured chart ---------- */}
      <Section spacing="default" className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 hero-glow-soft"
        />
        <Container>
          <SectionHeader
            eyebrow="Live"
            title={<>AAPL, 180 days. Every tick signal-matched.</>}
            subtitle="The headline equity series, overlaid with the feature store's watermark so you always know how fresh the number on the screen really is."
          />
          <Reveal delay={160}>
            <ErrorBoundary>
            <FeatureCard className="mt-10 p-4 md:p-8">
              <div className="flex items-center justify-between gap-4 pb-6">
                <div className="flex flex-col">
                  <span className="text-xs uppercase tracking-[0.14em] text-fg-subtle">
                    AAPL · adj close
                  </span>
                  <span className="text-xl font-semibold tabular-nums md:text-2xl">
                    {aaplLast ? fmtCurrency(aaplLast.adj_close) : "—"}{" "}
                    {aaplDelta != null && (
                      <span
                        className={
                          "ml-2 text-base " + signalClass(aaplDelta)
                        }
                      >
                        {fmtDelta(aaplDelta)} · 20d
                      </span>
                    )}
                  </span>
                </div>
                {aapl.isValidating ? <InlineSpinner label="syncing" /> : null}
              </div>
              {aapl.isLoading || aaplSeries.length === 0 ? (
                <LoadingRows rows={6} />
              ) : (
                <LineChart
                  series={[
                    {
                      id: "AAPL",
                      points: aaplSeries.map((p) => ({
                        ts: p.as_of_ts,
                        value: p.adj_close,
                      })),
                      strokeClassName: "stroke-accent-muted",
                    },
                  ]}
                  height={360}
                  yLabel="USD"
                  yFormat={(v) => fmtCurrency(v, 0)}
                />
              )}
            </FeatureCard>
            </ErrorBoundary>
          </Reveal>
        </Container>
      </Section>

      {/* ---------- event stream + severity summary ---------- */}
      <Section spacing="default">
        <Container>
          <SectionHeader
            eyebrow="Signals"
            title="The disruption stream, in one place."
            subtitle="Every ingestion layer funnels into a single event log — typed, scored, and cross-referenced against the margin elasticity model so every line carries a bps number, not a headline."
          />
          <div className="mt-10 grid grid-cols-1 gap-3 lg:grid-cols-3">
            <Reveal delay={60} className="lg:col-span-2">
              <FeatureCard>
                <div className="mb-5 flex items-center justify-between">
                  <span className="eyebrow">Latest 6</span>
                  <Activity
                    className="h-4 w-4 animate-pulse-subtle text-accent-muted"
                    aria-hidden
                  />
                </div>
                {events.isLoading ? (
                  <LoadingRows rows={5} />
                ) : events.error ? (
                  <ErrorState
                    error={events.error}
                    onRetry={() => events.mutate()}
                  />
                ) : events.data?.events.length ? (
                  <ul className="flex flex-col divide-y divide-border-subtle">
                    {events.data.events.slice(0, 6).map((evt) => (
                      <li
                        key={evt.id}
                        className="flex flex-col gap-2 py-4 first:pt-0 last:pb-0"
                      >
                        <div className="flex items-center gap-2">
                          <Badge variant={evt.severity}>{evt.severity}</Badge>
                          <span className="truncate text-[15px] font-medium text-fg">
                            {evt.title}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-fg-subtle">
                          <span>{evt.source_name}</span>
                          <span className="tabular-nums">
                            {evt.margin_delta_bps != null ? (
                              <span
                                className={signalClass(-evt.margin_delta_bps)}
                              >
                                {fmtDelta(
                                  -evt.margin_delta_bps / 10_000,
                                  2,
                                )}
                              </span>
                            ) : (
                              <span>—</span>
                            )}
                            {"  ·  "}
                            {fmtRelative(evt.as_of_ts)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-fg-muted">
                    No disruption events in the last window.
                  </p>
                )}
                <p className="mt-4 text-xs text-fg-subtle leading-relaxed">
                  Each bps figure is the gross-margin impact if the shock persists for 12 months at current commodity prices and Apple's hedging ratios. Negative bps = margin headwind.
                </p>
                <div className="mt-6 flex justify-end">
                  <Link
                    href="/events"
                    className="inline-flex items-center gap-1 text-sm text-accent-muted transition-colors hover:text-accent"
                  >
                    Open full event log
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                </div>
              </FeatureCard>
            </Reveal>
            <Reveal delay={160}>
              <FeatureCard className="flex h-full flex-col gap-6">
                <div className="flex flex-col gap-1">
                  <span className="eyebrow">Severity mix</span>
                  <h3 className="text-xl font-semibold">
                    How bad is right now?
                  </h3>
                </div>
                <ul className="flex flex-col gap-3">
                  {severityCounts.map(({ sev, count }) => {
                    const total = severityCounts.reduce(
                      (a, b) => a + b.count,
                      0,
                    );
                    const pct = total ? count / total : 0;
                    return (
                      <li key={sev} className="flex flex-col gap-1.5">
                        <div className="flex items-center justify-between text-sm">
                          <Badge variant={sev}>{sev}</Badge>
                          <span className="tabular-nums text-fg-muted">
                            {count}
                          </span>
                        </div>
                        <div className="h-1 w-full overflow-hidden rounded-full bg-bg-raised">
                          <span
                            className={
                              "block h-full rounded-full " +
                              (sev === "critical"
                                ? "bg-severity-critical"
                                : sev === "high"
                                  ? "bg-severity-high"
                                  : sev === "medium"
                                    ? "bg-severity-medium"
                                    : "bg-severity-low")
                            }
                            style={{
                              width: `${Math.max(4, pct * 100)}%`,
                              transition:
                                "width 700ms cubic-bezier(0.22,1,0.36,1)",
                            }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
                <Link
                  href="/events"
                  className="mt-auto inline-flex items-center gap-1 text-sm text-accent-muted transition-colors hover:text-accent"
                >
                  Review all events
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              </FeatureCard>
            </Reveal>
          </div>
        </Container>
      </Section>

      {/* ---------- product grid ---------- */}
      <Section spacing="default">
        <Container>
          <SectionHeader
            eyebrow="What's inside"
            title="Four surfaces. One story."
            subtitle="Every page below reads from the same point-in-time feature store, so the number you see in the commodities forecast is the exact same number feeding the DCF and the causal ATE."
          />
          <div className="mt-12 grid grid-cols-1 gap-3 md:grid-cols-2">
            {PRODUCT_TILES.map((tile, i) => (
              <Reveal key={tile.href} delay={60 + i * 80}>
                <Link
                  href={tile.href}
                  className="group block h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-3xl"
                >
                  <FeatureCard hover className="h-full">
                    <span className="eyebrow">{tile.eyebrow}</span>
                    <h3 className="mt-3 text-xl font-semibold leading-snug md:text-2xl">
                      {tile.title}
                    </h3>
                    <p className="mt-3 max-w-xl text-[15px] text-fg-muted">
                      {tile.copy}
                    </p>
                    <span className="mt-6 inline-flex items-center gap-1 text-sm text-accent-muted transition-transform duration-500 group-hover:translate-x-1">
                      Explore
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                    </span>
                  </FeatureCard>
                </Link>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      {/* ---------- closing CTA ---------- */}
      <Section spacing="loose">
        <Container width="narrow">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-border-subtle bg-gradient-to-br from-accent/15 via-bg-panel/60 to-bg-panel p-10 text-center md:p-16">
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 hero-glow-soft"
              />
              <span className="eyebrow">Get started</span>
              <h2 className="mt-4 text-gradient text-3xl font-semibold md:text-5xl">
                Move a slider. Watch the whole model react.
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-md text-fg-muted md:text-lg">
                Open the valuation page, drag a single assumption, and watch
                the DCF, sensitivity grid, and Monte Carlo distribution move in
                lockstep — the same calc that runs in the API, rendered live in
                your browser.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link href="/valuation" className="pill-primary">
                  Open valuation
                </Link>
                <Link href="/network" className="pill-secondary">
                  Explore the network
                </Link>
              </div>
            </div>
          </Reveal>
        </Container>
      </Section>
    </PageShell>
  );
}