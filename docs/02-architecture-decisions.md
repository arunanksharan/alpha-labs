# Architecture Decision Records — 2026-04-07

## ADR-001: Build from Scratch vs Fork ai-hedge-fund

**Decision**: Build from scratch with modular architecture.

**Context**: Virat Singh's ai-hedge-fund (50K+ stars) is a viable starting point. External review suggested forking it.

**Reasoning**:
- Virat's codebase is a monolithic proof-of-concept, not production architecture
- Forking inherits his technical debt (no backtesting, no validation, no risk management)
- Our modular layer/connector pattern (BaseConnector, BaseStrategy, BaseFeature ABCs) cannot be retrofitted onto his code
- We already have 6,500+ lines of tested, production-quality code that surpasses his data layer
- Our EDGAR connector parses XBRL directly — his uses a paid API (Financial Datasets)

**Status**: Accepted. We reference his architecture for agent persona design (Week 7) but build independently.

---

## ADR-002: ChromaDB over Qdrant for Vector Storage

**Decision**: Use ChromaDB for vector embeddings, not Qdrant.

**Context**: External review suggested Qdrant (open source) for vector storage.

**Reasoning**:
- ChromaDB is Python-native, zero-config, runs in-process — no server to manage
- For a research platform (not production serving), in-process is faster and simpler
- Qdrant requires a separate server process — unnecessary complexity for our use case
- ChromaDB has first-class LangChain/LangGraph integration
- If we outgrow ChromaDB, the vector store is behind an abstraction — swap later

**Status**: Accepted. ChromaDB for Week 7 (LLM-powered research).

---

## ADR-003: VectorBT/Qlib First, QuantConnect LEAN Optional

**Decision**: Primary backtesting via VectorBT (fast iteration) and Qlib (ML-oriented). LEAN as optional connector.

**Context**: External review suggested QuantConnect LEAN. Our roadmap includes multiple backtest engines.

**Reasoning**:
- VectorBT: Python-native, vectorized, 100x faster than event-driven for strategy iteration
- Qlib (Microsoft): AI-oriented, supports supervised learning + RL, perfect for ML signal research
- LEAN: C#-based, heavier to set up, but production-proven (300+ hedge funds)
- Our BaseBacktestEngine ABC allows all three via connectors — no lock-in

**Status**: Accepted. VectorBT (Week 2), Qlib (Week 8), LEAN (optional Week 12).

---

## ADR-004: Signal Decay Agent

**Decision**: Add Signal Decay measurement as a core capability (not just an agent).

**Context**: External review suggested a "Signal Decay Agent" — measuring how long an AI-derived signal remains profitable.

**Reasoning**:
- Signal decay is a first-class quant research concept, not just an agent feature
- Implement as: rolling Information Coefficient (IC) over time, half-life of IC, decay curve visualization
- This directly addresses a gap in Virat's ai-hedge-fund (no signal validation)
- Extremely demo-able at the meetup — "here's how long a CEO sentiment signal lasts"

**Status**: Accepted. Added to Week 6 (ML Signal Generation) roadmap.

---

## ADR-005: Native SEC EDGAR vs LlamaParse

**Decision**: Use our native EDGAR connector with XBRL parsing, not LlamaParse.

**Context**: External review suggested LlamaParse for unstructured SEC filings.

**Reasoning**:
- Our EdgarConnector already fetches and parses 10-K, 10-Q, 8-K filings directly from SEC
- XBRL parsing gives us structured financial data (revenue, net income, etc.) without LLM overhead
- For unstructured text analysis (management discussion, risk factors), we'll use Claude API directly
- LlamaParse adds a dependency and API cost for something we can do natively
- Our connector respects SEC's 10 req/s rate limit — LlamaParse would add another API to manage

**Status**: Accepted. Native EDGAR connector for structured data, Claude API for unstructured NLP.

---

## ADR-006: Project Positioning — "Agentic Alpha Lab"

**Decision**: Position the project as an "Agentic Alpha Lab" for the Singapore meetup.

**Context**: External review suggested this framing. The differentiator is "Statistically Validated Agentic Signals" — moving beyond LLM opinions to backtested, risk-managed investment signals.

**Key messaging**:
- Virat's ai-hedge-fund: viral proof-of-concept, LLM opinions over structured data
- Our platform: production-grade infrastructure with statistical validation, RAG over unstructured filings, proper backtesting
- Target audience: Singapore's institutional landscape (Point72, Citadel, GIC, Temasek)
- The "Claude Code" angle: demonstrate how AI-assisted development accelerates fintech prototyping

**Status**: Accepted. Update presentation section of ROADMAP.md.
