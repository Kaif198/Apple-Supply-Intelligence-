"use client";

import * as React from "react";

import { PageShell } from "@/components/layout/PageShell";
import { PageHero } from "@/components/layout/PageHero";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/layout/Reveal";
import { FeatureCard } from "@/components/ui/FeatureCard";
import { Badge } from "@/components/ui/Badge";
import { ErrorState, LoadingRows } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import {
  NetworkGraph,
  type NetworkEdge,
  type NetworkNode,
} from "@/components/charts/NetworkGraph";
import { useSuppliers } from "@/lib/hooks";
import { fmtNumber, fmtPercent } from "@/lib/format";
import type { Supplier } from "@/lib/types";

/**
 * Network page — D3 force-directed supplier graph.
 *
 * Apple sits at the centre; every tier-1 is a spoke, and tier-2 links
 * to any tier-1 that shares their category or country.
 */

function buildGraph(
  suppliers: Supplier[],
): { nodes: NetworkNode[]; edges: NetworkEdge[] } {
  if (!suppliers.length) return { nodes: [], edges: [] };

  const apple: NetworkNode = {
    id: "apple",
    name: "Apple Inc.",
    tier: 0,
    kind: "apple",
    size: 16,
  };

  const nodes: NetworkNode[] = [apple];
  const edges: NetworkEdge[] = [];
  const tier1: Supplier[] = [];

  for (const s of suppliers) {
    const severity =
      (s.distress_score ?? 0) >= 0.85
        ? "critical"
        : (s.distress_score ?? 0) >= 0.65
          ? "high"
          : (s.distress_score ?? 0) >= 0.5
            ? "medium"
            : "low";
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
      edges.push({
        source: "apple",
        target: s.id,
        weight: s.annual_spend_billions ?? 0.5,
      });
      tier1.push(s);
    }
  }

  for (const s of suppliers) {
    if ((s.tier ?? 1) !== 2) continue;
    const candidates = tier1.filter(
      (t1) => t1.country === s.country || t1.category === s.category,
    );
    for (const t1 of candidates.slice(0, 3)) {
      edges.push({ source: t1.id, target: s.id, weight: 0.6 });
    }
  }

  return { nodes, edges };
}

export default function NetworkPage() {
  const suppliers = useSuppliers();
  const [selected, setSelected] = React.useState<NetworkNode | null>(null);
  const graph = React.useMemo(
    () => buildGraph(suppliers.data?.suppliers ?? []),
    [suppliers.data],
  );

  const selectedSupplier = selected
    ? suppliers.data?.suppliers.find((s) => s.id === selected.id) ?? null
    : null;

  return (
    <PageShell>
      <PageHero
        eyebrow="Network"
        title={
          <>
            The supply graph,{" "}
            <span className="text-accent-muted">force-simulated.</span>
          </>
        }
        subtitle="Spend concentration made visible. A distressed node near the centre is a procurement emergency; one at the edge is a manageable risk. Every edge is a dollar dependency."
      />

      <Section spacing="default">
        <Container width="wide">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
            <Reveal delay={0} className="lg:col-span-9">
              <ErrorBoundary>
              <FeatureCard className="h-full">
                <div className="flex items-baseline justify-between gap-3">
                  <div className="flex flex-col">
                    <span className="eyebrow">Graph</span>
                    <h3 className="text-xl font-semibold">
                      {graph.nodes.length - 1} suppliers · {graph.edges.length}{" "}
                      edges
                    </h3>
                  </div>
                  <span className="text-xs text-fg-subtle">
                    Drag nodes · scroll to zoom
                  </span>
                </div>
                <div className="mb-4 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                  Risk propagates upward through tiers: a tier-2 disruption must pass through its tier-1 hub to reach Apple, but a distressed tier-1 with many tier-2 dependencies creates compounding exposure.
                </div>
                <div className="mt-6">
                  {suppliers.isLoading ? (
                    <LoadingRows rows={10} />
                  ) : suppliers.error ? (
                    <ErrorState
                      error={suppliers.error}
                      onRetry={() => suppliers.mutate()}
                    />
                  ) : (
                    <NetworkGraph
                      nodes={graph.nodes}
                      edges={graph.edges}
                      onSelect={setSelected}
                    />
                  )}
                </div>
              </FeatureCard>
              </ErrorBoundary>
            </Reveal>

            <Reveal delay={140} className="lg:col-span-3">
              <FeatureCard className="flex h-full flex-col gap-4">
                <span className="eyebrow">Inspector</span>
                <h3 className="text-xl font-semibold">
                  {selected ? selected.name : "Click a node"}
                </h3>
                {selectedSupplier ? (
                  <dl className="flex flex-col gap-3 text-sm">
                    <NodeField
                      label="Country"
                      value={selectedSupplier.country ?? "—"}
                    />
                    <NodeField
                      label="Tier"
                      value={selectedSupplier.tier ?? "—"}
                    />
                    <NodeField
                      label="Category"
                      value={selectedSupplier.category ?? "—"}
                    />
                    <NodeField
                      label="Spend"
                      value={`$${fmtNumber(selectedSupplier.annual_spend_billions ?? 0, 2)}B`}
                    />
                    <NodeField
                      label="OTD · 90d"
                      value={fmtPercent(selectedSupplier.otd_rate_90d ?? 0, 1)}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium uppercase tracking-[0.14em] text-fg-subtle">
                        Distress
                      </span>
                      <Badge variant={selected?.severity ?? "low"}>
                        {selected?.severity ?? "low"}
                      </Badge>
                    </div>
                  </dl>
                ) : (
                  <p className="text-sm text-fg-muted">
                    Select any supplier node to inspect its profile. Apple
                    sits at the centre; each spoke is weighted by annual
                    spend.
                  </p>
                )}
              </FeatureCard>
            </Reveal>

            <Reveal delay={220} className="lg:col-span-12">
              <FeatureCard padded={false} className="p-5 md:p-6">
                <div className="flex flex-wrap items-center gap-3 text-sm text-fg-muted">
                  <span className="eyebrow">Legend</span>
                  <span>severity:</span>
                  <Badge variant="low">low</Badge>
                  <Badge variant="medium">medium</Badge>
                  <Badge variant="high">high</Badge>
                  <Badge variant="critical">critical</Badge>
                  <span className="mx-3 h-4 w-px bg-border" />
                  <span>node size · log(spend) · edge weight · trade intensity</span>
                  <span className="ml-auto text-xs text-fg-subtle">
                    Edge weight represents normalised annual trade volume — thicker edges = higher dependency.
                  </span>
                </div>
              </FeatureCard>
            </Reveal>
          </div>
        </Container>
      </Section>
    </PageShell>
  );
}

function NodeField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium uppercase tracking-[0.14em] text-fg-subtle">
        {label}
      </span>
      <span className="tabular-nums text-fg">{value}</span>
    </div>
  );
}