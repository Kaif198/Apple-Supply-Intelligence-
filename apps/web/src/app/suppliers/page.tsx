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
import { DataTable, type Column } from "@/components/ui/DataTable";
import { ErrorState, LoadingRows } from "@/components/common/States";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { useSupplierDistress, useSuppliers } from "@/lib/hooks";
import { fmtNumber, fmtPercent } from "@/lib/format";
import type { Supplier } from "@/lib/types";

/**
 * Suppliers page — ranked table on the left, distress inference on the
 * right. Apple-themed: hero + paired FeatureCards.
 */

function severityFromScore(score: number | null | undefined) {
  if (score == null) return "low" as const;
  if (score >= 0.85) return "critical" as const;
  if (score >= 0.65) return "high" as const;
  if (score >= 0.5) return "medium" as const;
  return "low" as const;
}

export default function SuppliersPage() {
  const suppliers = useSuppliers();
  const [selected, setSelected] = React.useState<string | null>(null);
  const [sortKey, setSortKey] = React.useState<string>("distress_score");
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("desc");

  const rows = React.useMemo(() => {
    const data = suppliers.data?.suppliers ?? [];
    const byKey: Record<string, (s: Supplier) => number | string | null> = {
      name: (s) => s.name,
      tier: (s) => s.tier ?? null,
      country: (s) => s.country ?? "",
      annual_spend_billions: (s) => s.annual_spend_billions ?? 0,
      distress_score: (s) => s.distress_score ?? 0,
      otd_rate_90d: (s) => s.otd_rate_90d ?? 0,
    };
    const getter = (byKey[sortKey] ?? byKey.name) as (
      s: Supplier,
    ) => number | string | null;
    return [...data].sort((a, b) => {
      const va = getter(a);
      const vb = getter(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? va - vb
          : String(va).localeCompare(String(vb));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [suppliers.data, sortKey, sortDir]);

  const detail = useSupplierDistress(selected);

  const columns: Column<Supplier>[] = [
    {
      key: "name",
      header: "Supplier",
      accessor: (r) => (
        <div className="flex flex-col">
          <span className="text-fg">{r.name}</span>
          <span className="text-xs text-fg-subtle">
            {r.parent ?? "independent"}
          </span>
        </div>
      ),
      sortValue: (r) => r.name,
      width: "26%",
    },
    {
      key: "country",
      header: "Country",
      accessor: (r) => r.country ?? "—",
      sortValue: (r) => r.country ?? "",
      width: "10%",
    },
    {
      key: "tier",
      header: "Tier",
      accessor: (r) => r.tier ?? "—",
      align: "right",
      sortValue: (r) => r.tier ?? 0,
      width: "8%",
    },
    {
      key: "annual_spend_billions",
      header: "Spend ($B)",
      accessor: (r) => fmtNumber(r.annual_spend_billions ?? 0, 2),
      align: "right",
      sortValue: (r) => r.annual_spend_billions ?? 0,
    },
    {
      key: "otd_rate_90d",
      header: "OTD 90d",
      accessor: (r) => fmtPercent(r.otd_rate_90d ?? 0, 1),
      align: "right",
      sortValue: (r) => r.otd_rate_90d ?? 0,
    },
    {
      key: "distress_score",
      header: "Distress",
      accessor: (r) => {
        const sev = severityFromScore(r.distress_score);
        return (
          <div className="flex items-center justify-end gap-2">
            <span className="tabular-nums">
              {fmtNumber(r.distress_score ?? 0, 2)}
            </span>
            <Badge variant={sev}>{sev}</Badge>
          </div>
        );
      },
      align: "right",
      sortValue: (r) => r.distress_score ?? 0,
    },
  ];

  return (
    <PageShell>
      <PageHero
        eyebrow="Suppliers"
        title={
          <>
            Distress, ranked.{" "}
            <span className="text-accent-muted">Every tier.</span>
          </>
        }
        subtitle="Every tier-1 and tier-2 supplier scored for operational disruption risk. Click any row to see what's driving the score — and what it costs Apple if that supplier goes offline."
      />

      <Section spacing="default">
        <Container width="wide">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <Reveal delay={40} className="lg:col-span-2">
              <ErrorBoundary>
              <FeatureCard padded={false} className="h-full p-6 md:p-8">
                <div className="mb-4 border-l-2 border-accent/40 pl-3 text-xs text-fg-subtle leading-relaxed">
                  Distress score is the calibrated probability of operational disruption within 90 days. Scores ≥ 0.65 trigger automated procurement alerts.
                </div>
                <div className="mb-5 flex items-center justify-between gap-3">
                  <div className="flex flex-col">
                    <span className="eyebrow">Base</span>
                    <h3 className="text-xl font-semibold md:text-2xl">
                      {suppliers.data?.count ?? 0} suppliers
                    </h3>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-xs text-fg-subtle">
                      Click a row · run the classifier live
                    </span>
                    {suppliers.data?.as_of && (
                      <FreshnessStrip
                        items={[{ label: "Supplier filings", as_of: suppliers.data.as_of, source: "SEC EDGAR" }]}
                      />
                    )}
                  </div>
                </div>
                {suppliers.isLoading ? (
                  <LoadingRows rows={8} />
                ) : suppliers.error ? (
                  <ErrorState
                    error={suppliers.error}
                    onRetry={() => suppliers.mutate()}
                  />
                ) : (
                  <DataTable<Supplier>
                    columns={columns}
                    rows={rows}
                    rowKey={(r) => r.id}
                    onRowClick={(r) => setSelected(r.id)}
                    activeRowKey={selected}
                    sortKey={sortKey}
                    sortDir={sortDir}
                    onSort={(k) => {
                      if (k === sortKey) {
                        setSortDir(sortDir === "asc" ? "desc" : "asc");
                      } else {
                        setSortKey(k);
                        setSortDir("desc");
                      }
                    }}
                    emptyState="No suppliers loaded."
                  />
                )}
              </FeatureCard>
              </ErrorBoundary>
            </Reveal>

            <Reveal delay={140}>
              <FeatureCard className="flex h-full flex-col gap-4">
                <span className="eyebrow">Distress detail</span>
                <h3 className="text-xl font-semibold">
                  {selected
                    ? "XGBoost + isotonic calibration"
                    : "Pick a supplier"}
                </h3>

                {!selected ? (
                  <p className="text-sm text-fg-muted">
                    Select a row to call{" "}
                    <code className="rounded bg-bg-raised px-1.5 py-0.5 font-mono text-xs">
                      /api/suppliers/{"{id}"}/distress
                    </code>
                    . We'll return probability plus the top drivers.
                  </p>
                ) : detail.isLoading ? (
                  <LoadingRows rows={5} />
                ) : detail.error ? (
                  <ErrorState
                    error={detail.error}
                    onRetry={() => detail.mutate()}
                  />
                ) : detail.data ? (
                  <div className="flex flex-col gap-5">
                    <div className="flex items-baseline justify-between">
                      <div className="flex flex-col">
                        <span className="text-xs font-medium uppercase tracking-[0.14em] text-fg-subtle">
                          Probability of distress
                        </span>
                        <span className="text-4xl font-semibold tabular-nums">
                          {fmtPercent(detail.data.distress_probability, 1)}
                        </span>
                      </div>
                      <Badge
                        variant={severityFromScore(
                          detail.data.distress_probability,
                        )}
                      >
                        {severityFromScore(detail.data.distress_probability)}
                      </Badge>
                    </div>
                    <div className="hairline" />
                    <ImpactChain
                      values={{
                        supplierName: selected ? suppliers.data?.suppliers.find(s => s.id === selected)?.name : undefined,
                        marginDeltaBps: detail.data.distress_probability >= 0.5
                          ? -(detail.data.distress_probability * 120)
                          : undefined,
                      }}
                    />
                    <div className="hairline" />
                    <div>
                      <span className="eyebrow">Drivers</span>
                      <ul className="mt-3 flex flex-col gap-1.5 text-sm">
                        {detail.data.drivers.slice(0, 6).map((d) => (
                          <li
                            key={d.feature}
                            className="flex items-center justify-between rounded-xl bg-bg-raised/70 px-4 py-2.5"
                          >
                            <span className="text-fg-muted">{d.feature}</span>
                            <span className="tabular-nums text-fg">
                              {fmtNumber(d.value, 2)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <p className="text-xs text-fg-subtle">
                      Model · {detail.data.model_version ?? "fallback"} ·
                      calibrated on historical disruption events.
                    </p>
                  </div>
                ) : (
                  <LoadingRows rows={6} />
                )}
              </FeatureCard>
            </Reveal>
          </div>
        </Container>
      </Section>
    </PageShell>
  );
}