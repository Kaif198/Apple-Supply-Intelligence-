"""ASCIIP FastAPI backend.

Phase 1 exposes only ``/api/health`` so the rest of the monorepo (Docker,
Makefile, smoke tests, Render blueprint) can be wired end-to-end before
the full API surface lands in Phase 5.
"""

__version__ = "0.1.0"
