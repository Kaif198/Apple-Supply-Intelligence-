-- features_wide — the denormalised feature matrix used for model training.
-- Populated by the Python build step; this migration just declares the shape.

CREATE TABLE IF NOT EXISTS features_wide (
    entity_id              VARCHAR NOT NULL,    -- e.g. 'copper', 'AAPL', 'SUP-0012'
    entity_kind            VARCHAR NOT NULL,    -- 'commodity' | 'equity' | 'supplier' | 'macro'
    as_of_ts               TIMESTAMP WITH TIME ZONE NOT NULL,
    feature_name           VARCHAR NOT NULL,
    feature_value          DOUBLE,
    feature_text           VARCHAR,
    git_sha                VARCHAR,
    PRIMARY KEY (entity_id, as_of_ts, feature_name)
);

CREATE INDEX IF NOT EXISTS features_wide_asof_idx
    ON features_wide (as_of_ts);
CREATE INDEX IF NOT EXISTS features_wide_name_idx
    ON features_wide (feature_name, as_of_ts DESC);
CREATE INDEX IF NOT EXISTS features_wide_entity_idx
    ON features_wide (entity_kind, entity_id, as_of_ts DESC);
