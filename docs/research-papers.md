# Essential Research Papers for Quant Researcher Credibility

## Tier 0: López de Prado's Latest (2025-2026) — Interview Gold

These are from [quantresearch.org](https://www.quantresearch.org/Publications.htm) — López de Prado's latest work at ADIA (Abu Dhabi Investment Authority). Mentioning these in an interview shows you're current.

| Paper | Year | Why It Matters | Link |
|-------|------|---------------|------|
| **Implementing AI Foundation Models in Asset Management: A Practical Guide** | 2025 | DIRECTLY relevant to Head of AI role. How funds actually implement LLMs. | [PM Research](https://www.pm-research.com/content/iijpormgmt/52/2/11) (paywall) |
| **Ten Applications of Financial Machine Learning** | 2025 | Practical ML applications for asset managers. | [SSRN](https://ssrn.com/abstract=3365271) (free) |
| **Why Has Factor Investing Failed? / Correcting the Factor Mirage** | 2026 | Specification errors in factor investing. Causal approach. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4697929) (free) |
| **How to Use the Sharpe Ratio: Inference, New Standard** | 2026 | Latest on Sharpe ratio methodology. 44-page definitive guide. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5520741) (free) |
| **The Three Types of Backtests** | 2024 | Enhanced backtesting for practitioners. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4897573) (free) |
| **Causal Factor Investing** | 2023 | Book: why correlation-based factors fail, causal approach. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4205613) (free) |
| **The 10 Reasons Most Machine Learning Funds Fail** | 2018 | THE paper on ML fund failures. Read before any interview. | [SSRN](https://ssrn.com/abstract=3104816) (free) |

## Tier 1: Must-Read (Implement at least 1-2 in Alpha Lab)

### ML for Cross-Sectional Returns
| Paper | Authors | Year | Why It Matters | PDF Link |
|-------|---------|------|---------------|----------|
| **Empirical Asset Pricing via Machine Learning** | Gu, Kelly & Xiu | 2020 | THE definitive paper on ML for stock returns. Neural nets + trees outperform. All methods agree on same dominant signals (momentum, liquidity, volatility). | [NBER PDF](https://www.nber.org/system/files/working_papers/w25398/w25398.pdf) |
| **Predicting Returns with Text Data** | Ke, Kelly & Xiu | 2019 | NLP signals predict cross-sectional returns. Shows text-derived features have genuine IC beyond traditional factors. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3389884) |
| **Deep Learning for Predicting Asset Returns** | Feng, He & Polson | 2018 | How deep learning maps to factor models. The bridge between ML and financial theory. | [arXiv](https://arxiv.org/abs/1804.09314) |

### Financial NLP / Transformers
| Paper | Authors | Year | Why It Matters | PDF Link |
|-------|---------|------|---------------|----------|
| **FinBERT: Financial Sentiment Analysis with Pre-Trained Language Models** | Araci | 2019 | BERT fine-tuned on financial text. State-of-the-art sentiment classification. | [arXiv](https://arxiv.org/abs/1908.10063) |
| **FinBERT: A Pretrained Language Model for Financial Communications** | Yang, Huang & Wang | 2020 | Alternative FinBERT trained on larger financial corpus. | [arXiv](https://arxiv.org/abs/2006.08097) |
| **BloombergGPT: A Large Language Model for Finance** | Wu et al. | 2023 | How Bloomberg built a finance-specific LLM. Architecture decisions, training data. | [arXiv](https://arxiv.org/abs/2303.17564) |
| **Can ChatGPT Forecast Stock Price Movements?** | Lopez-Lira & Tang | 2023 | GPT sentiment predicts returns even after controlling for traditional factors. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4412788) |

### Quant Research Methodology
| Paper | Authors | Year | Why It Matters | PDF Link |
|-------|---------|------|---------------|----------|
| **The Deflated Sharpe Ratio** | Bailey & López de Prado | 2014 | How to adjust Sharpe for multiple testing. Prevents backtest overfitting. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) |
| **... and the Cross-Section of Expected Returns** | Harvey, Liu & Zhu | 2016 | 300+ published factors, most are false discoveries. The multiple testing crisis. | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314) |
| **Does Academic Research Destroy Stock Return Predictability?** | McLean & Pontiff | 2016 | Anomalies decay ~50% after publication. Signal decay is real. | [Journal of Finance](https://doi.org/10.1111/jofi.12365) |

## Tier 2: Important Context

### Factor Models & Anomalies
| Paper | Authors | Year | PDF Link |
|-------|---------|------|----------|
| **Common Risk Factors in the Returns on Stocks and Bonds** | Fama & French | 1993 | [Journal of Financial Economics](https://doi.org/10.1016/0304-405X(93)90023-5) |
| **Returns to Buying Winners and Selling Losers** | Jegadeesh & Titman | 1993 | [Journal of Finance](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x) |
| **Value and Momentum Everywhere** | Asness, Moskowitz & Pedersen | 2013 | [Journal of Finance](https://doi.org/10.1111/jofi.12021) |
| **A Five-Factor Asset Pricing Model** | Fama & French | 2015 | [Journal of Financial Economics](https://doi.org/10.1016/j.jfineco.2014.10.010) |
| **The Gross Profitability Premium** | Novy-Marx | 2013 | [Journal of Financial Economics](https://doi.org/10.1016/j.jfineco.2013.01.003) |
| **Dissecting Anomalies with a Five-Factor Model** | Fama & French | 2016 | [Review of Financial Studies](https://doi.org/10.1093/rfs/hhv043) |

### Market Microstructure
| Paper | Authors | Year | PDF Link |
|-------|---------|------|----------|
| **Optimal Execution of Portfolio Transactions** | Almgren & Chriss | 2001 | [Journal of Risk](https://www.smallake.kr/wp-content/uploads/2016/03/optmagmagmagexecution.pdf) |
| **Flow Toxicity and Liquidity (VPIN)** | Easley, López de Prado & O'Hara | 2012 | [Review of Financial Studies](https://doi.org/10.1093/rfs/hhs053) |

### Portfolio Construction
| Paper | Authors | Year | PDF Link |
|-------|---------|------|----------|
| **Building Diversified Portfolios that Outperform OOS** | López de Prado | 2016 | [Journal of Portfolio Management](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2708678) |
| **A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices** | Ledoit & Wolf | 2004 | [Journal of Multivariate Analysis](https://doi.org/10.1016/S0047-259X(03)00096-4) |

## Papers to Implement in Alpha Lab

### Priority 1: FinBERT Signal Pipeline
**Paper**: Araci (2019) + Yang et al. (2020)
**Implementation**: Fine-tune FinBERT on earnings calls → generate sentiment signals → backtest → measure IC decay → factor attribution

### Priority 2: ML Cross-Sectional Returns
**Paper**: Gu, Kelly & Xiu (2020)
**Implementation**: Tree-based models (XGBoost) for cross-sectional return prediction → compare with neural net → measure which features dominate → validate with deflated Sharpe
