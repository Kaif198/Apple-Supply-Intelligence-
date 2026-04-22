"""DCF base case + sensitivity tests."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest
from asciip_ml_models.valuation import (
    apple_base_case,
    run_dcf,
    two_way_sensitivity,
)

pytestmark = [pytest.mark.unit, pytest.mark.req_13]


def test_base_case_matches_operator_reference() -> None:
    """Implied price should land within ±5% of the operator's USD 176 anchor."""
    result = run_dcf(apple_base_case())
    assert 167.0 <= result.implied_price_usd <= 185.0
    assert abs(result.implied_price_usd - 176.0) / 176.0 < 0.05


def test_horizon_shape() -> None:
    a = apple_base_case()
    result = run_dcf(a)
    assert len(result.projected_revenue_bn) == a.horizon_years == 5
    assert len(result.projected_fcf_bn) == 5
    # Monotonic growth at positive CAGR.
    assert all(
        result.projected_revenue_bn[i + 1] > result.projected_revenue_bn[i] for i in range(4)
    )


def test_wacc_must_exceed_terminal_growth() -> None:
    a = replace(apple_base_case(), wacc=0.03, terminal_growth=0.04)
    with pytest.raises(ValueError):
        run_dcf(a)


def test_enterprise_plus_cash_equals_equity() -> None:
    a = apple_base_case()
    r = run_dcf(a)
    assert math.isclose(r.equity_value_bn, r.enterprise_value_bn + a.net_cash_bn, rel_tol=1e-9)
    assert math.isclose(r.implied_price_usd, r.equity_value_bn / a.shares_diluted_bn, rel_tol=1e-9)


def test_higher_wacc_decreases_price() -> None:
    base = run_dcf(apple_base_case()).implied_price_usd
    higher = run_dcf(replace(apple_base_case(), wacc=0.10)).implied_price_usd
    assert higher < base


def test_two_way_sensitivity_grid() -> None:
    grid = two_way_sensitivity(
        apple_base_case(),
        row_field="wacc",
        row_values=(0.070, 0.081, 0.090, 0.100),
        col_field="terminal_growth",
        col_values=(0.020, 0.029, 0.035),
    )
    assert len(grid.implied_prices) == 4
    assert all(len(row) == 3 for row in grid.implied_prices)
    # Higher WACC ⇒ lower price along any column.
    for col_idx in range(3):
        column = [row[col_idx] for row in grid.implied_prices]
        # Skip NaN cells (WACC ≤ g).
        finite = [v for v in column if not math.isnan(v)]
        assert all(finite[i] >= finite[i + 1] for i in range(len(finite) - 1))


def test_sensitivity_nan_when_wacc_below_g() -> None:
    grid = two_way_sensitivity(
        apple_base_case(),
        row_field="wacc",
        row_values=(0.020,),  # below any reasonable terminal growth
        col_field="terminal_growth",
        col_values=(0.025, 0.030),
    )
    assert all(math.isnan(v) for v in grid.implied_prices[0])
