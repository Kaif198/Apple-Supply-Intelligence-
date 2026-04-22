"""Apple Supplier Responsibility PDF download + parse (Requirement 24).

The supplier extractor has three stages:

1. **Download** — quarterly HTTPS GET. Apple changes the URL yearly; the
   operator overrides via ``APPLE_SUPPLIER_PDF_URL`` or we fall back to
   walking the SR page for the latest PDF link.
2. **Parse** — ``pypdf`` plus regex pipeline splits name/parent/country/
   facility. Name normalization handles the well-known aliases
   (e.g. "Hon Hai Precision" / "Foxconn").
3. **Geocode** — handled by
   :mod:`asciip_data_pipeline.supplier_extract.geocode`; this adapter only
   emits the structured text.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import httpx
import polars as pl
from pypdf import PdfReader
from selectolax.parser import HTMLParser

from asciip_data_pipeline.sources.base import Source, register_source

_SR_INDEX_URL = "https://www.apple.com/supplier-responsibility/"


_NAME_ALIASES: dict[str, str] = {
    "Hon Hai Precision Industry Co., Ltd.": "Hon Hai Precision (Foxconn)",
    "Foxconn Technology Group": "Hon Hai Precision (Foxconn)",
    "Foxconn": "Hon Hai Precision (Foxconn)",
    "Taiwan Semiconductor Manufacturing Company": "TSMC",
    "Taiwan Semiconductor Manufacturing": "TSMC",
    "Samsung Electronics Co., Ltd.": "Samsung Electronics",
    "LG Display Co., Ltd.": "LG Display",
    "BOE Technology Group Co., Ltd.": "BOE Technology",
    "Luxshare Precision Industry Co., Ltd.": "Luxshare Precision",
    "Pegatron Corporation": "Pegatron",
    "Murata Manufacturing Co., Ltd.": "Murata Manufacturing",
    "Largan Precision Co., Ltd.": "Largan Precision",
    "Goertek Inc.": "Goertek",
    "AAC Technologies Holdings Inc.": "AAC Technologies",
}

_LINE_RE = re.compile(
    r"^(?P<name>[A-Z][\w\s,.&()/'\-]+?)\s{2,}" r"(?P<country>[A-Z]{2})\s+(?P<address>.+)$"
)


@register_source
class AppleSupplierPDF(Source):
    name = "apple_supplier_pdf"
    source_url = "https://www.apple.com/supplier-responsibility/"
    # Aligned with adapter name so the feature store's src_* unification
    # treats this source uniformly with the others.
    snapshot_filename = "apple_supplier_pdf.parquet"

    retry_exceptions = (httpx.HTTPError, ConnectionError, TimeoutError, OSError)

    def _fetch(self) -> pl.DataFrame:
        pdf_url = self.settings.apple_supplier_pdf_url or self._discover_pdf_url()
        with httpx.Client(
            timeout=45.0,
            headers={"User-Agent": self.settings.nominatim_user_agent},
            follow_redirects=True,
        ) as client:
            r = client.get(pdf_url)
            r.raise_for_status()
            pdf_bytes = r.content

        rows = list(self._parse_pdf(pdf_bytes))
        if not rows:
            raise ConnectionError("Apple supplier PDF parsed to zero rows")
        return pl.DataFrame(rows)

    # ---------------------------------------------------------------- helpers

    def _discover_pdf_url(self) -> str:
        with httpx.Client(
            timeout=20.0,
            headers={"User-Agent": self.settings.nominatim_user_agent},
            follow_redirects=True,
        ) as client:
            r = client.get(_SR_INDEX_URL)
            r.raise_for_status()
        tree = HTMLParser(r.text)
        for link in tree.css("a[href$='.pdf']"):
            href = (link.attributes.get("href") or "").strip()
            if "supplier-list" in href.lower() or "supplier_list" in href.lower():
                return (
                    str(httpx.URL(href, scheme="https", host="www.apple.com"))
                    if href.startswith("/")
                    else href
                )
        raise ConnectionError("Apple SR page has no supplier-list PDF link")

    def _parse_pdf(self, pdf_bytes: bytes):  # type: ignore[no-untyped-def]
        reader = PdfReader(io.BytesIO(pdf_bytes))
        seen: set[str] = set()
        for page in reader.pages:
            text = page.extract_text() or ""
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("Apple Inc"):
                    continue
                m = _LINE_RE.match(line)
                if not m:
                    continue
                name = self.normalize_name(m.group("name").strip())
                if name in seen:
                    continue
                seen.add(name)
                yield {
                    "name": name,
                    "country": m.group("country"),
                    "address": m.group("address").strip(),
                }

    @staticmethod
    def normalize_name(name: str) -> str:
        if name in _NAME_ALIASES:
            return _NAME_ALIASES[name]
        # Strip common legal suffixes.
        cleaned = re.sub(
            r"\s*(Co\.,?|Ltd\.?|Inc\.?|Corp\.?|Corporation|Limited|GmbH|AG|S\.A\.)",
            "",
            name,
        ).strip(" ,.")
        return _NAME_ALIASES.get(cleaned, cleaned)


def parse_pdf_bytes(pdf_bytes: bytes) -> list[dict[str, str]]:
    """Public helper so tests can exercise parsing without network."""
    source = AppleSupplierPDF()
    return list(source._parse_pdf(pdf_bytes))


def parse_pdf_path(path: Path) -> list[dict[str, str]]:
    return parse_pdf_bytes(path.read_bytes())
