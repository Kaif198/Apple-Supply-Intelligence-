-- Feature: commodity_price_daily
-- Inputs : src_fred_commodity_prices      (raw if present, else snapshot)
-- Output : view commodity_price_daily(entity_id, as_of_ts, price)
-- PIT key: as_of_ts = date at 23:59:59 UTC.
-- Used by : margin sensitivity Ridge, commodity forecasting ensemble,
--           causal engine (lithium + copper treatment arms).

CREATE OR REPLACE VIEW commodity_price_daily AS
SELECT
    commodity                                                  AS entity_id,
    'commodity'                                                AS entity_kind,
    CAST(date AS TIMESTAMP) + INTERVAL '23:59:59'              AS as_of_ts,
    CAST(price AS DOUBLE)                                      AS price
FROM src_fred_commodity_prices;
