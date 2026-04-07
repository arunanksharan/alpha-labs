"""Tests for the SEC filing document processor."""

from __future__ import annotations

import pytest

from research.nlp.document_processor import DocumentChunk, DocumentProcessor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_10K_TEXT = """
Item 1. Business

Acme Corp is a global technology company that designs, manufactures, and
markets consumer electronics, software, and online services. The company
was founded in 1976 and is headquartered in Cupertino, California. Our
products include smartphones, personal computers, tablets, wearables,
and accessories. We also offer a range of related services.

Item 1A. Risk Factors

Investing in our securities involves a high degree of risk. The following
risk factors could materially affect our business, financial condition,
or results of operations. Global economic conditions may adversely impact
demand for our products. The technology industry is highly competitive and
subject to rapid change. We face significant competition from companies
that have greater resources and broader product lines. Supply chain
disruptions could impact our ability to deliver products on time.

Item 7. Management's Discussion and Analysis of Financial Condition

Revenue for the fiscal year was $394 billion, an increase of 8% from the
prior year. Services revenue grew 14% year-over-year, reaching $85 billion.
Gross margin improved to 45.2% from 43.3% in the prior year, primarily
driven by favorable product mix and cost efficiencies.

Item 7A. Quantitative and Qualitative Disclosures About Market Risk

We are exposed to market risk from changes in foreign currency exchange
rates, interest rates, and equity prices. We use derivative instruments
to partially offset our business exposure to foreign currency risk.

Item 8. Financial Statements and Supplementary Data

Consolidated Balance Sheet as of September 30, 2024:
Total assets: $352 billion
Total liabilities: $290 billion
Total shareholders equity: $62 billion

Item 9. Controls and Procedures
""".strip()


@pytest.fixture()
def processor() -> DocumentProcessor:
    return DocumentProcessor(chunk_size=200, chunk_overlap=50)


@pytest.fixture()
def large_processor() -> DocumentProcessor:
    return DocumentProcessor(chunk_size=1000, chunk_overlap=200)


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


class TestChunkText:
    def test_chunk_text_basic(self, processor: DocumentProcessor) -> None:
        """Chunks are created and respect the configured size limit."""
        text = "word " * 200  # ~1000 chars
        chunks = processor.chunk_text(text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.char_count <= processor.chunk_size + 1  # +1 for boundary rounding

    def test_chunk_overlap(self, processor: DocumentProcessor) -> None:
        """Consecutive chunks share overlapping text."""
        text = "A" * 500
        chunks = processor.chunk_text(text)

        assert len(chunks) >= 2

        # The end of chunk N should overlap with the start of chunk N+1
        for i in range(len(chunks) - 1):
            end_of_current = chunks[i].metadata["char_end"]
            start_of_next = chunks[i + 1].metadata["char_start"]
            assert start_of_next < end_of_current, (
                "Expected overlap between consecutive chunks"
            )

    def test_chunk_metadata(self, processor: DocumentProcessor) -> None:
        """Every chunk has chunk_index, char_start, char_end in metadata."""
        text = "Some text that should be chunked. " * 30
        chunks = processor.chunk_text(text, metadata={"source": "test"})

        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
            assert chunk.metadata["source"] == "test"

    def test_empty_text_returns_empty(self, processor: DocumentProcessor) -> None:
        """Empty or whitespace-only text produces no chunks."""
        assert processor.chunk_text("") == []
        assert processor.chunk_text("   ") == []
        assert processor.chunk_text("\n\n") == []

    def test_short_text_single_chunk(self, processor: DocumentProcessor) -> None:
        """Text shorter than chunk_size yields exactly one chunk."""
        text = "Short text."
        chunks = processor.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].text == text


# ---------------------------------------------------------------------------
# extract_sections_10k
# ---------------------------------------------------------------------------


class TestExtractSections10K:
    def test_extract_sections_10k(self, processor: DocumentProcessor) -> None:
        """Known 10-K text with Item headers returns expected sections."""
        sections = processor.extract_sections_10k(SAMPLE_10K_TEXT)

        assert "business" in sections
        assert "risk_factors" in sections
        assert "mda" in sections
        assert "quantitative_disclosures" in sections
        assert "financial_statements" in sections

    def test_business_section_content(self, processor: DocumentProcessor) -> None:
        sections = processor.extract_sections_10k(SAMPLE_10K_TEXT)
        assert "global technology company" in sections["business"]

    def test_risk_factors_content(self, processor: DocumentProcessor) -> None:
        sections = processor.extract_sections_10k(SAMPLE_10K_TEXT)
        assert "high degree of risk" in sections["risk_factors"]

    def test_mda_content(self, processor: DocumentProcessor) -> None:
        sections = processor.extract_sections_10k(SAMPLE_10K_TEXT)
        assert "$394 billion" in sections["mda"]

    def test_no_sections_found(self, processor: DocumentProcessor) -> None:
        """Plain text with no Item headers returns empty dict."""
        sections = processor.extract_sections_10k("Just some plain text.")
        assert sections == {}


# ---------------------------------------------------------------------------
# chunk_filing
# ---------------------------------------------------------------------------


class TestChunkFiling:
    def test_chunk_filing_10k_has_section_metadata(
        self, large_processor: DocumentProcessor
    ) -> None:
        """10-K filing chunks carry section names in metadata."""
        chunks = large_processor.chunk_filing(
            SAMPLE_10K_TEXT, "ACME", "10-K", "2024-09-30"
        )

        assert len(chunks) > 0
        section_names = {c.metadata["section"] for c in chunks}
        assert "business" in section_names or "risk_factors" in section_names

        # All chunks should have the filing-level metadata
        for chunk in chunks:
            assert chunk.metadata["ticker"] == "ACME"
            assert chunk.metadata["filing_type"] == "10-K"
            assert chunk.metadata["filing_date"] == "2024-09-30"
            assert "section" in chunk.metadata

    def test_chunk_filing_8k(self, processor: DocumentProcessor) -> None:
        """Non-10-K filings are chunked as a single body with section='full'."""
        text = "Material event disclosure. " * 50
        chunks = processor.chunk_filing(text, "ACME", "8-K", "2024-06-15")

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["section"] == "full"
            assert chunk.metadata["filing_type"] == "8-K"

    def test_chunk_filing_empty(self, processor: DocumentProcessor) -> None:
        """Empty filing text returns no chunks."""
        assert processor.chunk_filing("", "X", "10-Q", "2024-01-01") == []
