# Head of AI — Global Fund (Singapore) Interview Preparation Roadmap

## The JD Decoded

Before building a curriculum, let me break down what they're actually asking for vs what they wrote.

### What the JD says → What it actually means

| JD Language | Real Meaning |
|---|---|
| "AI-powered alter ego of its investment team" | Codify how their PMs think into ML models. Not replace them — augment and scale their judgment. |
| "Learn from decades of investment expertise" | Historical trade data + PM decision rationale → train models that predict what the PM would do. This is **imitation learning / decision cloning**. |
| "Explainable investment recommendations" | XAI is non-negotiable. Black-box models won't fly. SHAP, LIME, attention visualization, decision trees as interpretation layer. |
| "Greenfield buildout" | No existing system. You design everything. They want an architect, not an optimizer. |
| "Sits on senior leadership committee" | You need to speak business, not just tech. Translate "we retrained the transformer with attention on macro features" into "the system now weighs interest rate changes more heavily when making recommendations, which improved hit rate by 8%." |
| "Partner with portfolio managers" | The hardest part of the job. PMs are opinionated, skeptical of AI, and protective of their alpha. You need to earn trust by speaking their language. |
| "Buy vs build" | They want someone who won't reinvent the wheel. Know when Bloomberg data is enough vs when you need custom pipelines. When OpenAI is fine vs when you need fine-tuned models. |
| "10+ years data-intensive technology" | They'll flex on this for the right candidate. What they really want is evidence you've built systems at scale that worked. |
| "NLP transformer architectures" | They're going to process filings, earnings calls, news, research reports. You need to understand FinBERT, LLM fine-tuning, and RAG at production scale. |
| "Investment intuition" | Can you look at a set of signals and say "this doesn't smell right" without running a backtest? This comes from understanding markets, not just data. |

### Gap Analysis: Your Profile vs JD

| JD Requirement | Your Current Level | Gap | Priority |
|---|---|---|---|
| AI system architecture | Strong (RAG, multi-agent, enterprise) | Reframe for finance context | LOW |
| Python + ML ecosystem | Strong (production FastAPI, LangGraph) | Need PyTorch/transformer depth | MEDIUM |
| NLP transformers | Good (RAG, sentiment) | Need fine-tuning, FinBERT, attention mechanisms | MEDIUM |
| Large-scale data/cloud | Strong (enterprise platforms) | Need to articulate financial data scale | LOW |
| Financial markets understanding | Building (this project) | Need deeper: portfolio construction theory, market microstructure, PM decision frameworks | HIGH |
| Quant research / hedge fund experience | No direct experience | This is the biggest gap. Mitigate with the Alpha Lab project + demonstrated knowledge | HIGH |
| Senior leadership / C-suite communication | Strong (founder, client-facing) | Reframe for fund context | LOW |
| Team building | Strong (Kuzushi Labs) | Already demonstrated | LOW |
| Buy vs build judgment | Strong (architecture experience) | Need finance-specific vendor knowledge (Bloomberg, Refinitiv, FactSet) | MEDIUM |

---

## The 2-Month Roadmap

### Guiding Principles

1. **You learn by building.** Every topic has a "build this" component tied to the Alpha Lab project.
2. **Interview signal > academic depth.** You need to demonstrate fluency, not prove a PhD.
3. **The project IS the preparation.** The Alpha Lab is your portfolio piece. Every topic you study should improve it.
4. **Prioritize the gaps.** Don't spend time on things you already know (system architecture, team building). Spend time on what you don't (financial markets, PM decision frameworks, transformer fine-tuning).

### Time Budget: 8 weeks × 3-4 hours/day = ~200 hours

---

## Part 1: Financial Markets Fluency (Weeks 1-2)

**Goal**: Speak the language of PMs and investment professionals. Understand how they think, what they care about, and why they're skeptical of AI.

This is your biggest gap and the most important thing to fix. Everything else is technical — this is cultural.

### Week 1: How Investment Professionals Think

**Core concept**: A PM's job is to have a **view** (thesis) on a security, construct a **portfolio** that expresses that view, and manage the **risk** of being wrong. AI's job is to make each step faster, more rigorous, and more consistent.

#### Reading

| Resource | What You'll Learn | Time |
|---|---|---|
| **"More Than You Know" — Michael Mauboussin** | How investment professionals actually make decisions. Mental models, behavioral biases, probabilistic thinking. This is the book PMs read. | 6 hrs |
| **"The Man Who Solved the Market" — Gregory Zuckerman** | How Renaissance Technologies (the most successful quant fund) works. Culture, approach, what makes quant research different from traditional investing. | 8 hrs |
| **AQR Research Papers** (free at aqr.com): "Value and Momentum Everywhere", "A Century of Evidence on Trend-Following" | How institutional quant research is published. The writing style, the rigor expected, how factors are tested. | 4 hrs |

#### YouTube

| Video | Why Watch |
|---|---|
| **Patrick Boyle — "What Do Quant Researchers Actually Do?"** | Former hedge fund manager explains the daily reality |
| **Marcos López de Prado — "The 7 Reasons Most ML Funds Fail"** | The traps you need to avoid. Every interviewer will test whether you know these. |
| **Two Sigma — "Hal: How Our Data Scientists Apply ML"** | How a top quant fund actually uses ML in practice |

#### Build (in the Alpha Lab)
- Add a `docs/investment-thesis.md` that documents how a PM for a global macro fund would think about NVDA — not as a quant, but as a fundamental investor. What's the thesis? What would change their mind? What's the risk?
- This exercise forces you to think like the PMs you'll be partnering with.

### Week 2: Portfolio Construction & Risk

**Core concept**: Individual signals don't matter — **portfolios** matter. A PM cares about "how does this trade affect my portfolio?" not "is this stock cheap?"

#### Reading

| Resource | What You'll Learn | Time |
|---|---|---|
| **"Active Portfolio Management" — Grinold & Kahn, Ch. 1-6** | The fundamental law of active management: IR = IC × √BR. This is the quantitative framework for investment skill. Every quant fund thinks in these terms. | 10 hrs |
| **"Advances in Financial Machine Learning" — López de Prado, Ch. 1-4** | Why ML in finance is different from ML in tech. Overfit detection, purged CV, the scientific method applied to investment. | 8 hrs |
| **"Quantitative Trading" — Ernie Chan, Ch. 1-5** | Practical quant strategy building. Gets you from theory to implementation. | 6 hrs |

#### Key Concepts to Master

| Concept | Why It Matters for the Interview |
|---|---|
| **Information Ratio (IR)** | The single most important metric for a PM. IR = alpha / tracking error. You MUST be able to explain this. |
| **Fundamental Law: IR = IC × √BR** | IC = information coefficient (skill per bet), BR = breadth (number of independent bets). The interviewer will ask: "How do you improve a strategy?" Answer: increase IC (better signals) or BR (more independent bets). |
| **Factor investing** | Most institutional capital is allocated through factor lenses (value, momentum, quality, low vol). You need to know what these are and how they interact. |
| **Drawdown vs volatility** | PMs care more about drawdowns than volatility. A 20% drawdown is a career-ending event. Understanding this shapes every design decision. |

#### Build
- Run the Alpha Lab's factor model on a 5-stock portfolio. Decompose returns into market, value, momentum, and residual. Write up the results as if presenting to a PM.

---

## Part 2: ML for Finance — What Actually Works (Weeks 3-4)

**Goal**: Understand which ML techniques work in finance and why most don't. This is where you bridge your existing ML knowledge with financial applications.

### Week 3: Why Finance ML Is Different

**Core concept**: Financial data violates almost every assumption of standard ML — it's non-stationary, noisy, has regime changes, and the signal-to-noise ratio is extremely low. The techniques that work in computer vision don't work here.

#### Reading

| Resource | What You'll Learn | Time |
|---|---|---|
| **López de Prado — "Advances in Financial ML", Ch. 5-10** | Triple barrier labeling, meta-labeling, purged cross-validation, feature importance. This is the bible. | 12 hrs |
| **"Machine Learning for Asset Managers" — López de Prado** (short book, 150 pages) | Clustering, distance metrics for financial data, portfolio construction with ML. Written for PMs, not engineers. | 5 hrs |
| **Stefan Jansen — "Machine Learning for Algorithmic Trading", Ch. 1-8** | Practical implementations: factor models, NLP for trading, deep learning for time series. | 10 hrs |

#### Research Papers

| Paper | Why It Matters |
|---|---|
| **"Empirical Asset Pricing via Machine Learning" — Gu, Kelly, Xiu (2020)** | The definitive paper on ML for cross-sectional stock prediction. Uses neural nets, random forests, gradient boosting. Shows what works. |
| **"Deep Learning for Predicting Asset Returns" — Feng, He, Polson (2018)** | How deep learning maps to factor models. The bridge between ML and financial theory. |
| **"The Cross-Section of Expected Returns: A New Approach" — Kozak, Nagel, Santosh (2020)** | How shrinkage and regularization improve factor portfolios. The statistical foundation. |

#### Key Interview Concepts

| Concept | One-Sentence Answer |
|---|---|
| "Why does standard cross-validation fail in finance?" | Because financial data is serially correlated — future data leaks into training folds. You must use purged K-fold or walk-forward validation. |
| "What's the biggest risk in financial ML?" | Overfitting to noise. A Sharpe of 2.0 across 1000 backtested strategies will have at least one that looks great by chance. Use deflated Sharpe ratio. |
| "How do you handle non-stationarity?" | Rolling windows, regime detection, and adaptive models. Don't train on 20 years of data as if it's one regime. |
| "What's meta-labeling?" | Separate the question "which direction?" from "how much?" Train a primary model for direction, a secondary model for position sizing. |

#### Build
- Implement a walk-forward ML pipeline in the Alpha Lab: train XGBoost on rolling 2-year windows, test on 1-quarter forward, track IC decay over time. Document whether the signal is real or overfitted.

### Week 4: NLP and Transformers for Finance

**Core concept**: The JD specifically mentions "NLP systems" and "transformer architectures." The fund wants to process filings, earnings calls, news, and research reports. This is where your RAG experience becomes directly relevant.

#### Reading

| Resource | What You'll Learn | Time |
|---|---|---|
| **"Natural Language Processing with Transformers" — Tunstall, von Werra, Wolf** | End-to-end transformer understanding: attention, BERT, fine-tuning, deployment. | 10 hrs |
| **Hugging Face Course** (free, huggingface.co/course) | Hands-on: tokenization, fine-tuning, inference. Focus on Ch. 1-4 and 7 (token classification). | 6 hrs |
| **"Attention Is All You Need" — Vaswani et al. (2017)** | Read the original paper. Understand self-attention, multi-head attention, positional encoding. Interviewers will ask about this. | 3 hrs |

#### Finance-Specific NLP

| Resource | What You'll Learn |
|---|---|
| **FinBERT paper — Araci (2019)** | BERT fine-tuned on financial text. Understands that "profit warning" is negative, "exceeds guidance" is positive. |
| **"When Do NLP Models Learn Signal?" — McLean & Pontiff (2016)** | Not an NLP paper, but explains why textual signals decay — once published, the alpha gets traded away. |
| **BloombergGPT paper — Wu et al. (2023)** | How Bloomberg built a finance-specific LLM. Architecture decisions, training data, evaluation. |
| **SEC EDGAR research** — any paper using 10-K/10-Q text for prediction | Understand the pipeline: filing → extraction → embedding → signal |

#### Key Interview Concepts

| Concept | Why It Matters |
|---|---|
| **Fine-tuning vs RAG vs prompting** | Know when each is appropriate. Fine-tuning: domain adaptation. RAG: knowledge retrieval. Prompting: quick prototyping. The fund will likely use all three. |
| **Attention mechanisms** | Be able to explain self-attention at a whiteboard. "Each token attends to every other token with learned weights, allowing the model to capture long-range dependencies." |
| **Embeddings for financial documents** | How to embed 10-K filings (chunk → embed → store). Your RAG experience is directly applicable — frame it. |
| **Explainability in NLP** | Attention weights as explanation. LIME/SHAP for text. The fund needs explainable signals — not just "the model says bullish." |

#### Build
- Fine-tune a sentiment model on financial text using the Alpha Lab's sentiment analyzer. Compare FinBERT vs your Loughran-McDonald approach vs a fine-tuned model. Document the results.

---

## Part 3: System Architecture & Leadership (Weeks 5-6)

**Goal**: Demonstrate you can architect a system from scratch and lead a team. This is where your existing strengths shine — but you need to frame them for a fund context.

### Week 5: AI System Architecture for Finance

**Core concept**: The JD says "end-to-end architecture and technical strategy." They want someone who can design the ENTIRE system — data ingestion, feature engineering, model training, inference, monitoring, and human feedback loops.

#### Reading

| Resource | What You'll Learn | Time |
|---|---|---|
| **"Designing Machine Learning Systems" — Chip Huyen** | Production ML systems: data pipelines, feature stores, model serving, monitoring, feedback loops. The engineering side of ML. | 8 hrs |
| **"Machine Learning System Design Interview" — Ali Aminian & Alex Xu** | How to structure ML system design answers. This is the format they'll expect. | 6 hrs |
| **MLOps: Continuous delivery for ML** (Google's MLOps whitepaper) | How Google structures ML systems. Feature stores, model registries, A/B testing. | 3 hrs |

#### Key Architecture Patterns

| Pattern | Application to This Role |
|---|---|
| **Feature Store** | Centralized feature computation for all models. You built this in Week 5 of the Alpha Lab. |
| **Model Registry** | Version all models, track performance over time, enable rollback. |
| **Human-in-the-Loop** | PM feedback as training signal. Your approval gate design in the Alpha Lab is directly relevant. |
| **Explainability Layer** | Every model output must come with an explanation. SHAP values, attention maps, decision tree distillation. |
| **Monitoring & Drift Detection** | Models degrade as markets change. Signal decay monitoring is essential — you built this. |

#### Build
- Draw the complete architecture for the "AI alter ego" system described in the JD. Include: data sources, feature pipelines, model training, inference, PM interaction layer, feedback loops, and monitoring. This becomes your interview artifact.

### Week 6: Leadership & Communication

**Core concept**: This role "sits on the senior leadership committee and engages with all C-suite." You need to demonstrate you can translate between technical and business languages.

#### Reading

| Resource | What You'll Learn | Time |
|---|---|---|
| **"The Manager's Path" — Camille Fournier** | Engineering leadership: hiring, mentoring, managing up. Focus on chapters about building teams from scratch. | 6 hrs |
| **"Radical Candor" — Kim Scott** | How to give feedback and build trust with senior stakeholders (PMs). | 4 hrs |
| **"An Elegant Puzzle" — Will Larson** | Systems thinking for engineering organizations. How to structure a small, high-caliber team. | 4 hrs |

#### Key Interview Topics

| Topic | How to Answer |
|---|---|
| "How would you hire the first 3 people?" | Quant researcher (PhD in stats/ML + finance), ML engineer (production systems), data engineer (pipelines). Hire for complementary skills, not clones. |
| "How do you manage PM expectations?" | Weekly syncs, shared dashboards, start with quick wins (automate their report generation), then build trust for bigger projects. |
| "Buy vs build?" | Data: buy (Bloomberg, Refinitiv). Infrastructure: buy (AWS/GCP). Models: build (your alpha IS the model). Tooling: mix (Databricks for pipelines, custom for inference). |
| "How do you measure success?" | Short-term: PM adoption rate, signal IC. Medium-term: strategy performance attribution to AI signals. Long-term: fund alpha attributable to the platform. |

#### Build
- Write a "First 90 Days Plan" document for this role. What would you do in the first week? First month? First quarter? This is a common interview ask.

---

## Part 4: Deep Dives & Mock Interviews (Weeks 7-8)

**Goal**: Fill remaining gaps and practice interview delivery. At this point you should have breadth — now go deep on the topics most likely to come up.

### Week 7: Technical Deep Dives

Pick 3 of these based on what you feel weakest on:

#### Deep Dive A: PyTorch & Model Training

| Resource | What You'll Learn | Time |
|---|---|---|
| **"Deep Learning with PyTorch" — Stevens, Antiga, Viehmann** | Tensors, autograd, training loops, CNNs, RNNs, attention. Focus Ch. 1-8. | 10 hrs |
| **Fast.ai Course Part 2** (course.fast.ai) | Implementing models from scratch. The "hacker's guide" to deep learning. | 8 hrs |

Build: Implement a simple LSTM for stock return prediction. Show that it doesn't work (it shouldn't). Explain why. Then show how feature engineering + XGBoost outperforms it. This demonstrates you understand when deep learning is and isn't appropriate for finance.

#### Deep Dive B: Explainable AI (XAI)

| Resource | What You'll Learn | Time |
|---|---|---|
| **"Interpretable Machine Learning" — Christoph Molnar** (free online) | SHAP, LIME, partial dependence, feature interactions. The complete toolkit. | 8 hrs |
| **SHAP documentation** (shap.readthedocs.io) | How to use SHAP with tree models and deep learning. | 3 hrs |

Build: Add SHAP explanations to the Alpha Lab's ML signal generator. For each signal, show which features contributed most to the prediction. "NVDA is bullish because: momentum (40% contribution), sentiment (30%), fundamental (20%), macro (10%)."

#### Deep Dive C: Time Series & Regime Detection

| Resource | What You'll Learn | Time |
|---|---|---|
| **"Analysis of Financial Time Series" — Ruey Tsay, Ch. 1-5** | ARIMA, GARCH, volatility modeling. The classical approach. | 10 hrs |
| **Hidden Markov Models for regime detection** — any tutorial + Hamilton (1989) paper | How to detect bull/bear market regimes. Critical for adaptive strategies. | 5 hrs |

Build: Implement regime-aware strategy switching in the Alpha Lab — mean reversion in range-bound markets, momentum in trending markets. Show the combined performance vs individual strategies.

#### Deep Dive D: Cloud Architecture & MLOps

| Resource | What You'll Learn | Time |
|---|---|---|
| **AWS ML Specialty certification materials** | SageMaker, feature store, model endpoints, monitoring. The full AWS ML stack. | 10 hrs |
| **Databricks Lakehouse for Financial Services** (whitepaper) | How financial firms use Databricks for ML pipelines. Common in hedge funds. | 3 hrs |

Build: Write a deployment architecture document for the Alpha Lab on AWS — what goes where, how it scales, what the costs look like.

### Week 8: Mock Interviews & Polishing

#### Practice These Questions

**System Design (45 min each)**
1. "Design an AI system that learns from portfolio managers' past trades and generates recommendations in their style."
2. "How would you build a real-time news processing pipeline that generates trading signals?"
3. "Design a feature store for a multi-strategy hedge fund."

**Technical (30 min each)**
4. "Walk me through how you'd detect if a trading signal is overfitted."
5. "Explain the attention mechanism in transformers. How would you use it for financial document analysis?"
6. "What's the fundamental law of active management? How does it guide AI system design?"

**Leadership (20 min each)**
7. "You've built a model that shows 2x Sharpe improvement. The PM doesn't trust it. What do you do?"
8. "How would you structure a team of 5 to build this system?"
9. "It's 6 months in and the PM adoption is low. Diagnose and fix."

**Behavioral (15 min each)**
10. "Tell me about a system you built from scratch. What were the hardest decisions?"
11. "Tell me about a time you had to explain a technical concept to a non-technical stakeholder."
12. "What's your approach to 'buy vs build'? Give an example."

#### Your Key Talking Points (Memorize These)

| When They Ask... | Your Answer Framework |
|---|---|
| "Why you?" | "I've built production AI systems that combine multiple data sources, multi-agent orchestration, and real-time decision-making. The Alpha Lab is my proof — 35K lines of tested quant research infrastructure with 9 specialist agents that produce validated, explainable signals. I combine engineering rigor with financial understanding." |
| "What's your investment philosophy?" | "Signals should be grounded in computation, validated against history, and explainable to a human. I believe in the Grinold-Kahn framework: improve IC through better features and models, improve breadth through cross-asset coverage, and manage risk through factor-aware portfolio construction." |
| "How would you start this project?" | "Week 1: interviews with every PM to understand their decision process. Month 1: data audit and pipeline architecture. Month 2: first model — probably a simple factor model that replicates PM style on historical trades. Month 3: feedback loop, PM review, iteration. Don't try to beat the PM in month 1 — first prove you can mirror them." |

---

## Weekly Schedule

| Week | Focus | Hours | Primary Activity |
|---|---|---|---|
| 1 | Investment thinking | 20 | Read Mauboussin + Zuckerman, write investment thesis |
| 2 | Portfolio construction | 20 | Read Grinold-Kahn + Chan, run factor model |
| 3 | Financial ML | 25 | Read López de Prado, build walk-forward pipeline |
| 4 | NLP + Transformers | 25 | Read transformers book, fine-tune FinBERT |
| 5 | System architecture | 20 | Read Chip Huyen, design the "alter ego" architecture |
| 6 | Leadership + communication | 15 | Read Manager's Path, write First 90 Days plan |
| 7 | Deep dives (pick 2) | 25 | PyTorch/XAI/Time Series/Cloud |
| 8 | Mock interviews | 20 | Practice system design + technical + behavioral |
| **Total** | | **170 hrs** | |

---

## The Meta-Strategy: Your Interview Narrative

The interview is not about proving you know everything. It's about proving three things:

### 1. You understand finance (not just tech)
Evidence: You can discuss IR, factor models, PM decision frameworks, and why most ML approaches fail in finance. You've read Grinold-Kahn and López de Prado. You can explain drawdown risk vs volatility risk.

### 2. You can build from scratch
Evidence: The Alpha Lab — 35K lines, 9 agents, tested infrastructure, working dashboard. You designed the architecture, the data pipelines, the agent system, and the validation framework. From zero to production in weeks.

### 3. You can partner with investors
Evidence: Your approach starts with PM interviews, not model training. You speak their language (IR, IC, factor exposure) not just engineer language (RMSE, F1, accuracy). You understand that PM trust is earned through quick wins and explainability, not model performance claims.

The person they hire won't be the one who knows the most about transformers. It will be the one who can sit in a room with a PM, understand their investment process, and say: "I can build a system that codifies how you think, validates it against history, and scales it across your entire portfolio. Here's how."

That person is you.
