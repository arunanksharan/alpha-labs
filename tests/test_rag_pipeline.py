"""Tests for the financial RAG pipeline.

All tests run without API keys -- they exercise the pipeline logic,
vector storage, and retrieval, not the LLM generation step.
"""

from __future__ import annotations

import pytest

from research.nlp.document_processor import DocumentChunk
from research.nlp.rag_pipeline import FinancialRAG, RAGResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunks(n: int = 5, ticker: str = "AAPL") -> list[DocumentChunk]:
    """Generate *n* synthetic document chunks for testing."""
    chunks: list[DocumentChunk] = []
    for i in range(n):
        text = (
            f"Chunk {i}: Revenue grew {10 + i}% year-over-year driven by "
            f"strong demand in the services segment. Operating margin expanded "
            f"to {40 + i}% reflecting cost discipline and scale efficiencies."
        )
        chunks.append(
            DocumentChunk(
                text=text,
                metadata={
                    "ticker": ticker,
                    "filing_type": "10-K",
                    "filing_date": "2024-09-30",
                    "section": "mda",
                    "chunk_index": i,
                },
                char_count=len(text),
            )
        )
    return chunks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFinancialRAG:
    def test_add_documents_returns_count(self, tmp_path) -> None:
        """add_documents returns the number of chunks stored."""
        rag = FinancialRAG(db_path=tmp_path / "testdb")
        chunks = _make_chunks(3)
        count = rag.add_documents(chunks, collection="test_filings")
        assert count == 3

    def test_add_documents_empty(self, tmp_path) -> None:
        """Adding an empty list returns 0."""
        rag = FinancialRAG(db_path=tmp_path / "testdb")
        assert rag.add_documents([], collection="test_filings") == 0

    def test_search_returns_results(self, tmp_path) -> None:
        """After adding documents, search returns non-empty results."""
        rag = FinancialRAG(db_path=tmp_path / "testdb", top_k=3)
        chunks = _make_chunks(5)
        rag.add_documents(chunks, collection="test_filings")

        results = rag.search("revenue growth", collection="test_filings")
        assert len(results) > 0
        assert len(results) <= 3

        # Each result has the expected keys
        for r in results:
            assert "text" in r
            assert "metadata" in r
            assert "similarity_score" in r

    def test_search_empty_collection(self, tmp_path) -> None:
        """Searching a collection that does not exist returns empty list."""
        rag = FinancialRAG(db_path=tmp_path / "testdb")
        results = rag.search("anything", collection="nonexistent")
        assert results == []

    def test_search_result_metadata(self, tmp_path) -> None:
        """Retrieved documents preserve the original metadata."""
        rag = FinancialRAG(db_path=tmp_path / "testdb", top_k=2)
        chunks = _make_chunks(3, ticker="MSFT")
        rag.add_documents(chunks, collection="test_filings")

        results = rag.search("operating margin", collection="test_filings")
        assert len(results) > 0
        assert results[0]["metadata"]["ticker"] == "MSFT"

    def test_build_context_includes_question(self, tmp_path) -> None:
        """build_context output contains the original question."""
        rag = FinancialRAG(db_path=tmp_path / "testdb")
        chunks = _make_chunks(2)
        rag.add_documents(chunks, collection="test_filings")

        context = rag.build_context(
            "What drove revenue growth?", collection="test_filings"
        )
        assert "What drove revenue growth?" in context

    def test_build_context_includes_retrieved_text(self, tmp_path) -> None:
        """build_context output contains text from stored documents."""
        rag = FinancialRAG(db_path=tmp_path / "testdb")
        chunks = _make_chunks(2)
        rag.add_documents(chunks, collection="test_filings")

        context = rag.build_context("revenue", collection="test_filings")
        assert "Based on the following SEC filings:" in context
        # At least one chunk's text should appear
        assert "Revenue grew" in context

    def test_build_context_no_documents(self, tmp_path) -> None:
        """build_context with no matching collection returns fallback."""
        rag = FinancialRAG(db_path=tmp_path / "testdb")
        context = rag.build_context("anything", collection="empty")
        assert "No relevant documents found" in context
        assert "anything" in context

    def test_rag_result_dataclass(self) -> None:
        """RAGResult can be instantiated and fields accessed."""
        result = RAGResult(
            answer="Revenue grew 10%.",
            sources=[{"text": "chunk", "metadata": {}, "similarity_score": 0.95}],
            model="claude-sonnet-4-20250514",
            tokens_used=150,
        )
        assert result.answer == "Revenue grew 10%."
        assert len(result.sources) == 1
        assert result.model == "claude-sonnet-4-20250514"
        assert result.tokens_used == 150

    def test_query_without_api_key(self, tmp_path, monkeypatch) -> None:
        """query() without ANTHROPIC_API_KEY returns the assembled prompt."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        rag = FinancialRAG(db_path=tmp_path / "testdb")
        chunks = _make_chunks(2)
        rag.add_documents(chunks, collection="test_filings")

        result = rag.query("What is the operating margin?", collection="test_filings")
        assert isinstance(result, RAGResult)
        assert result.model == "none"
        assert result.tokens_used == 0
        assert "What is the operating margin?" in result.answer

    def test_add_then_add_more(self, tmp_path) -> None:
        """Adding documents to an existing collection appends, not replaces."""
        rag = FinancialRAG(db_path=tmp_path / "testdb", top_k=10)

        rag.add_documents(_make_chunks(3), collection="test_filings")
        rag.add_documents(_make_chunks(2, ticker="GOOG"), collection="test_filings")

        results = rag.search("revenue", collection="test_filings", top_k=10)
        assert len(results) == 5
