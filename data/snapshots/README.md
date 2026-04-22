# data/snapshots

Committed Parquet fallback datasets used when live sources are unreachable. Phase 2 seeds this directory with one file per source plus a `.sha256` sidecar; Phase 1 leaves it empty so the shape is visible.

Each snapshot is accompanied by `{source}.meta.json` recording the original fetch timestamp, upstream URL, and checksum — these values surface as the `"Using cached data from {timestamp}"` banner in the UI when fallback mode is active.
