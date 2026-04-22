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
import { ImpactChain } from "@/components/ui/ImpactChain";
import { ErrorState, LoadingRows } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import {
  NetworkGraph,
  type NetworkEdge,
  type NetworkNode,
} from "@/components/charts/NetworkGraph";
import { runDcf, useSuppliers } from "@/lib/hooks";
import { fmtCurrency, fmtPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Supplier } from "@/lib/types";
import type { DcfResponse } from "@/lib/types";

const BASE_ASSUMPTIONS = {
  revenue_cagr_5y:  0.07,
  fcf_margin:       0.27,
  wacc:             0.081,
  terminal_growth:  0.029,
};

interface Scenario {
  id: string;
  label: string;
  description: string;
  fcf_margin_delta: number;
  revenue_haircut:  number;
  affectedCategories: string[];
  commodity?: string;
  marginDeltaBps: number;
}

const SCENARIOS: Scenario[] = [
  {
    id: "port_la_lb",
    label: "LA / LB port congestion",
    description: "Longshoremen strike shuts West Coast ports for 3 weeks. Ocean freight backlogs 60+ days.",
    fcf_margin_delta: -0.003,
    revenue_haircut:  0.01,
    affectedCategories: ["Logistics", "Freight"],
    marginDeltaBps: -30,
  },
  {
    id: "taiwan_typhoon",
    label: "Taiwan fab closure 72h",
    description: "Category-5 typhoon forces TSMC Fab 18 to pause production for 72 hours.",
    fcf_margin_delta: -0.008,
    revenue_haircut:  0.03,
    affectedCategories: ["Semiconductors", "Display"],
    marginDeltaBps: -80,
  },
  {
    id: "copper_shock",
    label: "Copper +50% over 1 quarter",
    description: "LME copper spikes on DRC export ban. iPhone PCB cost +18%, AirPods margins compress.",
    fcf_margin_delta: -0.012,
    revenue_haircut:  0.0,
    affectedCategories: ["Metals", "PCB"],
    commodity: "copper",
    marginDeltaBps: -120,
  },
  {
    id: "tier1_offline_30d",
    label: "Tier-1 supplier offline 30d",
    description: "Foxconn Zhengzhou assembly complex (40% of iPhone output) disrupted for 30 days.",
    fcf_margin_delta: -0.015,
    revenue_haircut:  0.04,
    affectedCategories: ["Assembly", "EMS"],
    marginDeltaBps: -150,
  },
  {
    id: "rare_earth_quota",
    label: "Rare-earth export quota",
    description: "China cuts NdPr export quota by 30%. MagSafe and Taptic motor costs surge.",
    fcf_margin_delta: -0.005,
    revenue_haircut:  0.01,
    affectedCategories: ["Magnetics", "Rare Earth"],
    commodity: "rare_earth_ndpr",
    marginDeltaBps: -50,
  },
  {
    id: "fx_usd_twd",
    label: "USD / TWD –15% FX shock",
    description: "Taiwan dollar depreciates 15% vs USD. TSMC contract repricing shifts cost structure.",
    fcf_margin_delta: -0.006,
    revenue_haircut:  0.0,
    affectedCategories: ["Semiconductors"],
    marginDeltaBps: -60,
  },
];

function buildGraph(
  suppliers: Supplier[],
  affectedCategories: string[],
): { nodes: NetworkNode[]; edges: NetworkEdge[] } {
  if (!suppliers.length) return { nodes: [], edges: [] };

  const apple: NetworkNode = { id: "apple", name: "Apple Inc.", tier: 0, kind: "apple", size: 16 };
  const nodes: NetworkNode[] = [apple];
  const edges: NetworkEdge[] = [];
  const tier1: Supplier[] = [];

  for (const s of suppliers) {
    const isAffected = affectedCategories.length > 0 &&
      affectedCategories.some(
        (cat) => s.category?.toLowerCase().includes(cat.toLowerCase()),
      );
    const baseSeverity =
      (s.distress_score ?? 0) >= 0.85 ? "critical"
      : (s.distress_score ?? 0) >= 0.65 ? "high"
      : (s.distress_score ?? 0) >= 0.5 ? "medium"
      : "low";
    const severity = isAffected ? "critical" : baseSeverity;
    nodes.push({
      id: s.id,
      name: s.name,
      tier: s.tier ?? 1,
      country: s.country,
      severity,
      size: 4 + Math.min(6, Math.log2(1 + (s.annual_spend_billions ?? 0.5)) * 2),
      kind: "supplier",
    });
    if ((s.tier ?? 1) === 1) {
      edges.push({ source: "apple", target: s.id, weight: s.annual_spend_billions ?? 0.5 });
      tier1.push(s);
    }
  }

  for (const s of suppliers) {
    if ((s.tier ?? 1) !== 2) continue;
    const candidates = tier1.filter((t1) => t1.country === s.country || t1.category === s.category);
    for (const t1 of candidates.slice(0, 3)) {
      edges.push({ source: t1.id, target: s.id, weight: 0.6 });
    }
  }

  return { nodes, edges };
}

export default function SimulatePage() {
  const [activeId, setActiveId] = React.useState<string>(SCENARIOS[0]!.id);
  const [baseDcf, setBaseDcf] = React.useState<DcfResponse | null>(null);
  const [shockDcf, setShockDcf] = React.useState<DcfResponse | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<unknown>(null);
  const suppliers = useSuppliers();

  const scenario = SCENARIOS.find((s) => s.id === activeId) ?? SCENARIOS[0]!;

  const graph = React.useMemo(
    () => buildGraph(suppliers.data?.suppliers ?? [], scenario.affectedCategories),
    [suppliers.data, scenario.affectedCategories],
  );

  const run = React.useCallback(async (s: Scenario) => {
    setBusy(true);
    setError(null);
    try {
      const [base, shock] = await Promise.all([
        runDcf(BASE_ASSUMPTIONS),
        runDcf({
          ...BASE_ASSUMPTIONS,
          fcf_margin: BASE_ASSUMPTIONS.fcf_margin + s.fcf_margin_delta,
          revenue_cagr_5y: BASE_ASSUMPTIONS.revenue_cagr_5y * (1 - s.revenue_haircut),
        }),
      ]);
      setBaseDcf(base);
      setShockDcf(shock);
    } catch (exc) {
      setError(exc);
    } finally {
      setBusy(false);
    }
  }, []);

  React.useEffect(() => {
    void run(scenario);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  const priceDelta =
    baseDcf && shockDcf
      ? shockDcf.implied_price_usd - baseDcf.implied_price_usd
      : null;

  return (
    <PageShell>
      <PageHero
        eyebrow="Shock Simulator"
        title={
          <>
            Pick a scenario.{" "}
            <span className="text-accent-muted">Watch the cascade.</span>
          </>
        }
        subtitle="Six procurement stress scenarios — each one propagates through bill-of-materials costs, revenue exposure, and the DCF model in real time. Select a scenario to see where the damage lands."
      />

      <Section spacing="tight">
        <Container width="wide">
          <Reveal>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setActiveId(s.id)}
                  className={cn(
                    "flex flex-col items-start gap-2 rounded-2xl border p-5 text-left transition-all duration-300",
                    activeId === s.id
                      ? "border-accent bg-accent/10"
                      : "border-border-subtle bg-bg-panel/40 hover:border-border-strong hover:bg-bg-raised",
                  )}
                >
                  <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-fg-subtle">
                    {s.id.replace(/_/g, " ")}
                  </span>
                  <span className="font-semibold text-fg">{s.label}</span>
                  <span className="text-xs text-fg-muted leading-relaxed">{s.description}</span>
                  <Badge variant={s.marginDeltaBps <= -100 ? "critical" : s.marginDeltaBps <= -50 ? "high" : "medium"}>
                    {s.marginDeltaBps} bps
                  </Badge>
                </button>
              ))}
            </div>
          </Reveal>
        </Container>
      </Section>

      <Section spacing="default">
        <Container width="wide">
          <SectionHeader
            eyebrow="Impact cascade"
            title={<>{scenario.label}</>}
            subtitle={scenario.description}
          />

          <div className="mt-10 grid grid-cols-1 gap-3 lg:grid-cols-12">
            <Reveal delay={0} className="lg:col-span-4">
              <FeatureCard className="flex h-full flex-col gap-5">
                <span className="eyebrow">Causal chain</span>
                <ImpactChain
                  values={{
                    commodity: scenario.commodity,
                    marginDeltaBps: scenario.marginDeltaBps,
                  }}
                />
                <div className="hairline" />
                {busy ? (
                  <LoadingRows rows={4} />
                ) : error ? (
                  <ErrorState error={error} onRetry={() => run(scenario)} />
                ) : baseDcf && shockDcf ? (
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                      <span className="eyebrow">Before / After</span>
                      <Badge variant={priceDelta != null && priceDelta < 0 ? "high" : "low"}>
                        DCF
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <StatBlock
                        label="Base"
                        value={fmtCurrency(baseDcf.implied_price_usd, 0)}
                        size="md"
                      />
                      <StatBlock
                        label="Shocked"
                        value={fmtCurrency(shockDcf.implied_price_usd, 0)}
                        size="md"
                        tone="negative"
                      />
                    </div>
                    {priceDelta != null && (
                      <div className="flex items-center justify-between rounded-xl bg-severity-high/10 px-4 py-3 text-sm">
                        <span className="text-fg-muted">Fair value impact</span>
                        <span className="tabular-nums font-semibold text-severity-high">
                          {priceDelta >= 0 ? "+" : ""}
                          {fmtCurrency(priceDelta, 0)}
                        </span>
                      </div>
                    )}
                    <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-fg-subtle">
                      <div>
                        <span className="block text-fg-muted">FCF margin haircut</span>
                        <span className="tabular-nums">{fmtPercent(scenario.fcf_margin_delta, 1)}</span>
                      </div>
                      <div>
                        <span className="block text-fg-muted">Revenue haircut</span>
                        <span className="tabular-nums">{fmtPercent(scenario.revenue_haircut, 1)}</span>
                      </div>
                    </div>
                  </div>
                ) : null}
              </FeatureCard>
            </Reveal>

            <Reveal delay={120} className="lg:col-span-8">
              <ErrorBoundary>
              <FeatureCard className="h-full">
                <div className="mb-4 flex items-baseline justify-between gap-3">
                  <div className="flex flex-col">
                    <span className="eyebrow">Network overlay</span>
                    <h3 className="text-xl font-semibold">
                      Affected nodes highlighted
                    </h3>
                  </div>
                  <span className="text-xs text-fg-subtle">
                    Red = scenario-affected · size = spend
                  </span>
                </div>
                <div className="mb-4 border-l-2 border-severity-high/40 pl-3 text-xs text-severity-high leading-relaxed">
                  Nodes highlighted in red are suppliers whose category aligns with the shock vector. Tier-2 exposure propagates upward through their tier-1 hubs.
                </div>
                {suppliers.isLoading ? (
                  <LoadingRows rows={10} />
                ) : suppliers.error ? (
                  <ErrorState error={suppliers.error} onRetry={() => suppliers.mutate()} />
                ) : (
                  <NetworkGraph nodes={graph.nodes} edges={graph.edges} height={440} />
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
