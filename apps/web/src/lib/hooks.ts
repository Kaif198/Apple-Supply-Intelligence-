/**
 * SWR hooks per ASCIIP endpoint.
 *
 * Every hook returns `{ data, error, isLoading, mutate }` so pages can
 * reuse a single loading/error skeleton pattern.
 */

"use client";

import useSWR, { type SWRConfiguration } from "swr";

import { apiFetch, swrFetcher } from "@/lib/api";
import type {
  AaplHistoryResponse,
  AlertsResponse,
  CausalResponse,
  CommoditiesResponse,
  CommodityForecastResponse,
  DcfRequest,
  DcfResponse,
  EventsResponse,
  FactorResponse,
  HealthResponse,
  MonteCarloRequest,
  MonteCarloResponse,
  SensitivityResponse,
  SupplierDistressResponse,
  SuppliersResponse,
} from "@/lib/types";

const DEFAULT: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  shouldRetryOnError: true,
  errorRetryCount: 2,
  errorRetryInterval: 1_500,
};

export const useHealth = () =>
  useSWR<HealthResponse>("/health", swrFetcher, { ...DEFAULT, refreshInterval: 30_000 });

export const useCommodityPrices = (lookback_days = 365) =>
  useSWR<CommoditiesResponse>(
    ["/commodities/prices", { lookback_days }],
    swrFetcher,
    { ...DEFAULT, refreshInterval: 60_000 },
  );

export const useCommodityForecast = (entity_id: string | null, horizon_days = 30) =>
  useSWR<CommodityForecastResponse>(
    entity_id ? ["/commodities/forecast", { entity_id, horizon_days }] : null,
    swrFetcher,
    DEFAULT,
  );

export const useAaplHistory = (lookback_days = 365) =>
  useSWR<AaplHistoryResponse>(
    ["/equity/aapl", { lookback_days }],
    swrFetcher,
    { ...DEFAULT, refreshInterval: 60_000 },
  );

export const useFactors = () =>
  useSWR<FactorResponse>("/equity/factors", swrFetcher, DEFAULT);

export const useSuppliers = () =>
  useSWR<SuppliersResponse>("/suppliers", swrFetcher, DEFAULT);

export const useSupplierDistress = (supplierId: string | null) =>
  useSWR<SupplierDistressResponse>(
    supplierId ? `/suppliers/${supplierId}/distress` : null,
    swrFetcher,
    DEFAULT,
  );

export const useEvents = (severity?: string, limit = 50) =>
  useSWR<EventsResponse>(
    ["/events", { severity, limit }],
    swrFetcher,
    { ...DEFAULT, refreshInterval: 30_000 },
  );

export const useAlerts = (unacknowledged_only = false) =>
  useSWR<AlertsResponse>(
    ["/alerts", { unacknowledged_only, limit: 100 }],
    swrFetcher,
    { ...DEFAULT, refreshInterval: 15_000 },
  );

/* -------------------------------------------------------------- mutations */

export async function runMonteCarlo(body: MonteCarloRequest): Promise<MonteCarloResponse> {
  return apiFetch<MonteCarloResponse>("/scenarios/run", { method: "POST", body });
}

export async function runDcf(body: DcfRequest): Promise<DcfResponse> {
  return apiFetch<DcfResponse>("/scenarios/dcf", { method: "POST", body });
}

export async function runSensitivity(body: {
  row_field: string;
  col_field: string;
  row_values: number[];
  col_values: number[];
}): Promise<SensitivityResponse> {
  return apiFetch<SensitivityResponse>("/scenarios/sensitivity", { method: "POST", body });
}

export async function runCausalAte(body: {
  treatment: string;
  outcome?: string;
  confounders?: string[];
  lookback_days?: number;
}): Promise<CausalResponse> {
  return apiFetch<CausalResponse>("/causal/ate", { method: "POST", body });
}

/* -------------------------------------------------------------- Signal of the Day */

const COMMODITY_ELASTICITY_BPS_PER_PCT: Record<string, number> = {
  aluminum:          0.8,
  copper:            0.9,
  lithium_carbonate: 0.4,
  rare_earth_ndpr:   0.3,
  crude_oil_wti:     0.5,
};

const COMMODITY_PRODUCT: Record<string, string> = {
  aluminum:          "iPhone chassis",
  copper:            "PCB traces",
  lithium_carbonate: "battery cells",
  rare_earth_ndpr:   "Taptic motors",
  crude_oil_wti:     "freight cost",
};

const APPLE_REVENUE_B = 391;
const APPLE_SHARES_B  = 15.4;
const APPLE_PE        = 31;

export function useSignalOfDay(): string | null {
  const prices = useCommodityPrices(5);
  if (!prices.data) return null;

  let best: { id: string; delta: number } | null = null;
  for (const c of prices.data.commodities) {
    const first = c.series.at(0)?.price;
    const last  = c.series.at(-1)?.price;
    if (!first || !last) continue;
    const delta = (last - first) / Math.abs(first);
    if (!best || Math.abs(delta) > Math.abs(best.delta)) {
      best = { id: c.entity_id, delta };
    }
  }
  if (!best) return null;

  const sign       = best.delta >= 0 ? "+" : "";
  const pctStr     = `${sign}${(best.delta * 100).toFixed(1)}%`;
  const name       = best.id.replace(/_/g, " ");
  const product    = COMMODITY_PRODUCT[best.id] ?? "components";
  const elasticity = COMMODITY_ELASTICITY_BPS_PER_PCT[best.id] ?? 0.5;
  const marginBps  = best.delta * 100 * elasticity;
  const epsDelta   = (marginBps / 10_000) * APPLE_REVENUE_B / APPLE_SHARES_B;
  const priceDelta = epsDelta * APPLE_PE;

  const fmtBps    = `${marginBps >= 0 ? "+" : ""}${marginBps.toFixed(1)} bps gross margin`;
  const fmtEps    = `${epsDelta >= 0 ? "+" : ""}$${Math.abs(epsDelta).toFixed(3)} EPS`;
  const fmtPrice  = `${priceDelta >= 0 ? "+" : ""}$${Math.abs(priceDelta).toFixed(2)} fair value`;

  return `${name.charAt(0).toUpperCase() + name.slice(1)} ${pctStr} in 5 sessions → ${fmtBps} → ${fmtEps} → AAPL ${fmtPrice}`;
}

