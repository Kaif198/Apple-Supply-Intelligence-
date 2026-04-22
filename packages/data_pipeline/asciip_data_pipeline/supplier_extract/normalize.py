"""Supplier name normalization.

Apple's Supplier List includes full legal names ("Hon Hai Precision
Industry Co., Ltd.") while news sources, tickers, and common parlance use
short forms ("Foxconn"). The normalizer collapses aliases to a single
canonical entry so the distress classifier and network graph see one node
per supplier.
"""

from __future__ import annotations

import re
from typing import Final

_ALIASES: Final[dict[str, str]] = {
    # legal name -> canonical
    "hon hai precision industry": "Hon Hai Precision (Foxconn)",
    "hon hai": "Hon Hai Precision (Foxconn)",
    "foxconn technology group": "Hon Hai Precision (Foxconn)",
    "foxconn": "Hon Hai Precision (Foxconn)",
    "taiwan semiconductor manufacturing": "TSMC",
    "tsmc": "TSMC",
    "samsung electronics": "Samsung Electronics",
    "lg display": "LG Display",
    "boe technology group": "BOE Technology",
    "luxshare precision industry": "Luxshare Precision",
    "luxshare": "Luxshare Precision",
    "pegatron corporation": "Pegatron",
    "pegatron": "Pegatron",
    "wistron": "Wistron",
    "murata manufacturing": "Murata Manufacturing",
    "largan precision": "Largan Precision",
    "goertek": "Goertek",
    "aac technologies holdings": "AAC Technologies",
    "aac technologies": "AAC Technologies",
    "sk hynix": "SK hynix",
    "micron technology": "Micron Technology",
    "broadcom": "Broadcom",
    "qualcomm": "Qualcomm",
    "skyworks solutions": "Skyworks Solutions",
    "corning": "Corning",
    "stmicroelectronics": "STMicroelectronics",
    "texas instruments": "Texas Instruments",
    "sony semiconductor": "Sony Semiconductor",
    "sony group corporation": "Sony Semiconductor",
    "amphenol": "Amphenol",
    "nidec": "Nidec",
    "tdk": "TDK",
    "yageo": "Yageo",
    "catl": "CATL",
    "amperex technology limited": "ATL (Amperex)",
    "amperex": "ATL (Amperex)",
    "lg energy solution": "LG Energy Solution",
    "sunwoda electronic": "Sunwoda",
    "simplo technology": "Simplo Technology",
    "jabil": "Jabil",
    "flex": "Flex",
}

# Suffixes we strip before alias lookup. Order-sensitive: longest first.
_SUFFIXES = (
    "co\\.,\\s*ltd\\.?",
    "corporation",
    "corp\\.?",
    "limited",
    "ltd\\.?",
    "inc\\.?",
    "gmbh",
    "ag",
    "s\\.a\\.?",
    "holdings",
    "group",
    "company",
    "co\\.?",
)

_SUFFIX_RE = re.compile(
    r"[\s,]*(?:" + "|".join(_SUFFIXES) + r")\.?\s*$",
    flags=re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[\s]{2,}")


def _strip_suffix(name: str) -> str:
    prev = None
    cur = name
    while prev != cur:
        prev = cur
        cur = _SUFFIX_RE.sub("", cur).strip(" ,.")
    return cur


def normalize_supplier_name(name: str) -> str:
    """Return the canonical supplier name for ``name``.

    The function is stable, idempotent, and case-insensitive on input; the
    output preserves the canonical casing declared in :data:`_ALIASES`.
    """
    if not name:
        return ""
    cleaned = _PUNCT_RE.sub(" ", name).strip()
    # Check alias map before suffix stripping so entries like
    # "foxconn technology group" resolve before the "group" suffix is stripped.
    pre_key = cleaned.lower()
    if pre_key in _ALIASES:
        return _ALIASES[pre_key]
    stripped = _strip_suffix(cleaned)
    key = stripped.lower()
    if key in _ALIASES:
        return _ALIASES[key]
    # Fall back: title-case each word, preserving existing initialisms.
    tokens = []
    for word in stripped.split():
        tokens.append(word if word.isupper() and len(word) > 1 else word.title())
    return " ".join(tokens)
