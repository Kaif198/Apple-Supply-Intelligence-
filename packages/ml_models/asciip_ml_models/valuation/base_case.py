"""AAPL DCF base case.

The default assumptions are calibrated so ``run_dcf(apple_base_case())``
produces an implied share price within 5% of the operator's reference
value of ~USD 176. The calibration was chosen post-hoc from FY2024/FY2025
public filings; every assumption is documented in the dataclass below and
exposed as an API parameter so consumers can A/B test their own views.

Cash-flow formula per year ``t``:
    revenue_t = revenue_0 * (1 + revenue_cagr) ** t
    FCF_t     = revenue_t * fcf_margin

Terminal value at the end of year N (Gordon growth):
    TV = FCF_N * (1 + g) / (WACC - g)

Enterprise value:
    EV = sum_{t=1..N} FCF_t / (1 + WACC)^t  +  TV / (1 + WACC)^N

Equity value = EV + net_cash (Apple has a substantial net cash position).
Implied price = equity_value / shares_diluted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

import numpy as np


@dataclass(frozen=True)
class DCFAssumptions:
    """Base-case inputs for an Apple DCF."""

    revenue_ttm_bn: float            # revenue in $ billions at t=0
    revenue_cagr_5y: float           # annual growth for the explicit forecast window
    fcf_margin: float                # FCF / revenue, held constant across horizon
    wacc: float                      # weighted average cost of capital
    terminal_growth: float           # perpetual growth after year N
    net_cash_bn: float               # cash + marketable securities - debt
    shares_diluted_bn: float         # diluted share count in billions
    horizon_years: int = 5

    def validate(self) -> None:
        if self.wacc <= self.terminal_growth:
            raise ValueError("wacc must be strictly greater than terminal_growth")
        if self.horizon_years < 1:
            raise ValueError("horizon_years must be >= 1")
        if self.shares_diluted_bn <= 0:
            raise ValueError("shares_diluted_bn must be positive")


@dataclass(frozen=True)
class DCFResult:
    assumptions: DCFAssumptions
    projected_revenue_bn: tuple[float, ...]
    projected_fcf_bn: tuple[float, ...]
    discount_factors: tuple[float, ...]
    pv_explicit_bn: float
    terminal_value_bn: float
    pv_terminal_bn: float
    enterprise_value_bn: float
    equity_value_bn: float
    implied_price_usd: float

    def to_dict(self) -> dict[str, object]:
        return {
            "assumptions": asdict(self.assumptions),
            "projected_revenue_bn": list(self.projected_revenue_bn),
            "projected_fcf_bn": list(self.projected_fcf_bn),
            "discount_factors": list(self.discount_factors),
            "pv_explicit_bn": self.pv_explicit_bn,
            "terminal_value_bn": self.terminal_value_bn,
            "pv_terminal_bn": self.pv_terminal_bn,
            "enterprise_value_bn": self.enterprise_value_bn,
            "equity_value_bn": self.equity_value_bn,
            "implied_price_usd": self.implied_price_usd,
        }


# Calibrated so run_dcf() returns ~USD 176 (see module docstring).
_APPLE_BASE: Final[DCFAssumptions] = DCFAssumptions(
    revenue_ttm_bn=408.0,
    revenue_cagr_5y=0.070,
    fcf_margin=0.270,
    wacc=0.081,
    terminal_growth=0.029,
    net_cash_bn=47.0,
    shares_diluted_bn=15.02,
    horizon_years=5,
)


def apple_base_case() -> DCFAssumptions:
    """Return a fresh copy of the base-case assumption set."""
    return _APPLE_BASE


def run_dcf(assumptions: DCFAssumptions) -> DCFResult:
    """Compute the DCF implied price under ``assumptions``."""
    assumptions.validate()

    years = np.arange(1, assumptions.horizon_years + 1, dtype=np.float64)
    revenue = assumptions.revenue_ttm_bn * (1.0 + assumptions.revenue_cagr_5y) ** years
    fcf = revenue * assumptions.fcf_margin
    discount = (1.0 + assumptions.wacc) ** years

    pv_explicit = float(np.sum(fcf / discount))
    terminal_value = float(
        fcf[-1] * (1.0 + assumptions.terminal_growth)
        / (assumptions.wacc - assumptions.terminal_growth)
    )
    pv_terminal = terminal_value / discount[-1]
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value + assumptions.net_cash_bn
    implied_price = (equity_value / assumptions.shares_diluted_bn)

    return DCFResult(
        assumptions=assumptions,
        projected_revenue_bn=tuple(float(v) for v in revenue),
        projected_fcf_bn=tuple(float(v) for v in fcf),
        discount_factors=tuple(float(v) for v in discount),
        pv_explicit_bn=pv_explicit,
        terminal_value_bn=terminal_value,
        pv_terminal_bn=pv_terminal,
        enterprise_value_bn=enterprise_value,
        equity_value_bn=equity_value,
        implied_price_usd=float(implied_price),
    )
