# Feature SQL

One `.sql` file per feature (or a small group of closely-related features). Each file begins with a header comment declaring inputs, output columns, and the as-of key used for point-in-time correctness.

The files are applied in lexical order by `FeatureStore.rebuild_feature_views()`; any file whose view name differs from its filename must document the mapping in the header comment. Prefer `CREATE OR REPLACE VIEW` so re-running is idempotent.

PIT guarantee: every view must emit an `as_of_ts` column; every read-time query wraps the view in a CTE that filters `WHERE as_of_ts < :point_in_time`.
