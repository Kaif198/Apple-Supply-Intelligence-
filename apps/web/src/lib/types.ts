/**
 * Shared response types — mirror `apps/api/asciip_api/schemas.py`.
 *
 * Keeping these types in sync with the backend Pydantic models is a
 * manual step today; Phase 8 introduces an OpenAPI → TS codegen pass.
 */

import type { Severity } from "@/lib/api";

export interface HealthComponent {
  name: string;
  status: "ok" | "degraded" | "down";
  detail?: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded" | "down";
  service: string;
  version: string;
  env: string;
  started_at: string;
  uptime_seconds: number;
  correlation_id: string | null;
  watermark: string | null;
  components: HealthComponent[];
}

export interface CommodityPricePoint {
  as_of_ts: string;
  price: number;
}

export interface CommoditySeries {
  entity_id: string;
  series: CommodityPricePoint[];
  vol_30d_annualized: number | null;
}

export interface CommoditiesResponse {
  as_of: string;
  commodities: CommoditySeries[];
}

export interface CommodityForecastPoint {
  ts: string;
  mean: number;
  lower: number;
  upper: number;
}

export interface CommodityForecastResponse {
  entity_id: string;
  horizon_days: number;
  members: Record<string, number>;
  val_mae: Record<string, number>;
  forecast: CommodityForecastPoint[];
  history_tail: CommodityPricePoint[];
}

export interface EquityPoint {
  as_of_ts: string;
  adj_close: number;
  log_return: number | null;
}

export interface AaplHistoryResponse {
  entity_id: "AAPL";
  series: EquityPoint[];
}

export interface FactorCoefficient {
  name: string;
  coefficient: number;
  std_error: number;
  t_value: number;
  p_value: number;
}

export interface FactorResponse {
  r_squared: number;
  adj_r_squared: number;
  n_obs: number;
  factors: FactorCoefficient[];
  notes: string;
}

export interface Supplier {
  id: string;
  name: string;
  parent?: string | null;
  country?: string | null;
  category?: string | null;
  tier?: number | null;
  annual_spend_billions?: number | null;
  distress_score?: number | null;
  otd_rate_90d?: number | null;
  dpo_days?: number | null;
  revenue_concentration_top3?: number | null;
  lat?: number | null;
  lon?: number | null;
}

export interface SuppliersResponse {
  as_of: string;
  count: number;
  suppliers: Supplier[];
}

export interface SupplierDistressResponse {
  id: string;
  name: string;
  distress_probability: number;
  distress_score: number | null;
  drivers: { feature: string; value: number }[];
  model_version: string | null;
}

export interface DisruptionEvent {
  id: string;
  as_of_ts: string;
  event_type: "commodity" | "tariff" | "logistics" | "supplier" | "fx";
  title: string;
  summary?: string | null;
  source_name: string;
  source_url?: string | null;
  impact_usd: number;
  severity: Severity;
  margin_delta_bps?: number | null;
  ev_delta_usd?: number | null;
  affected_supplier_ids: string[];
}

export interface EventsResponse {
  as_of: string;
  count: number;
  events: DisruptionEvent[];
}

export interface ShockSpecInput {
  name: string;
  mean_return: number;
  volatility: number;
  elasticity_bps_per_10pct: number;
}

export interface MonteCarloRequest {
  n_trials: number;
  horizon_years: number;
  shocks: ShockSpecInput[];
  correlation?: number[][];
  supplier_stress_mean: number;
  supplier_stress_sd: number;
  outage_revenue_haircut_mean: number;
  outage_revenue_haircut_sd: number;
  seed: number;
}

export interface MonteCarloResponse {
  n_trials: number;
  mean_price: number;
  std_price: number;
  percentiles: Record<string, number>;
  var_5pct: number;
  cvar_5pct: number;
  mean_margin_delta_bps: number;
  mean_revenue_delta_pct: number;
  implied_price_samples: number[];
}

export interface DcfRequest {
  revenue_ttm_bn?: number;
  revenue_cagr_5y?: number;
  fcf_margin?: number;
  wacc?: number;
  terminal_growth?: number;
  net_cash_bn?: number;
  shares_diluted_bn?: number;
  horizon_years?: number;
}

export interface DcfResponse {
  assumptions: Record<string, number>;
  projected_revenue_bn: number[];
  projected_fcf_bn: number[];
  enterprise_value_bn: number;
  equity_value_bn: number;
  implied_price_usd: number;
  pv_explicit_bn: number;
  pv_terminal_bn: number;
}

export interface SensitivityResponse {
  row_field: string;
  col_field: string;
  row_values: number[];
  col_values: number[];
  implied_prices: number[][];
}

export interface CausalResponse {
  method: string;
  ate: number;
  std_error: number;
  ci_low: number;
  ci_high: number;
  n_obs: number;
  refutations: Record<string, number>;
  assumptions: string[];
}

export interface Alert {
  id: string;
  created_at: string;
  event_id: string | null;
  severity: Severity;
  acknowledged_at: string | null;
  channel: string | null;
  payload: Record<string, unknown>;
}

export interface AlertsResponse {
  count: number;
  alerts: Alert[];
}
