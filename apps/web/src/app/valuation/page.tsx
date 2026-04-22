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
import { Heatmap } from "@/components/charts/Heatmap";
import { Histogram } from "@/components/charts/Histogram";
import { LoadingRows, ErrorState } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { runDcf, runMonteCarlo, runSensitivity } from "@/lib/hooks";
import { fmtCurrency, fmtNumber, fmtPercent } from "@/lib/format";
import type {
  DcfResponse,
  MonteCarloResponse,
  SensitivityResponse,
} from "@/lib/types";

/**
 * Valuation page — DCF base case, 2-way sensitivity, Monte Carlo.
 * Apple-themed: hero, assumption panel, headline stat, then sensitivity
 * and distribution side-by-side.
 */

interface Assumptions {
  revenue_cagr_5y: number;
  fcf_margin: number;
  wacc: number;
  terminal_growth: number;
}

const DEFAULTS: Assumptions = {
  revenue_cagr_5y: 0.07,
  fcf_margin: 0.27,
  wacc: 0.081,
  terminal_growth: 0.029,
};

const DEFAULT_SHOCKS = [
  {
    name: "aluminum",
    mean_return: 0.02,
    volatility: 0.18,
    elasticity_bps_per_10pct: 8,
  },
  {
    name: "copper",
    mean_return: 0.02,
    volatility: 0.22,
    elasticity_bps_per_10pct: 9,
  },
  {
    name: "lithium",
    mean_return: 0.0,
    volatility: 0.45,
    elasticity_bps_per_10pct: 4,
  },
  {
    name: "cobalt",
    mean_return: -0.01,
    volatility: 0.35,
    elasticity_bps_per_10pct: 3,
  },
  {
    name: "brent",
    mean_return: 0.01,
    volatility: 0.28,
    elasticity_bps_per_10pct: 5,
  },
];

const LABELS: Record<keyof Assumptions, string> = {
  revenue_cagr_5y: "Revenue CAGR · 5Y",
  fcf_margin: "FCF margin",
  wacc: "WACC",
  terminal_growth: "Terminal growth",
};

export default function ValuationPage() {
  const [assumptions, setAssumptions] = React.useState<Assumptions>(DEFAULTS);
  const [dcf, setDcf] = React.useState<DcfResponse | null>(null);
  const [sens, setSens] = React.useState<SensitivityResponse | null>(null);
  const [mc, setMc] = React.useState<MonteCarloResponse | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<unknown>(null);

  const compute = React.useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [dcfR, sensR, mcR] = await Promise.all([
        runDcf(assumptions),
        runSensitivity({
          row_field: "wacc",
          row_values: [0.07, 0.075, 0.08, assumptions.wacc, 0.09, 0.095, 0.1],
          col_field: "terminal_growth",
          col_values: [0.02, 0.025, assumptions.terminal_growth, 0.032, 0.035],
        }),
        runMonteCarlo({
          n_trials: 10_000,
          horizon_years: 1.0,
          shocks: DEFAULT_SHOCKS,
          supplier_stress_mean: 0.15,
          supplier_stress_sd: 0.05,
          outage_revenue_haircut_mean: 0.03,
          outage_revenue_haircut_sd: 0.01,
          seed: 20250101,
        }),
      ]);
      setDcf(dcfR);
      setSens(sensR);
      setMc(mcR);
    } catch (exc) {
      setError(exc);
    } finally {
      setBusy(false);
    }
  }, [assumptions]);

  React.useEffect(() => {
    void compute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setField =
    (k: keyof Assumptions) => (e: React.ChangeEvent<HTMLInputElement>) =>
      setAssumptions((prev) => ({ ...prev, [k]: Number(e.target.value) }));

  return (
    <PageShell>
      <PageHero
        eyebrow="Valuation"
        title={
          <>
            Move a slider.{" "}
            <span className="text-accent-muted">See the whole model react.</span>
          </>
        }
        subtitle="Procurement-adjusted valuation — input-cost shocks and supplier distress propagated through Apple's cash flows, with confidence bands from 10,000 simulation paths. Move a slider and watch the model react."
        footer={
          <button
            type="button"
            onClick={() => compute()}
            disabled={busy}
            className="pill-primary disabled:opacity-60"
          >
            {busy ? "Running…" : "Recompute"}
          </button>
        }
      />

      <Section spacing="tight">
        <Container width="wide">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <Reveal delay={0}>
              <FeatureCard className="flex h-full flex-col gap-5">
                <div>
                  <span className="eyebrow">Assumptions</span>
                  <h3 className="mt-1 text-xl font-semibold">
                    Tune the base case
                  </h3>
                </div>
                <div className="flex flex-col gap-5">
                  {(Object.keys(DEFAULTS) as (keyof Assumptions)[]).map((k) => (
                    <label key={k} className="flex flex-col gap-2">
                      <span className="flex items-center justify-between text-xs font-medium">
                        <span className="uppercase tracking-[0.14em] text-fg-subtle">
                          {LABELS[k]}
                        </span>
                        <span className="tabular-nums text-fg">
                          {fmtPercent(assumptions[k], 2)}
                        </span>
                      </span>
                      <input
                        type="range"
                        min={k === "terminal_growth" ? 0.01 : 0.02}
                        max={
                          k === "wacc"
                            ? 0.14
                            : k === "revenue_cagr_5y"
                              ? 0.15
                              : 0.4
                        }
                        step={0.001}
                        value={assumptions[k]}
                        onChange={setField(k)}
                        className="accent-accent"
                      />
                    </label>
                  ))}
                </div>
              </FeatureCard>
            </Reveal>

            <Reveal delay={80}>
              <FeatureCard className="flex h-full flex-col gap-5">
                <span className="eyebrow">DCF · implied price</span>
                {dcf ? (
                  <>
                    <StatBlock
                      label="Base case"
                      value={fmtCurrency(dcf.implied_price_usd, 2)}
                      size="lg"
                      helper={
                        <span>
                          EV {fmtCurrency(dcf.enterprise_value_bn, 0)}B ·
                          Equity {fmtCurrency(dcf.equity_value_bn, 0)}B
                        </span>
                      }
                    />
                    <p className="text-sm text-fg-muted">
                      Five-year FCFF projection discounted at your chosen
                      WACC; terminal value via Gordon growth.
                    </p>
                  </>
                ) : error ? (
                  <ErrorState error={error} onRetry={() => compute()} />
                ) : (
                  <LoadingRows rows={3} />
                )}
              </FeatureCard>
            </Reveal>

            <Reveal delay={160}>
              <FeatureCard className="flex h-full flex-col gap-5">
                <span className="eyebrow">Monte Carlo · 10,000 trials</span>
                {mc ? (
                  <div className="flex flex-col gap-4">
                    <StatBlock
                      label="Mean implied price"
                      value={fmtCurrency(mc.mean_price)}
                      size="md"
                      helper={
                        <span>σ {fmtCurrency(mc.std_price)}</span>
                      }
                    />
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <StatBlock
                        label="5% VaR"
                        value={fmtCurrency(mc.var_5pct)}
                        size="sm"
                        tone="negative"
                      />
                      <StatBlock
                        label="5% CVaR"
                        value={fmtCurrency(mc.cvar_5pct)}
                        size="sm"
                        tone="negative"
                      />
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(mc.percentiles).map(([p, v]) => (
                        <Badge key={p} variant="accent">
                          P{p} · {fmtCurrency(Number(v), 0)}
                        </Badge>
                      ))}
                    </div>
                    <div className="border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                      VaR (5%) is the implied price below which only 5% of trials land. CVaR (5%) is the expected price conditional on being in that worst-5% tail — a more conservative stress floor.
                    </div>
                  </div>
                ) : (
                  <LoadingRows rows={4} />
                )}
              </FeatureCard>
            </Reveal>
          </div>
        </Container>
      </Section>

      <Section spacing="default">
        <Container width="wide">
          <SectionHeader
            eyebrow="Sensitivity"
            title={<>WACC × terminal growth.</>}
            subtitle="The two assumptions the valuation is most sensitive to, on a single heatmap. The cell nearest your current base case is highlighted."
          />
          <div className="mt-10 grid grid-cols-1 gap-3 lg:grid-cols-12">
            <Reveal delay={40} className="lg:col-span-7">
              <ErrorBoundary>
              <FeatureCard className="h-full">
                <h3 className="text-xl font-semibold">Implied price grid</h3>
                <p className="mt-1 text-sm text-fg-muted">
                  Heatmap centred on the DCF base case.
                </p>
                <div className="border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                  Each cell is the implied share price at that WACC × terminal growth pair. The diagonal from top-right to bottom-left is the iso-price zone — different assumptions, same valuation. Your base case sits at the centre.
                </div>
                <div className="mt-6">
                  {sens ? (
                    <Heatmap
                      rowLabels={sens.row_values.map((v) => fmtPercent(v, 1))}
                      colLabels={sens.col_values.map((v) => fmtPercent(v, 1))}
                      values={sens.implied_prices}
                      formatCell={(v) =>
                        Number.isFinite(v) ? fmtNumber(v, 0) : "—"
                      }
                      center={dcf?.implied_price_usd}
                      height={360}
                    />
                  ) : (
                    <LoadingRows rows={6} />
                  )}
                </div>
              </FeatureCard>
              </ErrorBoundary>
            </Reveal>
            <Reveal delay={140} className="lg:col-span-5">
              <ErrorBoundary>
              <FeatureCard className="h-full">
                <h3 className="text-xl font-semibold">
                  Implied price distribution
                </h3>
                <p className="mt-1 text-sm text-fg-muted">
                  10 000 trials, shocks + supplier stress + outage haircut.
                </p>
                <div className="mt-6">
                  {mc ? (
                    <Histogram
                      samples={mc.implied_price_samples}
                      markers={[
                        {
                          value: mc.mean_price,
                          label: "Mean",
                          strokeClassName: "stroke-fg",
                        },
                        {
                          value: mc.var_5pct,
                          label: "VaR 5%",
                          strokeClassName: "stroke-severity-high",
                        },
                        {
                          value: mc.cvar_5pct,
                          label: "CVaR 5%",
                          strokeClassName: "stroke-severity-critical",
                        },
                      ]}
                      format={(v) => fmtCurrency(v, 0)}
                    />
                  ) : (
                    <LoadingRows rows={6} />
                  )}
                </div>
              </FeatureCard>
              </ErrorBoundary>
            </Reveal>
          </div>
        </Container>
      </Section>
    </PageShell>
  );
}