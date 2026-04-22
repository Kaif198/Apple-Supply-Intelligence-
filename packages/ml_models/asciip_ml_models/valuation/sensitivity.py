"""Two-way DCF sensitivity surfaces.

Surface most useful for the Valuation page heatmap: WACC vs terminal
growth. The function is written generically so other pairings (e.g. FCF
margin vs revenue growth) can be plotted with no code change.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Sequence

import numpy as np

from asciip_ml_models.valuation.base_case import DCFAssumptions, run_dcf


@dataclass(frozen=True)
class Sensitivity2D:
    base: DCFAssumptions
    row_field: str
    col_field: str
    row_values: tuple[float, ...]
    col_values: tuple[float, ...]
    implied_prices: tuple[tuple[float, ...], ...]  # rows × cols

    def to_dict(self) -> dict[str, object]:
        return {
            "row_field": self.row_field,
            "col_field": self.col_field,
            "row_values": list(self.row_values),
            "col_values": list(self.col_values),
            "implied_prices": [list(r) for r in self.implied_prices],
        }


def two_way_sensitivity(
    base: DCFAssumptions,
    *,
    row_field: str,
    row_values: Sequence[float],
    col_field: str,
    col_values: Sequence[float],
) -> Sensitivity2D:
    """Compute a grid of implied prices by flexing two assumption fields.

    Any ``DCFAssumptions`` float field is addressable. Invalid combinations
    (e.g. WACC ≤ terminal growth) are returned as ``nan`` rather than raising.
    """

    allowed = {f for f in DCFAssumptions.__dataclass_fields__ if f != "horizon_years"}
    for field in (row_field, col_field):
        if field not in allowed:
            raise ValueError(f"unknown sensitivity field: {field}")

    rows = tuple(float(v) for v in row_values)
    cols = tuple(float(v) for v in col_values)
    grid: list[tuple[float, ...]] = []

    for r in rows:
        row_prices: list[float] = []
        for c in cols:
            try:
                flexed = replace(base, **{row_field: r, col_field: c})
                row_prices.append(run_dcf(flexed).implied_price_usd)
            except (ValueError, ZeroDivisionError):
                row_prices.append(float("nan"))
        grid.append(tuple(row_prices))

    return Sensitivity2D(
        base=base,
        row_field=row_field,
        col_field=col_field,
        row_values=rows,
        col_values=cols,
        implied_prices=tuple(grid),
    )


def sensitivity_delta(
    base: DCFAssumptions, *, field: str, delta: float, fn: Callable[[DCFAssumptions], float] | None = None
) -> float:
    """Return ``Δ implied_price`` for a one-variable perturbation."""
    flex_up = replace(base, **{field: getattr(base, field) + delta})
    flex_dn = replace(base, **{field: getattr(base, field) - delta})
    pick = fn or (lambda a: run_dcf(a).implied_price_usd)
    return pick(flex_up) - pick(flex_dn)
