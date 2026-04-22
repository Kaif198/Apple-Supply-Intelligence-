-- ASCIIP feature store — initial schema.
-- Everything that persists beyond raw Parquet lives here. Derived / computed
-- features are declared as views in ../sql/*.sql so they are cheap to refresh.

-- Ingestion audit is already created lazily by audit.py; we include a
-- CREATE IF NOT EXISTS so fresh databases do not surprise the orchestrator.
CREATE TABLE IF NOT EXISTS ingestion_audit (
    id                     VARCHAR PRIMARY KEY,
    run_id                 VARCHAR NOT NULL,
    source_name            VARCHAR NOT NULL,
    source_url             VARCHAR NOT NULL,
    fetched_at             TIMESTAMP WITH TIME ZONE NOT NULL,
    row_count              INTEGER NOT NULL,
    checksum_sha256        VARCHAR NOT NULL,
    fallback               BOOLEAN NOT NULL,
    fallback_snapshot_ts   TIMESTAMP WITH TIME ZONE,
    notes                  VARCHAR,
    parquet_path           VARCHAR
);

-- Feature lineage per Requirement 3.3 / 17.5.
CREATE TABLE IF NOT EXISTS feature_lineage (
    feature_name   VARCHAR NOT NULL,
    git_sha        VARCHAR NOT NULL,
    source_tables  VARCHAR NOT NULL,          -- comma-separated
    author         VARCHAR,
    materialised_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (feature_name, materialised_at)
);

-- Model registry (Requirement 28) — used by asciip_ml_models.registry.
CREATE TABLE IF NOT EXISTS model_registry (
    id              VARCHAR PRIMARY KEY,
    family          VARCHAR NOT NULL,         -- e.g. forecast_commodity, classify_distress
    version         VARCHAR NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    metrics         JSON,
    hyperparameters JSON,
    artifact_path   VARCHAR NOT NULL,
    is_production   BOOLEAN NOT NULL DEFAULT FALSE,
    notes           VARCHAR
);

CREATE INDEX IF NOT EXISTS model_registry_family_idx
    ON model_registry (family, created_at DESC);

-- Disruption events (Requirement 11 + 26).
CREATE TABLE IF NOT EXISTS disruption_events (
    id              VARCHAR PRIMARY KEY,
    as_of_ts        TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type      VARCHAR NOT NULL,         -- commodity | tariff | logistics | supplier | fx
    title           VARCHAR NOT NULL,
    summary         VARCHAR,
    source_name     VARCHAR NOT NULL,
    source_url      VARCHAR,
    impact_usd      DOUBLE NOT NULL,
    severity        VARCHAR NOT NULL,         -- low | medium | high | critical
    margin_delta_bps INTEGER,
    ev_delta_usd    DOUBLE,
    affected_supplier_ids VARCHAR             -- comma-separated
);

CREATE INDEX IF NOT EXISTS disruption_events_ts_idx
    ON disruption_events (as_of_ts DESC);
CREATE INDEX IF NOT EXISTS disruption_events_sev_idx
    ON disruption_events (severity, as_of_ts DESC);

-- Alerts (Requirement 29).
CREATE TABLE IF NOT EXISTS alerts (
    id            VARCHAR PRIMARY KEY,
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL,
    event_id      VARCHAR REFERENCES disruption_events (id),
    severity      VARCHAR NOT NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    channel       VARCHAR,                    -- ui | email | webhook
    payload       JSON
);

-- Suppliers — canonical record (the PDF adapter + geocoder write here).
CREATE TABLE IF NOT EXISTS suppliers (
    id                           VARCHAR PRIMARY KEY,
    name                         VARCHAR NOT NULL,
    parent                       VARCHAR,
    country                      VARCHAR,
    category                     VARCHAR,
    tier                         INTEGER,
    annual_spend_billions        DOUBLE,
    lat                          DOUBLE,
    lon                          DOUBLE,
    as_of_ts                     TIMESTAMP WITH TIME ZONE NOT NULL,
    source_name                  VARCHAR,
    source_url                   VARCHAR
);

CREATE INDEX IF NOT EXISTS suppliers_name_idx ON suppliers (name);

-- Disruption scoring audit — every score recomputation lands here so we can
-- reproduce any displayed number back to its inputs (Requirement 17.4).
CREATE TABLE IF NOT EXISTS scoring_audit (
    id              VARCHAR PRIMARY KEY,
    event_id        VARCHAR REFERENCES disruption_events (id),
    scored_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    model_version   VARCHAR,
    inputs          JSON,
    outputs         JSON
);
