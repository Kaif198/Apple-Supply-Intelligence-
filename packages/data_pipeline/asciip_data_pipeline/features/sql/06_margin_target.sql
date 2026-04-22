-- Feature: apple_margin_target
-- Inputs : hardcoded 10-K history (see ml_models/valuation/base_case.py).
-- Output : quarterly gross margin target used as the Ridge regression label.
-- PIT key: as_of_ts = quarter-end + 45 days (filing lag).

CREATE OR REPLACE VIEW apple_margin_target AS
WITH base AS (
    SELECT * FROM (VALUES
        (DATE '2021-03-31', 0.4278),
        (DATE '2021-06-30', 0.4370),
        (DATE '2021-09-30', 0.4223),
        (DATE '2021-12-31', 0.4380),
        (DATE '2022-03-31', 0.4353),
        (DATE '2022-06-30', 0.4326),
        (DATE '2022-09-30', 0.4233),
        (DATE '2022-12-31', 0.4296),
        (DATE '2023-03-31', 0.4435),
        (DATE '2023-06-30', 0.4447),
        (DATE '2023-09-30', 0.4525),
        (DATE '2023-12-31', 0.4592),
        (DATE '2024-03-31', 0.4658),
        (DATE '2024-06-30', 0.4626),
        (DATE '2024-09-30', 0.4620),
        (DATE '2024-12-31', 0.4669),
        (DATE '2025-03-31', 0.4695),
        (DATE '2025-06-30', 0.4671),
        (DATE '2025-09-30', 0.4684)
    ) AS t(quarter_end, gross_margin)
)
SELECT
    'AAPL'                                          AS entity_id,
    'equity'                                        AS entity_kind,
    CAST(quarter_end AS TIMESTAMP) + INTERVAL '45 days' AS as_of_ts,
    gross_margin
FROM base;
