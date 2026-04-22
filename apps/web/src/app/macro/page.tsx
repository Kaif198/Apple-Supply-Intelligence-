"use client";

import * as React from "react";

import { PageShell } from "@/components/layout/PageShell";
import { PageHero } from "@/components/layout/PageHero";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/layout/Reveal";
import { FeatureCard } from "@/components/ui/FeatureCard";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatBlock } from "@/components/ui/StatBlock";
import { Badge } from "@/components/ui/Badge";
import { LineChart } from "@/components/charts/LineChart";
import { Sparkline } from "@/components/charts/Sparkline";
import { ErrorState, LoadingRows } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import {
  runCausalAte,
  useAaplHistory,
  useCommodityPrices,
  useFactors,
} from "@/lib/hooks";
import { fmtDelta, fmtNumber } from "@/lib/format";
import { ImpactChain } from "@/components/ui/ImpactChain";
import type { CausalResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Macro page — factor regression readout + ad-hoc causal ATE estimator.
 */

const TREATMENTS = [
  "aluminum",
  "copper",
  "lithium_carbonate",
  "rare_earth_ndpr",
  "crude_oil_wti",
] as const;

export default function MacroPage() {
  const factors = useFactors();
  const aapl = useAaplHistory(365);
  const commodities = useCommodityPrices(365);
  const [treatment, setTreatment] =
    React.useState<(typeof TREATMENTS)[number]>("copper");
  const [lookback, setLookback] = React.useState(500);
  const [ate, setAte] = React.useState<CausalResponse | null>(null);
  const [ateError, setAteError] = React.useState<unknown>(null);
  const [ateBusy, setAteBusy] = React.useState(false);

  const runAte = React.useCallback(async () => {
    setAteBusy(true);
    setAteError(null);
    try {
      const r = await runCausalAte({ treatment, lookback_days: lookback });
      setAte(r);
    } catch (exc) {
      setAteError(exc);
      setAte(null);
    } finally {
      setAteBusy(false);
    }
  }, [treatment, lookback]);

  React.useEffect(() => {
    void runAte();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const aaplPoints = (aapl.data?.series ?? []).map((p) => ({
    ts: p.as_of_ts,
    value: p.adj_close,
  }));
  const treatmentSeries = commodities.data?.commodities.find(
    (c) => c.entity_id === treatment,
  );
  const treatmentPoints = (treatmentSeries?.series ?? []).map((p) => ({
    ts: p.as_of_ts,
    value: p.price,
  }));

  return (
    <PageShell>
      <PageHero
        eyebrow="Macro & Causal"
        title={
          <>
            Factor regression.{" "}
            <span className="text-accent-muted">Then cause, not just correlation.</span>
          </>
        }
        subtitle="Factor attribution for AAPL returns — then a causal estimate of what a commodity price move actually does to earnings, after stripping out shared macro noise. Correlation is not the answer here."
      />

      <Section spacing="tight">
        <Container width="wide">
          <Reveal>
            <FeatureCard>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex flex-col">
                  <span className="eyebrow">Factor regression · AAPL</span>
                  <h3 className="text-2xl font-semibold md:text-3xl">
                    Exposure, by factor
                  </h3>
                </div>
                {factors.data && (
                  <div className="flex gap-6">
                    <StatBlock
                      label="R²"
                      value={fmtNumber(factors.data.r_squared, 3)}
                      size="sm"
                      helper={<span>n = {factors.data.n_obs}</span>}
                    />
                    <StatBlock
                      label="Adj R²"
                      value={fmtNumber(factors.data.adj_r_squared, 3)}
                      size="sm"
                    />
                  </div>
                )}
              </div>
              {factors.isLoading ? (
                <LoadingRows rows={3} />
              ) : factors.error ? (
                <ErrorState
                  error={factors.error}
                  onRetry={() => factors.mutate()}
                />
              ) : factors.data ? (
                <div className="mt-8 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs uppercase tracking-[0.14em] text-fg-subtle">
                        <th className="py-2 text-left font-medium">Factor</th>
                        <th className="text-right font-medium">Coef</th>
                        <th className="text-right font-medium">SE</th>
                        <th className="text-right font-medium">t</th>
                        <th className="text-right font-medium">p</th>
                      </tr>
                    </thead>
                    <tbody>
                      {factors.data.factors.map((f) => (
                        <tr
                          key={f.name}
                          className="border-t border-border-subtle"
                        >
                          <td className="py-3 font-medium uppercase tracking-wider text-fg-muted">
                            {f.name}
                          </td>
                          <td className="text-right tabular-nums">
                            {fmtNumber(f.coefficient, 4)}
                          </td>
                          <td className="text-right tabular-nums">
                            {fmtNumber(f.std_error, 4)}
                          </td>
                          <td className="text-right tabular-nums">
                            {fmtNumber(f.t_value, 2)}
                          </td>
                          <td
                            className={cn(
                              "text-right tabular-nums",
                              f.p_value < 0.05 && "text-signal-pos",
                              f.p_value >= 0.1 && "text-fg-subtle",
                            )}
                          >
                            {fmtNumber(f.p_value, 3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {factors.data.notes && (
                    <p className="mt-6 text-xs text-fg-subtle">
                      {factors.data.notes}
                    </p>
                  )}
                  <div className="mt-4 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                    R² is the fraction of AAPL daily return variance explained by the factor set. Above 0.35 is typical for well-specified equity factor models; adjusted R² penalises spurious factors.
                  </div>
                </div>
              ) : null}
            </FeatureCard>
          </Reveal>
        </Container>
      </Section>

      <Section spacing="default">
        <Container width="wide">
          <SectionHeader
            eyebrow="Causal"
            title={<>Cause, not just correlation.</>}
            subtitle="Double machine learning — partial-out GBM on confounders, then orthogonal estimator on the residualised treatment effect."
          />
          <div className="mt-10 grid grid-cols-1 gap-3 lg:grid-cols-12">
            <Reveal delay={0} className="lg:col-span-5">
              <FeatureCard className="flex h-full flex-col gap-5">
                <div className="flex items-center justify-between">
                  <span className="eyebrow">Treatment</span>
                  <button
                    type="button"
                    onClick={runAte}
                    disabled={ateBusy}
                    className="pill-primary disabled:opacity-60"
                  >
                    {ateBusy ? "Running…" : "Run"}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {TREATMENTS.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setTreatment(t)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wider transition-colors",
                        treatment === t
                          ? "border-accent bg-accent text-accent-foreground"
                          : "border-border-subtle text-fg-muted hover:text-fg",
                      )}
                    >
                      {t.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
                <label className="flex flex-col gap-2">
                  <span className="flex items-center justify-between text-xs font-medium">
                    <span className="uppercase tracking-[0.14em] text-fg-subtle">
                      Lookback · days
                    </span>
                    <span className="tabular-nums text-fg">{lookback}</span>
                  </span>
                  <input
                    type="range"
                    min={120}
                    max={1825}
                    step={30}
                    value={lookback}
                    onChange={(e) => setLookback(Number(e.target.value))}
                    className="accent-accent"
                  />
                </label>
                {ate ? (
                  <div className="flex flex-col gap-2 rounded-2xl bg-bg-raised/70 p-5 text-sm">
                    <Row label="ATE" value={fmtNumber(ate.ate, 4)} />
                    <Row
                      label="95% CI"
                      value={`[${fmtNumber(ate.ci_low, 4)}, ${fmtNumber(ate.ci_high, 4)}]`}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-fg-muted">Method</span>
                      <Badge variant="accent">{ate.method}</Badge>
                    </div>
                    <div className="text-xs text-fg-subtle">
                      n = {ate.n_obs}
                    </div>
                    <details className="mt-2 cursor-pointer text-xs text-fg-subtle">
                      <summary>Assumptions</summary>
                      <ul className="mt-2 list-inside list-disc space-y-1">
                        {ate.assumptions.map((a) => (
                          <li key={a}>{a}</li>
                        ))}
                      </ul>
                    </details>
                    <div className="mt-2 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                      ATE (average treatment effect) is the causal estimate of how a 1-unit commodity price move changes AAPL's daily return, after partialling out shared macro confounders via double-ML — not simple correlation.
                    </div>
                    {Math.abs(ate.ate) > 0.0001 && (
                      <div className="mt-3 border-t border-border-subtle pt-3">
                        <ImpactChain
                          values={{
                            commodity: treatment,
                            marginDeltaBps: ate.ate * 10_000,
                          }}
                        />
                      </div>
                    )}
                  </div>
                ) : ateError ? (
                  <ErrorState error={ateError} onRetry={() => runAte()} />
                ) : (
                  <LoadingRows rows={3} />
                )}
              </FeatureCard>
            </Reveal>

            <Reveal delay={100} className="lg:col-span-7">
              <ErrorBoundary>
              <FeatureCard className="flex h-full flex-col gap-4">
                <div className="flex flex-col">
                  <span className="eyebrow">Co-movement</span>
                  <h3 className="text-xl font-semibold md:text-2xl">
                    AAPL vs {treatment.toUpperCase().replace(/_/g, " ")}
                  </h3>
                </div>
                {aapl.isLoading || commodities.isLoading ? (
                  <LoadingRows rows={6} />
                ) : (
                  <div className="flex flex-col gap-6">
                    <LineChart
                      series={[
                        {
                          id: "AAPL",
                          points: aaplPoints,
                          strokeClassName: "stroke-accent-muted",
                        },
                      ]}
                      height={170}
                      yLabel="USD"
                    />
                    <LineChart
                      series={[
                        {
                          id: treatment,
                          points: treatmentPoints,
                          strokeClassName: "stroke-signal-warn",
                        },
                      ]}
                      height={150}
                      yLabel={treatment}
                    />
                    <div className="flex flex-wrap items-center gap-3 text-xs text-fg-subtle">
                      <span>quick deltas:</span>
                      {TREATMENTS.map((t) => {
                        const s = commodities.data?.commodities.find(
                          (c) => c.entity_id === t,
                        );
                        const first = s?.series.at(-60)?.price;
                        const last = s?.series.at(-1)?.price;
                        const delta =
                          first && last ? (last - first) / Math.abs(first) : 0;
                        return (
                          <span key={t} className="flex items-center gap-1.5">
                            <span className="uppercase tracking-wider text-fg-muted">
                              {t.replace(/_/g, " ")}
                            </span>
                            <Sparkline
                              values={(s?.series ?? [])
                                .slice(-60)
                                .map((p) => p.price)}
                              width={48}
                              height={16}
                              strokeClassName="stroke-fg-muted"
                            />
                            <span
                              className={
                                delta > 0
                                  ? "text-signal-warn"
                                  : "text-signal-pos"
                              }
                            >
                              {fmtDelta(delta, 2)}
                            </span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </FeatureCard>
              </ErrorBoundary>
            </Reveal>
          </div>
        </Container>
      </Section>
    </PageShell>
  );
}

interface RowProps {
  label: string;
  value: React.ReactNode;
}

function Row({ label, value }: RowProps) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-fg-muted">{label}</span>
      <span className="tabular-nums text-fg">{value}</span>
    </div>
  );
}