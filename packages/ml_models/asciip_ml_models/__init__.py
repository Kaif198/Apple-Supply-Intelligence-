"""asciip-ml-models — Layer 4 forecasting, distress, margin, stock, valuation.

Modules
-------
- :mod:`asciip_ml_models.registry` — model registration + artifact I/O
- :mod:`asciip_ml_models.margin`   — Ridge regression for margin sensitivity
- :mod:`asciip_ml_models.valuation`— DCF base case + sensitivity
- :mod:`asciip_ml_models.montecarlo`— vectorised 10k-trial supply-shock simulator
- :mod:`asciip_ml_models.forecast` — commodity price ensemble (next turn)
- :mod:`asciip_ml_models.distress` — supplier XGBoost classifier (next turn)
- :mod:`asciip_ml_models.factor`   — AAPL factor regression (next turn)
- :mod:`asciip_ml_models.causal`   — DoWhy/EconML wrappers (next turn)
"""

__version__ = "0.1.0"
