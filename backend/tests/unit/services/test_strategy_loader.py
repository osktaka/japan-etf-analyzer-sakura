"""Tests for StrategyLoader."""
from __future__ import annotations

from datetime import date

import pytest

from src.services.strategy_loader import (
    BuyAction,
    SellAction,
    StrategyLoader,
    TargetHolding,
)


VALID_FRONTMATTER = """---
revision: 2026-04-29
owner: test
benchmark: ^N225
review_frequency: weekly_friday

target_allocation:
  core: 0.65
  theme: 0.25
  cash: 0.10

target_holdings:
  core:
    - { code: "2559", name: "MAXIS全世界株", weight: 0.35 }
    - { code: "1306", name: "NF TOPIX", weight: 0.30 }
  theme:
    - { code: "200A", name: "NF日経半導体", weight: 0.25 }

sell_schedule:
  - { date: "2026-05-07", code: "1540", name: "純金", quantity: 10, action: "all", reason: "金過剰" }

buy_dca_schedule:
  - { date: "2026-05-20", code: "2559", quantity: 3 }
  - { date: "2026-05-20", code: "1306", quantity: 8 }

mechanical_rules:
  min_holding_months: 6
  loss_cut_pct: -20.0
  take_profit_pct: [50.0, 100.0]
  n225_drawdown_trigger_pct: -5.0
  n225_drawdown_basis: "previous_close"
  n225_dca_lookback_days: 10
  alpha_deviation_threshold_pp: 10.0
  rebalance_threshold_pct: 5.0
  rebalance_check_basis: "close"
---

# 戦略書本文
案1B戦略を採用する。
"""


class TestStrategyLoaderLoads:
    def test_loads_valid_frontmatter(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert s.revision == date(2026, 4, 29)
        assert s.owner == "test"
        assert s.benchmark == "^N225"
        assert s.review_frequency == "weekly_friday"
        assert s.target_allocation["core"] == 0.65
        assert s.target_allocation["theme"] == 0.25
        assert s.target_allocation["cash"] == 0.10
        assert "案1B戦略を採用する" in s.body_markdown

    def test_target_holdings_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.target_holdings_core) == 2
        assert len(s.target_holdings_theme) == 1
        assert s.target_holdings_core[0] == TargetHolding(
            code="2559", name="MAXIS全世界株", weight=0.35
        )

    def test_sell_schedule_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.sell_schedule) == 1
        sell = s.sell_schedule[0]
        assert sell.date == date(2026, 5, 7)
        assert sell.code == "1540"
        assert sell.quantity == 10
        assert sell.action == "all"

    def test_buy_dca_schedule_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.buy_dca_schedule) == 2
        assert s.buy_dca_schedule[0] == BuyAction(
            date=date(2026, 5, 20), code="2559", quantity=3
        )

    def test_mechanical_rules_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        r = s.mechanical_rules
        assert r.min_holding_months == 6
        assert r.loss_cut_pct == -20.0
        assert r.take_profit_pct == (50.0, 100.0)
        assert r.n225_drawdown_trigger_pct == -5.0
        assert r.n225_drawdown_basis == "previous_close"
        assert r.alpha_deviation_threshold_pp == 10.0

    def test_get_sells_on(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.get_sells_on(date(2026, 5, 7))) == 1
        assert len(s.get_sells_on(date(2026, 5, 8))) == 0

    def test_get_buys_on(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.get_buys_on(date(2026, 5, 20))) == 2
        assert len(s.get_buys_on(date(2026, 5, 21))) == 0

    def test_all_target_holdings(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.all_target_holdings()) == 3


class TestStrategyLoaderInvalid:
    def test_no_frontmatter(self):
        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            StrategyLoader.loads("# 本文だけ")

    def test_unclosed_frontmatter(self):
        with pytest.raises(ValueError, match="not properly closed"):
            StrategyLoader.loads("---\nrevision: 2026-04-29\n")

    def test_invalid_yaml(self):
        text = "---\nrevision: [unclosed\n---\n"
        with pytest.raises(ValueError, match="Invalid YAML"):
            StrategyLoader.loads(text)

    def test_missing_required_keys(self):
        text = "---\nrevision: 2026-04-29\nowner: test\n---\n本文"
        with pytest.raises(ValueError, match="missing required keys"):
            StrategyLoader.loads(text)

    def test_invalid_date_format(self):
        bad = VALID_FRONTMATTER.replace(
            "revision: 2026-04-29", 'revision: "not-a-date"'
        )
        with pytest.raises(ValueError, match="Invalid date format"):
            StrategyLoader.loads(bad)

    def test_target_holdings_missing_field(self):
        bad = VALID_FRONTMATTER.replace(
            '- { code: "2559", name: "MAXIS全世界株", weight: 0.35 }',
            '- { code: "2559", weight: 0.35 }',
        )
        with pytest.raises(ValueError, match="target_holdings item missing"):
            StrategyLoader.loads(bad)

    def test_take_profit_must_be_list(self):
        bad = VALID_FRONTMATTER.replace(
            "take_profit_pct: [50.0, 100.0]", "take_profit_pct: 50.0"
        )
        with pytest.raises(ValueError, match="must be non-empty list"):
            StrategyLoader.loads(bad)

    def test_mechanical_rules_missing(self):
        bad = VALID_FRONTMATTER.replace("min_holding_months: 6", "")
        with pytest.raises(ValueError, match="mechanical_rules missing keys"):
            StrategyLoader.loads(bad)


class TestStrategyLoaderFile:
    def test_load_from_real_strategy_file(self):
        """docs/12_personal_strategy.md を実ファイルとしてロード."""
        from pathlib import Path

        strategy_path = (
            Path(__file__).resolve().parents[4]
            / "docs"
            / "12_personal_strategy.md"
        )
        if not strategy_path.exists():
            pytest.skip(f"Strategy file not found: {strategy_path}")
        s = StrategyLoader.load(strategy_path)
        assert s.benchmark == "^N225"
        assert s.target_allocation["core"] == 0.65
        assert len(s.sell_schedule) >= 1
        assert len(s.buy_dca_schedule) >= 1

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            StrategyLoader.load(tmp_path / "nonexistent.md")
