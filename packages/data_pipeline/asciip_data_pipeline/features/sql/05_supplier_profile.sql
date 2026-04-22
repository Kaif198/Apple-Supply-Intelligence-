-- Feature: supplier_profile
-- Inputs : src_apple_supplier_pdf (id, name, country, category, tier, spend,
--          distress_score, otd_rate_90d, dpo_days, revenue_concentration_top3,
--          lat, lon).
-- Output : supplier_profile — one row per supplier with the snapshot timestamp
--          as as_of_ts so it plugs into the PIT pattern.

CREATE OR REPLACE VIEW supplier_profile AS
SELECT
    id                                                AS entity_id,
    'supplier'                                        AS entity_kind,
    CURRENT_TIMESTAMP                                 AS as_of_ts,
    name,
    country,
    category,
    tier,
    annual_spend_billions,
    distress_score,
    otd_rate_90d,
    dpo_days,
    revenue_concentration_top3,
    lat,
    lon
FROM src_apple_supplier_pdf;
