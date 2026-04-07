"""Retrieval-Augmented Generation pipeline for financial document Q&A.

Uses LanceDB for vector storage and Anthropic's Claude for generation.
Designed for SEC filings, earnings calls, and research reports.

The embedding step uses a deterministic hash-based embedding by default so
that the full pipeline can be tested and exercised without API keys.  In
production this should be swapped for a real embedding model (e.g.
Anthropic Voyage, OpenAI ``text-embedding-3-large``).

Example usage:
    from research.nlp.document_processor import DocumentProcessor
    from research.nlp.rag_pipeline import FinancialRAG

    processor = DocumentProcessor()
    chunks = processor.chunk_filing(sec_text, "AAPL", "10-K", "2024-10-30")
    rag = FinancialRAG(db_path="/tmp/vectordb")
    rag.add_documents(chunks)
    result = rag.query("What are Apple's key risk factors?")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from research.nlp.document_processor import DocumentChunk


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RAGResult:
    """Container for a single RAG query result."""

    answer: str
    sources: list[dict]  # [{text, metadata, similarity_score}, ...]
    model: str
    tokens_used: int


# ---------------------------------------------------------------------------
# Hash-based embedding (test / offline fallback)
# ---------------------------------------------------------------------------

def _hash_embedding(text: str, dim: int = 1024) -> np.ndarray:
    """Deterministic hash-based pseudo-embedding.

    This is **not** a semantic embedding -- it exists purely so the full
    pipeline can be exercised without an API key.  The vectors are
    reproducible for the same input text, which makes testing predictable.

    We use the hash digest to seed a PRNG so that every component is a
    well-formed float (no NaN / Inf from raw byte reinterpretation).
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "little")
    rng = np.random.Generator(np.random.PCG64(seed))
    arr = rng.standard_normal(dim).astype(np.float32)
    # Normalise to unit vector
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr /= norm
    return arr


# ---------------------------------------------------------------------------
# Main RAG class
# ---------------------------------------------------------------------------


class FinancialRAG:
    """RAG pipeline for querying financial documents with Claude.

    Uses LanceDB for vector storage, Anthropic API for generation.
    Designed for SEC filings, earnings calls, and research reports.
    """

    def __init__(
        self,
        db_path: Path | str = "data/store/vectordb",
        embedding_dim: int = 1024,
        top_k: int = 5,
    ) -> None:
        import lancedb

        self.db_path = Path(db_path)
        self.embedding_dim = embedding_dim
        self.top_k = top_k
        self.db = lancedb.connect(str(self.db_path))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_documents(
        self,
        chunks: list[DocumentChunk],
        collection: str = "filings",
    ) -> int:
        """Embed *chunks* and upsert them into a LanceDB table.

        Returns the number of documents added.
        """
        if not chunks:
            return 0

        records = []
        for chunk in chunks:
            vector = _hash_embedding(chunk.text, dim=self.embedding_dim)
            records.append(
                {
                    "text": chunk.text,
                    "metadata": json.dumps(chunk.metadata),
                    "vector": vector.tolist(),
                }
            )

        try:
            resp = self.db.list_tables()
            table_names = resp.tables if hasattr(resp, "tables") else list(resp)
        except Exception:
            table_names = []

        if collection in table_names:
            table = self.db.open_table(collection)
            table.add(records)
        else:
            try:
                self.db.create_table(collection, data=records)
            except ValueError:
                table = self.db.open_table(collection)
                table.add(records)

        logger.info("Added %d chunks to collection '%s'", len(records), collection)
        return len(records)

    def search(
        self,
        query: str,
        collection: str = "filings",
        top_k: int | None = None,
    ) -> list[dict]:
        """Embed *query* and return the *top_k* most similar documents.

        Each result dict contains ``text``, ``metadata``, and
        ``similarity_score``.
        """
        k = top_k or self.top_k

        try:
            resp = self.db.list_tables()
            table_names = resp.tables if hasattr(resp, "tables") else list(resp)
        except Exception:
            table_names = []
        if collection not in table_names:
            logger.warning("Collection '%s' does not exist", collection)
            return []

        query_vec = _hash_embedding(query, dim=self.embedding_dim)
        table = self.db.open_table(collection)
        results = table.search(query_vec.tolist()).limit(k).to_list()

        output: list[dict] = []
        for row in results:
            output.append(
                {
                    "text": row["text"],
                    "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                    "similarity_score": float(row.get("_distance", 0.0)),
                }
            )

        return output

    def build_context(
        self,
        question: str,
        collection: str = "filings",
    ) -> str:
        """Search for relevant chunks and format them into a prompt context."""
        results = self.search(question, collection=collection)

        if not results:
            return f"No relevant documents found.\n\nQuestion: {question}"

        chunks_text = "\n\n---\n\n".join(
            f"[Source: {r['metadata']}]\n{r['text']}" for r in results
        )

        return (
            f"Based on the following SEC filings:\n\n"
            f"{chunks_text}\n\n"
            f"Answer: {question}"
        )

    def query(
        self,
        question: str,
        collection: str = "filings",
        system_prompt: str | None = None,
    ) -> RAGResult:
        """End-to-end RAG: retrieve context, call Claude, return answer.

        If ``ANTHROPIC_API_KEY`` is not set the method returns a
        :class:`RAGResult` whose ``answer`` field contains the fully
        assembled prompt (useful for inspection and testing).
        """
        sources = self.search(question, collection=collection)
        context = self.build_context(question, collection=collection)

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.info("ANTHROPIC_API_KEY not set; returning assembled prompt")
            return RAGResult(
                answer=context,
                sources=sources,
                model="none",
                tokens_used=0,
            )

        # Call Claude via the Anthropic SDK
        return self._call_claude(question, context, sources, system_prompt, api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_claude(
        self,
        question: str,
        context: str,
        sources: list[dict],
        system_prompt: str | None,
        api_key: str,
    ) -> RAGResult:
        """Call the Anthropic API with the assembled context."""
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        sys_prompt = system_prompt or (
            "You are a senior financial analyst. Answer questions about SEC "
            "filings using only the provided context. Cite specific sections "
            "when possible. If the context does not contain enough information "
            "to answer, say so clearly."
        )

        model = "claude-sonnet-4-20250514"
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            system=sys_prompt,
            messages=[
                {"role": "user", "content": context},
            ],
        )

        answer = message.content[0].text if message.content else ""
        tokens_used = (message.usage.input_tokens or 0) + (message.usage.output_tokens or 0)

        return RAGResult(
            answer=answer,
            sources=sources,
            model=model,
            tokens_used=tokens_used,
        )
