"""Tests for StrategyLoader."""
from __future__ import annotations

from datetime import date

import pytest

from src.services.strategy_loader import (
    BucketDef,
    StrategyLoader,
    TargetHolding,
)


VALID_FRONTMATTER = """---
revision: 2026-05-14
owner: test
benchmark: ^N225
review_frequency: weekly_friday

target_buckets:
  group_a: { label_ja: "A群（コア・逆相関）", weight_pct: 45.00 }
  group_b: { label_ja: "B群（日本株テーマ）", weight_pct: 45.00 }
  cash:    { label_ja: "現金",              weight_pct: 10.00 }

target_holdings:
  - { code: "2559", name: "オルカン",       bucket: "group_a", weight_pct: 15.00 }
  - { code: "1540", name: "純金",           bucket: "group_a", weight_pct: 15.00 }
  - { code: "200A", name: "半導体",         bucket: "group_a", weight_pct: 15.00 }
  - { code: "1306", name: "TOPIX",          bucket: "group_b", weight_pct:  9.00 }
  - { code: "1629", name: "商社",           bucket: "group_b", weight_pct:  9.00 }
  - { code: "1615", name: "銀行",           bucket: "group_b", weight_pct:  9.00 }
  - { code: "2646", name: "メタル",         bucket: "group_b", weight_pct:  9.00 }
  - { code: "1618", name: "エネルギー資源", bucket: "group_b", weight_pct:  9.00 }

mechanical_rules:
  min_holding_months: 6
  loss_cut_pct: -20.0
  take_profit_pct: [50.0, 100.0]
  n225_drawdown_trigger_pct: -5.0
  n225_drawdown_basis: previous_close
  n225_dca_lookback_days: 10
  alpha_deviation_threshold_pp: 10.0
  drift_ok_pp: 3.0
  drift_warn_pp: 5.0
  rebalance_check_basis: close
---

# 戦略書本文
A群/B群モデルを採用する。
"""


class TestStrategyLoaderLoads:
    def test_loads_valid_frontmatter(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert s.revision == date(2026, 5, 14)
        assert s.owner == "test"
        assert s.benchmark == "^N225"
        assert s.review_frequency == "weekly_friday"
        assert "A群/B群モデルを採用する" in s.body_markdown

    def test_target_buckets_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert set(s.target_buckets.keys()) == {"group_a", "group_b", "cash"}
        assert s.target_buckets["group_a"] == BucketDef(
            code="group_a", label_ja="A群（コア・逆相関）", weight_pct=45.0
        )
        assert s.target_buckets["group_b"].weight_pct == 45.0
        assert s.target_buckets["cash"].weight_pct == 10.0

    def test_target_holdings_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.target_holdings) == 8
        h0 = s.target_holdings[0]
        assert h0 == TargetHolding(
            code="2559", name="オルカン", bucket="group_a", weight_pct=15.0
        )
        # bucket フィールドが正しく分類されている
        group_a = [h for h in s.target_holdings if h.bucket == "group_a"]
        group_b = [h for h in s.target_holdings if h.bucket == "group_b"]
        assert len(group_a) == 3
        assert len(group_b) == 5

    def test_holdings_by_bucket(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        assert len(s.holdings_by_bucket("group_a")) == 3
        assert len(s.holdings_by_bucket("group_b")) == 5
        assert len(s.holdings_by_bucket("cash")) == 0

    def test_mechanical_rules_parsed(self):
        s = StrategyLoader.loads(VALID_FRONTMATTER)
        r = s.mechanical_rules
        assert r.min_holding_months == 6
        assert r.loss_cut_pct == -20.0
        assert r.take_profit_pct == (50.0, 100.0)
        assert r.n225_drawdown_trigger_pct == -5.0
        assert r.n225_drawdown_basis == "previous_close"
        assert r.alpha_deviation_threshold_pp == 10.0
        assert r.drift_ok_pp == 3.0
        assert r.drift_warn_pp == 5.0


class TestStrategyLoaderInvalid:
    def test_no_frontmatter(self):
        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            StrategyLoader.loads("# 本文だけ")

    def test_unclosed_frontmatter(self):
        with pytest.raises(ValueError, match="not properly closed"):
            StrategyLoader.loads("---\nrevision: 2026-05-14\n")

    def test_invalid_yaml(self):
        text = "---\nrevision: [unclosed\n---\n"
        with pytest.raises(ValueError, match="Invalid YAML"):
            StrategyLoader.loads(text)

    def test_missing_required_keys(self):
        text = "---\nrevision: 2026-05-14\nowner: test\n---\n本文"
        with pytest.raises(ValueError, match="missing required keys"):
            StrategyLoader.loads(text)

    def test_invalid_date_format(self):
        bad = VALID_FRONTMATTER.replace(
            "revision: 2026-05-14", 'revision: "not-a-date"'
        )
        with pytest.raises(ValueError, match="Invalid date format"):
            StrategyLoader.loads(bad)

    def test_target_holdings_missing_field(self):
        bad = VALID_FRONTMATTER.replace(
            '- { code: "2559", name: "オルカン",       bucket: "group_a", weight_pct: 15.00 }',
            '- { code: "2559", bucket: "group_a", weight_pct: 15.00 }',
        )
        with pytest.raises(ValueError, match="target_holdings item missing"):
            StrategyLoader.loads(bad)

    def test_target_buckets_sum_mismatch(self):
        """target_buckets の weight_pct 合計が100でなければエラー."""
        bad = VALID_FRONTMATTER.replace(
            'cash:    { label_ja: "現金",              weight_pct: 10.00 }',
            'cash:    { label_ja: "現金",              weight_pct: 5.00 }',
        )
        with pytest.raises(ValueError, match="target_buckets weight_pct must sum to 100"):
            StrategyLoader.loads(bad)

    def test_target_holdings_bucket_invalid(self):
        """target_holdings の bucket 値が target_buckets キーと一致しない."""
        bad = VALID_FRONTMATTER.replace(
            'bucket: "group_a", weight_pct: 15.00 }',
            'bucket: "unknown_bucket", weight_pct: 15.00 }',
            1,
        )
        with pytest.raises(ValueError, match="bucket .* is invalid"):
            StrategyLoader.loads(bad)

    def test_target_holdings_weight_sum_mismatch(self):
        """target_holdings の bucket 内 weight_pct 合計が target_buckets[bucket].weight_pct と一致しない."""
        bad = VALID_FRONTMATTER.replace(
            '- { code: "2559", name: "オルカン",       bucket: "group_a", weight_pct: 15.00 }',
            '- { code: "2559", name: "オルカン",       bucket: "group_a", weight_pct: 10.00 }',
        )
        with pytest.raises(
            ValueError,
            match="target_holdings weight_pct sum for bucket 'group_a'",
        ):
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

    def test_drift_ok_must_be_less_than_warn(self):
        """drift_ok_pp >= drift_warn_pp なら error."""
        bad = VALID_FRONTMATTER.replace("drift_ok_pp: 3.0", "drift_ok_pp: 6.0")
        with pytest.raises(ValueError, match="drift_ok_pp .* must be less than"):
            StrategyLoader.loads(bad)


class TestStrategyLoaderFile:
    def test_load_from_real_strategy_file(self):
        """docs/12_personal_strategy.md を実ファイルとしてロード."""
        from pathlib import Path

        # Docker環境（/app/docs/...）とホスト環境（parents[4]/docs/...）
        # の両方をフォールバック探索する
        candidates = [
            Path("/app/docs/12_personal_strategy.md"),
            Path(__file__).resolve().parents[4] / "docs" / "12_personal_strategy.md",
        ]
        strategy_path = next((p for p in candidates if p.exists()), None)
        if strategy_path is None:
            pytest.skip(f"Strategy file not found in: {candidates}")
        s = StrategyLoader.load(strategy_path)
        assert s.benchmark == "^N225"
        assert set(s.target_buckets.keys()) == {"group_a", "group_b", "cash"}
        # 採用銘柄は8銘柄
        assert len(s.target_holdings) == 8

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            StrategyLoader.load(tmp_path / "nonexistent.md")
