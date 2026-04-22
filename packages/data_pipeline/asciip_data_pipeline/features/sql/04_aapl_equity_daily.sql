-- Feature: aapl_equity_daily + aapl_return_daily
-- Inputs : src_yfinance_aapl (open/high/low/close/adj_close/volume)
-- Output : aapl_equity_daily  (prices) and aapl_return_daily (log returns).
-- Used by: factor regression (AAPL vs SPY/XLK/UUP + supply stress), Control
--          Tower sparkline, valuation implied-price delta.

CREATE OR REPLACE VIEW aapl_equity_daily AS
SELECT
    'AAPL'                                                     AS entity_id,
    'equity'                                                   AS entity_kind,
    CAST(date AS TIMESTAMP) + INTERVAL '21:00:00'              AS as_of_ts, -- ~16:00 ET ≈ 21:00 UTC
    CAST(open AS DOUBLE)                                       AS open,
    CAST(high AS DOUBLE)                                       AS high,
    CAST(low AS DOUBLE)                                        AS low,
    CAST(close AS DOUBLE)                                      AS close,
    CAST(adj_close AS DOUBLE)                                  AS adj_close,
    CAST(volume AS BIGINT)                                     AS volume
FROM src_yfinance_aapl;

CREATE OR REPLACE VIEW aapl_return_daily AS
WITH sorted AS (
    SELECT
        as_of_ts,
        adj_close,
        LAG(adj_close) OVER (ORDER BY as_of_ts) AS prev_close
    FROM aapl_equity_daily
)
SELECT
    'AAPL' AS entity_id,
    as_of_ts,
    adj_close,
    CASE
        WHEN prev_close IS NULL OR prev_close <= 0 THEN NULL
        ELSE LN(adj_close / prev_close)
    END AS log_return
FROM sorted;
