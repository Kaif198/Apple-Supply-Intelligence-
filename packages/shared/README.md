# asciip-shared

Cross-cutting utilities used by every ASCIIP service.

| Module | Purpose |
|---|---|
| `config` | Pydantic settings loaded from env + `.env` with fail-fast validation |
| `logging` | structlog-based JSON logger (pretty in dev) with correlation IDs |
| `correlation` | `contextvars`-backed correlation ID propagation |
| `exceptions` | Typed domain exceptions with RFC 7807-ready payloads |
| `provenance` | Source attribution dataclasses (Requirement 17) |
| `constants` | Severity thresholds, commodity codes, DCF base-case keys |
