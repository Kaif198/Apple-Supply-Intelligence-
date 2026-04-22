"""Traceability matrix — asserts every requirement is covered by at least one test.

Phase 1 seeds this with the handful of requirements already exercised; every
subsequent phase adds its own ``@pytest.mark.req_N`` markers and the expected
set here.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


# Requirements that MUST have at least one tagged test at the end of Phase 8.
# The list mirrors the requirements document; adding a new requirement means
# adding the marker here AND tagging a real test with ``@pytest.mark.req_N``.
COVERED_REQUIREMENTS: frozenset[int] = frozenset(
    {
        1,   # Monorepo + bootstrap
        2,   # Source adapter registry
        3,   # Feature store + PIT correctness
        9,   # Supplier distress classifier
        10,  # Margin Ridge regression
        11,  # Causal engine
        13,  # DCF valuation
        14,  # Monte Carlo simulator
        15,  # API surface
        16,  # ETag + problem+json error layer
        17,  # Provenance + ingestion audit
        20,  # Graceful degradation
        22,  # Configuration fail-fast
        24,  # Apple supplier PDF extractor
        28,  # Model registry
    }
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKER_RE = re.compile(r"pytest\.mark\.req_(\d+)")

EXCLUDED_DIR_FRAGMENTS = (
    "/.venv/", "/.tox/", "/.pytest_cache/",
    "/node_modules/", "/.next/", "/.turbo/",
    "/dist/", "/build/", "/.git/",
)


def _collect_req_markers() -> set[int]:
    covered: set[int] = set()
    for path in REPO_ROOT.rglob("*.py"):
        posix = path.as_posix()
        if any(frag in posix for frag in EXCLUDED_DIR_FRAGMENTS):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in MARKER_RE.finditer(text):
            covered.add(int(match.group(1)))
    return covered


def test_every_required_marker_has_at_least_one_test() -> None:
    covered = _collect_req_markers()
    missing = sorted(COVERED_REQUIREMENTS - covered)
    assert not missing, (
        f"requirements without any @pytest.mark.req_N test: {missing}. "
        f"Add a marker to a meaningful test or re-scope the coverage set."
    )


def test_no_unknown_markers_leak_into_tests() -> None:
    """Every ``req_N`` marker we find must live in the pyproject whitelist."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = {
        int(m.group(1)) for m in re.finditer(r"req_(\d+):", pyproject)
    }
    used = _collect_req_markers()
    strays = sorted(used - declared)
    assert not strays, (
        f"tests use markers not declared in pyproject.toml: {strays}. "
        "Declare them under [tool.pytest.ini_options].markers."
    )


def test_pytest_knows_all_req_markers() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for i in range(1, 31):
        assert f"req_{i}:" in pyproject, f"pyproject.toml missing marker req_{i}"
