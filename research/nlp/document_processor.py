"""Document chunking and embedding pipeline for SEC filings.

Processes 10-K, 10-Q, and 8-K filings into chunks suitable for embedding
and retrieval-augmented generation (RAG). Section-aware chunking preserves
the logical structure of SEC filings so downstream models receive
contextually coherent passages.

Example usage:
    processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
    chunks = processor.chunk_filing(text, "AAPL", "10-K", "2024-10-30")
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A single chunk of text extracted from a financial document."""

    text: str
    metadata: dict  # source, filing_type, ticker, date, section, chunk_index
    char_count: int


# ---------------------------------------------------------------------------
# 10-K section regex patterns
# ---------------------------------------------------------------------------

_10K_SECTIONS: dict[str, re.Pattern[str]] = {
    "business": re.compile(
        r"(?:^|\n)\s*item\s+1[\.\s:\-]+(?!a\b)(.*?)(?=\n\s*item\s+1a[\.\s:\-]|\n\s*item\s+2[\.\s:\-]|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
    "risk_factors": re.compile(
        r"(?:^|\n)\s*item\s+1a[\.\s:\-]+(.*?)(?=\n\s*item\s+1b[\.\s:\-]|\n\s*item\s+2[\.\s:\-]|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
    "mda": re.compile(
        r"(?:^|\n)\s*item\s+7[\.\s:\-]+(?!a\b)(.*?)(?=\n\s*item\s+7a[\.\s:\-]|\n\s*item\s+8[\.\s:\-]|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
    "quantitative_disclosures": re.compile(
        r"(?:^|\n)\s*item\s+7a[\.\s:\-]+(.*?)(?=\n\s*item\s+8[\.\s:\-]|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
    "financial_statements": re.compile(
        r"(?:^|\n)\s*item\s+8[\.\s:\-]+(.*?)(?=\n\s*item\s+9[\.\s:\-]|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
}


class DocumentProcessor:
    """Process SEC filings into chunks suitable for embedding and RAG.

    Handles 10-K, 10-Q, 8-K filings with section-aware chunking.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        metadata: dict | None = None,
    ) -> list[DocumentChunk]:
        """Split *text* into overlapping chunks, preferring natural boundaries.

        Splitting priority:
        1. Paragraph boundaries (``\\n\\n``)
        2. Sentence boundaries (``. ``)
        3. Word boundaries (`` ``)
        4. Hard character split (last resort)

        Each returned :class:`DocumentChunk` carries *metadata* augmented with
        ``chunk_index``, ``char_start``, and ``char_end``.
        """
        if not text or not text.strip():
            return []

        base_meta = metadata or {}
        chunks: list[DocumentChunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # If we haven't reached the end of the text, try to find a
            # natural break point so we don't cut mid-word / mid-sentence.
            if end < len(text):
                end = self._find_break_point(text, start, end)

            chunk_text = text[start:end]
            chunk_meta = {
                **base_meta,
                "chunk_index": chunk_index,
                "char_start": start,
                "char_end": end,
            }
            chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    metadata=chunk_meta,
                    char_count=len(chunk_text),
                )
            )

            # If we reached the end of the text, stop.
            if end >= len(text):
                break

            # Advance by (chunk_size - overlap), but ensure we always move
            # forward by at least 1 character to avoid infinite loops.
            step = max(end - start - self.chunk_overlap, 1)
            start += step
            chunk_index += 1

        return chunks

    def extract_sections_10k(self, text: str) -> dict[str, str]:
        """Extract key 10-K sections by their SEC Item headings.

        Returns a dict mapping section name to the extracted text. Only
        sections that are actually found in *text* are included.
        """
        sections: dict[str, str] = {}
        for name, pattern in _10K_SECTIONS.items():
            match = pattern.search(text)
            if match:
                section_text = match.group(1).strip()
                if section_text:
                    sections[name] = section_text
        return sections

    def chunk_filing(
        self,
        text: str,
        ticker: str,
        filing_type: str,
        filing_date: str,
    ) -> list[DocumentChunk]:
        """Chunk a complete SEC filing with filing-level metadata.

        For 10-K filings, sections are extracted first and each section is
        chunked independently so that section context is preserved in the
        metadata of every chunk.  Other filing types are chunked as a single
        body of text.
        """
        if not text or not text.strip():
            return []

        base_meta = {
            "ticker": ticker,
            "filing_type": filing_type,
            "filing_date": filing_date,
        }

        if filing_type.upper() == "10-K":
            return self._chunk_10k(text, base_meta)

        # Default: chunk entire text with section="full"
        meta = {**base_meta, "section": "full"}
        return self.chunk_text(text, metadata=meta)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _chunk_10k(self, text: str, base_meta: dict) -> list[DocumentChunk]:
        """Section-aware chunking for 10-K filings."""
        sections = self.extract_sections_10k(text)

        if not sections:
            logger.warning(
                "No 10-K sections found for %s; chunking full text",
                base_meta.get("ticker", "?"),
            )
            return self.chunk_text(text, metadata={**base_meta, "section": "full"})

        all_chunks: list[DocumentChunk] = []
        for section_name, section_text in sections.items():
            meta = {**base_meta, "section": section_name}
            all_chunks.extend(self.chunk_text(section_text, metadata=meta))

        return all_chunks

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """Find the best break point within [start, end] of *text*.

        Preference order: paragraph > sentence > word > hard cut.
        We search backwards from *end* within the overlap region to find a
        natural boundary.
        """
        search_start = max(start, end - self.chunk_overlap)
        window = text[search_start:end]

        # 1. Paragraph boundary
        para_idx = window.rfind("\n\n")
        if para_idx != -1:
            return search_start + para_idx + 2  # after the double newline

        # 2. Sentence boundary (". " or ".\n")
        sentence_idx = window.rfind(". ")
        newline_sent = window.rfind(".\n")
        best_sent = max(sentence_idx, newline_sent)
        if best_sent != -1:
            return search_start + best_sent + 2

        # 3. Word boundary
        space_idx = window.rfind(" ")
        if space_idx != -1:
            return search_start + space_idx + 1

        # 4. Hard cut at end
        return end
