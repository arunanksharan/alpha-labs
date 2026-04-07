"""Tests for the research report generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from research.reports.generator import ResearchReport, ResearchReportGenerator


@pytest.fixture
def generator() -> ResearchReportGenerator:
    return ResearchReportGenerator(template_style="dark")


@pytest.fixture
def sample_analysis() -> dict:
    return {
        "sentiment": {
            "score": 0.05,
            "magnitude": 0.12,
            "label": "bullish",
            "key_phrases": ["strong profit growth", "exceeded expectations"],
        },
        "signals": [
            {"date": "2024-06-01", "direction": 1.0, "confidence": 0.8, "rationale": "bullish sentiment"},
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_returns_report(
    generator: ResearchReportGenerator, sample_analysis: dict
) -> None:
    report = generator.generate("AAPL", sample_analysis)
    assert isinstance(report, ResearchReport)
    assert report.ticker == "AAPL"
    assert report.title == "AAPL Research Report"
    assert report.date  # non-empty


def test_report_has_html(
    generator: ResearchReportGenerator, sample_analysis: dict
) -> None:
    report = generator.generate("AAPL", sample_analysis)
    assert report.html
    assert "<!DOCTYPE html>" in report.html


def test_report_html_contains_ticker(
    generator: ResearchReportGenerator, sample_analysis: dict
) -> None:
    report = generator.generate("MSFT", sample_analysis)
    assert "MSFT" in report.html


def test_save_creates_file(
    generator: ResearchReportGenerator, sample_analysis: dict, tmp_path: Path
) -> None:
    report = generator.generate("GOOG", sample_analysis)
    out = tmp_path / "report.html"
    generator.save(report, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "GOOG" in content
    assert "<!DOCTYPE html>" in content


def test_dark_theme_in_html(
    generator: ResearchReportGenerator, sample_analysis: dict
) -> None:
    report = generator.generate("AAPL", sample_analysis)
    # Verify Avashi dark design system colours
    assert "#111827" in report.html  # background
    assert "#f9fafb" in report.html  # text
    assert "#8b5cf6" in report.html  # violet accent


def test_handles_partial_analysis(generator: ResearchReportGenerator) -> None:
    """Report should generate even when only sentiment data is provided."""
    partial = {
        "sentiment": {
            "score": -0.03,
            "magnitude": 0.08,
            "label": "bearish",
            "key_phrases": ["decline in revenue"],
        },
    }
    report = generator.generate("NFLX", partial)
    assert isinstance(report, ResearchReport)
    assert report.html
    assert "Sentiment Analysis" in report.html
    # Factor / backtest sections should not appear
    assert "Factor Exposure" not in report.html
    assert "Backtest Results" not in report.html
