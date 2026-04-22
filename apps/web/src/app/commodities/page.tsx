"use client";

import * as React from "react";

import { PageShell } from "@/components/layout/PageShell";
import { PageHero } from "@/components/layout/PageHero";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/layout/Reveal";
import { FeatureCard } from "@/components/ui/FeatureCard";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Badge } from "@/components/ui/Badge";
import { FreshnessStrip } from "@/components/ui/FreshnessStrip";
import { ImpactChain } from "@/components/ui/ImpactChain";
import { LineChart } from "@/components/charts/LineChart";
import { Sparkline } from "@/components/charts/Sparkline";
import { ErrorState, LoadingRows } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { useCommodityForecast, useCommodityPrices } from "@/lib/hooks";
import { fmtDelta, fmtNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Commodities page — Apple-style: hero → picker → big chart →
 * validation card → 30-day basket grid.
 */

const COMMODITIES = [
  "aluminum",
  "copper",
  "lithium_carbonate",
  "rare_earth_ndpr",
  "crude_oil_wti",
] as const;
type Commodity = (typeof COMMODITIES)[number];

const HORIZONS = [14, 30, 60, 90];

export default function CommoditiesPage() {
  const [entity, setEntity] = React.useState<Commodity>("copper");
  const [horizon, setHorizon] = React.useState(30);
  const prices = useCommodityPrices(365);
  const forecast = useCommodityForecast(entity, horizon);

  const selected = prices.data?.commodities.find((c) => c.entity_id === entity);
  const historyPoints = (selected?.series ?? []).map((p) => ({
    ts: p.as_of_ts,
    value: p.price,
  }));
  const forecastPoints = (forecast.data?.forecast ?? []).map((f) => ({
    ts: f.ts,
    value: f.mean,
  }));
  const forecastBand = (forecast.data?.forecast ?? []).map((f) => ({
    lower: f.lower,
    upper: f.upper,
  }));

  return (
    <PageShell>
      <PageHero
        eyebrow="Commodities"
        title={
          <>
            The basket Apple buys.{" "}
            <span className="text-accent-muted">Forecast.</span>
          </>
        }
        subtitle="Five inputs drive the bulk of Apple's bill of materials cost. Pick one to see where the price is heading — and what that means for gross margin."
      />

      <Section spacing="tight">
        <Container width="wide">
          <Reveal>
            <FeatureCard padded={false} className="p-6 md:p-8">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <span className="eyebrow">Choose a commodity</span>
                <div className="flex items-center gap-1 text-xs text-fg-subtle">
                  <span className="mr-1">Horizon</span>
                  {HORIZONS.map((h) => (
                    <button
                      key={h}
                      type="button"
                      onClick={() => setHorizon(h)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        horizon === h
                          ? "border-accent bg-accent text-accent-foreground"
                          : "border-border-subtle bg-transparent text-fg-muted hover:bg-bg-raised",
                      )}
                    >
                      {h}d
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
                {COMMODITIES.map((c) => {
                  const series = prices.data?.commodities.find(
                    (s) => s.entity_id === c,
                  );
                  const tail = (series?.series ?? [])
                    .slice(-30)
                    .map((p) => p.price);
                  const active = c === entity;
                  return (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setEntity(c)}
                      className={cn(
                        "flex flex-col items-start gap-2 rounded-2xl border p-4 text-left transition-all duration-300",
                        active
                          ? "border-accent bg-accent/10"
                          : "border-border-subtle bg-bg-panel/40 hover:border-border-strong hover:bg-bg-raised",
                      )}
                    >
                      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-fg-subtle">
                        {c.replace(/_/g, " ")}
                      </span>
                      <Sparkline
                        values={tail}
                        height={32}
                        strokeClassName={
                          active ? "stroke-accent-muted" : "stroke-fg-muted"
                        }
                      />
                    </button>
                  );
                })}
              </div>
            </FeatureCard>
          </Reveal>
          {prices.data?.as_of && (
            <FreshnessStrip
              className="mt-3"
              items={[{ label: "Commodity prices", as_of: prices.data.as_of, source: "FRED / DuckDB" }]}
            />
          )}
        </Container>
      </Section>

      <Section spacing="default">
        <Container width="wide">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
            <Reveal delay={60} className="lg:col-span-8">
              <ErrorBoundary>
              <FeatureCard className="h-full">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <span className="eyebrow">{entity.replace(/_/g, " ")}</span>
                    <h3 className="text-2xl font-semibold md:text-3xl">
                      History + ensemble forecast
                    </h3>
                  </div>
                  {forecast.data?.members && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {Object.entries(forecast.data.members).map(
                        ([name, weight]) => (
                          <Badge key={name} variant="accent">
                            {name} · {(weight * 100).toFixed(0)}%
                          </Badge>
                        ),
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-4 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                  The shaded band is the 80% prediction interval. Disagreement between ARIMA, LightGBM, and Prophet widens the band where price dynamics are most uncertain. Weights auto-rebalance to the member with the lowest 60-day hold-out MAE.
                </div>
                <div className="mt-6">
                  {prices.isLoading ? (
                    <LoadingRows rows={8} />
                  ) : prices.error ? (
                    <ErrorState
                      error={prices.error}
                      onRetry={() => prices.mutate()}
                    />
                  ) : (
                    <LineChart
                      height={360}
                      series={[
                        {
                          id: "history",
                          points: historyPoints.slice(-180),
                          strokeClassName: "stroke-fg",
                        },
                        ...(forecastPoints.length
                          ? [
                              {
                                id: "forecast",
                                points: forecastPoints,
                                strokeClassName: "stroke-accent-muted",
                                dashed: true,
                                band: forecastBand,
                                bandClassName: "fill-accent/15",
                              },
                            ]
                          : []),
                      ]}
                      yFormat={(v) => fmtNumber(v, 0)}
                      yLabel="price"
                    />
                  )}
                </div>
                {selected && (
                  <div className="mt-4 border-t border-border-subtle pt-4">
                    <span className="eyebrow mb-2 block">Impact chain</span>
                    <ImpactChain
                      values={{
                        commodity: entity,
                        marginDeltaBps: selected.vol_30d_annualized != null
                          ? -(selected.vol_30d_annualized * 50)
                          : undefined,
                      }}
                    />
                  </div>
                )}
              </FeatureCard>
              </ErrorBoundary>
            </Reveal>

            <Reveal delay={140} className="lg:col-span-4">
              <FeatureCard className="flex h-full flex-col gap-4">
                <span className="eyebrow">Validation MAE</span>
                <h3 className="text-xl font-semibold">Members & weights</h3>
                {forecast.isLoading ? (
                  <LoadingRows rows={4} />
                ) : forecast.data ? (
                  <ul className="flex flex-col gap-2">
                    {Object.entries(forecast.data.val_mae).map(
                      ([member, mae]) => (
                        <li
                          key={member}
                          className="flex items-center justify-between rounded-xl bg-bg-raised/70 px-4 py-3 text-sm"
                        >
                          <span className="font-medium uppercase tracking-wider text-fg-muted">
                            {member}
                          </span>
                          <span className="tabular-nums text-fg">
                            {fmtNumber(mae, 3)}
                          </span>
                        </li>
                      ),
                    )}
                  </ul>
                ) : (
                  <p className="text-sm text-fg-muted">
                    Pick a commodity to run the forecaster.
                  </p>
                )}
                <p className="mt-auto text-xs text-fg-subtle">
                  Weights are inverse-MAE normalised across successful members.
                  Members that fail to fit are excluded and the rest are
                  re-weighted.
                </p>
              </FeatureCard>
            </Reveal>
          </div>
        </Container>
      </Section>

      <Section spacing="default">
        <Container width="wide">
          <SectionHeader
            eyebrow="Basket"
            title="30-day delta across the basket."
            subtitle="A glance at where the costs are moving — green is a tailwind for margin, orange a headwind."
          />
          <Reveal delay={60}>
            <div className="mt-8 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
              Material-to-product mapping: aluminum → chassis &amp; enclosures · copper → PCB traces &amp; cables · lithium carbonate → battery cells · rare earth (NdPr) → MagSafe magnets &amp; Taptic motors · WTI crude → ocean &amp; air freight cost.
            </div>
          </Reveal>
          <Reveal delay={120}>
            <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
              {COMMODITIES.map((c) => {
                const s = prices.data?.commodities.find(
                  (x) => x.entity_id === c,
                );
                const first = s?.series.at(-30)?.price;
                const last = s?.series.at(-1)?.price;
                const delta =
                  first && last ? (last - first) / Math.abs(first) : null;
                return (
                  <FeatureCard
                    key={c}
                    hover
                    className="flex flex-col gap-2"
                    padded={false}
                  >
                    <div className="p-6">
                      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-fg-subtle">
                        {c.replace(/_/g, " ")}
                      </span>
                      <div className="mt-3 text-3xl font-semibold tabular-nums">
                        {last != null ? fmtNumber(last, 0) : "—"}
                      </div>
                      {delta != null && (
                        <div
                          className={cn(
                            "mt-1 text-xs font-medium tabular-nums",
                            delta > 0 ? "text-signal-warn" : "text-signal-pos",
                          )}
                        >
                          {fmtDelta(delta, 2)} · 30d
                        </div>
                      )}
                    </div>
                  </FeatureCard>
                );
              })}
            </div>
          </Reveal>
        </Container>
      </Section>
    </PageShell>
  );
}