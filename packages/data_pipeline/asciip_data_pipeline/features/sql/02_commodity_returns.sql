-- Feature: commodity_returns_daily
-- Inputs : commodity_price_daily
-- Output : log returns + rolling 30d volatility per commodity.
-- PIT key: as_of_ts inherited from commodity_price_daily (date EOD UTC).

CREATE OR REPLACE VIEW commodity_returns_daily AS
WITH sorted AS (
    SELECT
        entity_id,
        as_of_ts,
        price,
        LAG(price) OVER (PARTITION BY entity_id ORDER BY as_of_ts) AS prev_price
    FROM commodity_price_daily
)
SELECT
    entity_id,
    as_of_ts,
    price,
    CASE
        WHEN prev_price IS NULL OR prev_price <= 0 THEN NULL
        ELSE LN(price / prev_price)
    END AS log_return
FROM sorted;

CREATE OR REPLACE VIEW commodity_vol_30d AS
SELECT
    entity_id,
    as_of_ts,
    STDDEV_POP(log_return) OVER (
        PARTITION BY entity_id ORDER BY as_of_ts
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) * SQRT(252) AS vol_30d_annualized
FROM commodity_returns_daily;
