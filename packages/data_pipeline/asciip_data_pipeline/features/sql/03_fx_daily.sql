-- Feature: fx_daily
-- Inputs : src_fred_fx (USD/CNY, USD/EUR) and src_ecb_reference_rates.
-- Output : fx_daily(entity_id='USD_CNY'|'USD_EUR'|'USD_xxx', as_of_ts, rate).
-- PIT key: as_of_ts = date at 23:59:59 UTC.

CREATE OR REPLACE VIEW fx_daily AS
SELECT
    pair                                                       AS entity_id,
    'fx'                                                       AS entity_kind,
    CAST(date AS TIMESTAMP) + INTERVAL '23:59:59'              AS as_of_ts,
    CAST(rate AS DOUBLE)                                       AS rate
FROM src_fred_fx;
