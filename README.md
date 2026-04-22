# Apple Supply Chain Intelligence Platform

---

## The Problem

Apple generates $391 billion in annual revenue from a supply chain that spans over 50 countries, depends on a handful of critical commodities — lithium, cobalt, rare earth elements, aluminum, copper — and routes the majority of its manufacturing through a concentrated cluster of suppliers in China and Taiwan.

That concentration is a calculated bet. It enables the cost efficiency and scale precision that makes Apple's 46% gross margin possible. But it also means that a single disruption — a geopolitical shift, a commodity spike, a tier-2 supplier failure — can propagate through the Bill of Materials, compress margin, and move the stock before analysts have time to model it.

The problem is not that these risks are invisible. They are reported in earnings calls, disclosed in 10-Ks, and tracked by specialists. The problem is that they are fragmented. Commodity data lives in one place, supplier health in another, geopolitical events in a third. By the time the signals are assembled into a coherent view of financial exposure, the market has already priced it in.

Apple's supply chain is not just an operational system. It is a financial variable. And right now, there is no single platform that treats it that way.

---

## Our Approach

We built a platform that connects external supply chain signals directly to dollar-denominated financial outcomes.

The core idea is simple: every disruption in Apple's supply chain has a traceable path to earnings. A rare earth price spike raises component costs. Raised component costs compress gross margin. Compressed gross margin reduces operating income. Reduced operating income changes the DCF-implied fair value of the stock. That chain is deterministic enough to model, and dynamic enough to require real-time inputs.

We call this the ImpactChain. It is the spine of the platform — a live propagation from raw signal to equity consequence.

On top of that, we layer three analytical capabilities:

**Forecasting.** Commodity prices are modeled using an ensemble of ARIMA, LightGBM, and Prophet, weighted by validation error. The output is a 30-to-180-day forward view with an 80% prediction interval, updated on each data refresh.

**Supplier Distress Scoring.** Each tracked supplier receives a distress score from an XGBoost classifier trained on financial ratios, revenue concentration, geographic exposure, and event history. Tier-1 and Tier-2 suppliers are modeled separately because their failure modes are different. A Tier-1 failure is an assembly stoppage. A Tier-2 failure is a parts shortage that Tier-1 cannot absorb.

**Causal Attribution.** We use double machine learning (DoWhy + econml) rather than plain regression. Standard OLS on commodity-versus-return scatters absorbs shared macro confounders and overstates the relationship. Double-ML partials out those confounders from both sides before estimating the effect, so the output is a defensible causal claim rather than a correlation dressed as one.

All of this runs through a simulation engine where a user can specify a shock scenario — a 25% tariff on Chinese imports, a lithium carbonate spike, a major supplier entering distress — and watch the ImpactChain propagate in real time through BOM structure, margin model, DCF, and supplier network.

---

## Business Impact

The platform addresses a specific gap in how institutional analysts and supply chain risk teams currently work.

Today, a supply chain analyst at a fund or inside Apple's own finance team would spend hours pulling commodity data from Bloomberg, cross-referencing supplier financials from EDGAR, reading event summaries from news aggregators, and then manually building a margin sensitivity model in Excel. The latency between signal and financial conclusion is measured in days, sometimes weeks.

This platform compresses that latency to minutes.

More precisely, it does four things that matter:

**Quantifies exposure, not just risk.** Most supply chain risk tools surface alerts — "copper prices are elevated," "this supplier has a low credit score." This platform translates those signals into basis points of gross margin impact and cents of EPS change. That is the language of investment decisions and earnings guidance.

**Models second-order effects.** A lithium carbonate price increase does not just affect battery costs. It affects the financial health of battery suppliers, which affects their ability to invest in capacity, which affects Apple's supply security in the following cycle. The network graph and distress model together capture this second-order propagation.

**Separates causation from noise.** Markets move on macro factors that have nothing to do with Apple's supply chain. The causal model isolates the supply chain contribution to stock returns from FX, broad market moves, and interest rate effects. The result is a cleaner signal for attribution.

**Enables scenario planning.** The simulation page lets a user construct a hypothetical shock and observe its full financial consequence before it happens. That capability has direct value in earnings preparation, capital allocation decisions, and risk committee presentations.

---

## Platform Structure

The platform is organized as a monorepo with four layers: data ingestion, feature store, analytical models, and frontend.

```
asciip/
├── apps/
│   ├── web/               Next.js 15 frontend — 8 pages, D3 charts, SWR hooks
│   └── api/               FastAPI backend — REST + SSE endpoints, ETag cache
├── packages/
│   ├── shared/            Config, structured logging, exception taxonomy
│   ├── data_pipeline/     Ingestion adapters (FRED, yfinance, EDGAR, Marketaux)
│   │                      DuckDB feature store — append-only, Parquet-backed
│   ├── ml_models/         Commodity ensemble forecast, supplier distress classifier,
│   │                      margin ridge regression, factor regression
│   └── causal/            DAG specification, DoWhy + econml double-ML, refutation tests
├── data/
│   ├── features/          asciip.duckdb — live feature store
│   ├── snapshots/         Shipped Parquet fallbacks (no API keys required)
│   └── models/            Serialized model artifacts and registry
├── tests/                 pytest — unit, property-based (Hypothesis), integration
├── .github/workflows/     CI: ruff lint → mypy → vitest → Next.js build → pytest
├── Makefile               Unix task runner
└── tasks.ps1              PowerShell equivalent for Windows
```

**Pages**

| Route | Function |
|---|---|
| `/` | Live control tower — AAPL price, commodity basket, supplier distress index, event velocity, Signal of the Day |
| `/commodities` | Ensemble price forecasts with prediction intervals; 30-day delta table across the full commodity basket |
| `/suppliers` | Per-supplier distress scores with feature-level breakdowns; Tier-1 and Tier-2 classification |
| `/network` | D3 force-directed supplier network; edge weight by annual spend, node color by distress score |
| `/events` | Typed disruption event log; each event carries a `margin_delta_bps` estimate and a live ImpactChain |
| `/valuation` | Interactive 5-year DCF, WACC-by-terminal-growth sensitivity heatmap, 10,000-trial Monte Carlo |
| `/macro` | 5-factor OLS with Newey-West standard errors; double-ML causal ATE for each supply chain driver |
| `/simulate` | Flagship — six shock scenarios propagate through BOM to margin to DCF to network overlay in real time |

**Data Sources**

All data sources are free-tier and public. The platform runs offline on first boot using shipped snapshots. Live ingestion activates by adding keys to `.env`.

| Source | What it provides |
|---|---|
| FRED | Commodity spot prices, FX rates, macro indicators |
| yfinance | AAPL daily equity, volume, earnings history |
| SEC EDGAR | Supplier 10-K and 10-Q filings for financial ratio extraction |
| Marketaux | Disruption event stream, entity-tagged to supplier and commodity |

**Model Stack**

| Model | Method | Where |
|---|---|---|
| Commodity forecast | ARIMA + LightGBM + Prophet ensemble | `/commodities` |
| Supplier distress | XGBoost classifier, calibrated probabilities | `/suppliers`, `/network` |
| Margin regression | Ridge regression on cost drivers | `/simulate`, `/events` |
| Factor model | 5-factor OLS, HAC standard errors (Newey-West) | `/macro` |
| Causal ATE | Double-ML via econml, DoWhy refutation | `/macro` |
| Valuation | Vectorized 5Y DCF, 10,000-trial Monte Carlo | `/valuation`, `/simulate` |

---

## Running the Platform

**Unix / macOS / WSL / Git Bash**

```bash
make bootstrap    # install Python and Node dependencies, seed DuckDB from snapshots
make up           # start API on :8000 and web on :3000
```

**Windows**

```powershell
./tasks.ps1 bootstrap
./tasks.ps1 up
```

The platform runs fully offline on first boot. No external API keys are required to use the shipped snapshots.

- Web interface: http://localhost:3000
- API documentation: http://localhost:8000/api/docs
- Health endpoint: http://localhost:8000/api/health

To enable live data ingestion, copy `.env.example` to `.env` and add keys for FRED, Marketaux, Finnhub, and SEC EDGAR.

---

## Technical Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 App Router, TypeScript strict mode, Tailwind CSS v4, SWR |
| Charts | D3.js v7 — SVG rendering, zero DOM manipulation from React |
| API | FastAPI, Pydantic v2, Uvicorn, ETag-based response cache |
| Feature store | DuckDB + Parquet — embedded, no server process, query-speed reads |
| Ingestion | Polars, yfinance, fredapi, finnhub-python, selectolax |
| ML | Prophet, LightGBM, XGBoost, scikit-learn |
| Causal | DoWhy, econml (double-ML / DML) |
| Valuation | NumPy-vectorized DCF, Monte Carlo simulation |
| Testing | pytest, Hypothesis (property-based), Vitest |
| CI | GitHub Actions — lint, typecheck, test, build on every push |

---

## Scope and Limitations

This is an independent research platform built on public data. It is not affiliated with, endorsed by, or sponsored by Apple Inc. All financial figures are modeled from public disclosures and open data sources. The platform is designed to demonstrate analytical methodology — it is not investment advice and should not be used as the basis for trading decisions.

The supplier dataset covers the companies disclosed in Apple's annual Supplier Responsibility Report. Tier-2 suppliers are approximated from public procurement and SEC filing analysis. BOM cost estimates are derived from teardown reports and public commodity benchmarks, not internal Apple data.

All trademarks belong to their respective owners.

---

*Built by Kaif Ahmed.*
