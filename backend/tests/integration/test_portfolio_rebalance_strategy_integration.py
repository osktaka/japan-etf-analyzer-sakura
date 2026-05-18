"""Integration test: 実 strategy.md を読み込み、PortfolioRebalanceService が
期待通りのリバランス計画を返すことを検証する.

Step 5 の完了条件:
- docs/12_personal_strategy.md からの読み込みが成功
- target_weights が7銘柄分すべて出力されている
- mechanical_rules.drift_warn_pp / drift_ok_pp が strategy 経由で正しく取得されている
- 単純なモック portfolio で cash_deviation_pp が期待値どおり計算される
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services.portfolio_rebalance_service import PortfolioRebalanceService
from src.services.strategy_loader import StrategyLoader


# プロジェクトルートの実 strategy.md を使う（テスト用ダミーではなく SSOT 検証）
# Docker内: /app/tests/integration/foo.py → /app, /app/docs/12_personal_strategy.md
# ホスト: backend/tests/integration/foo.py → backend, 親が project root
_THIS_DIR = Path(__file__).resolve().parent
# tests/integration → tests → backend → project root
_BACKEND_ROOT = _THIS_DIR.parent.parent  # /app or backend/
# docs/ は backend と同階層（プロジェクトルート直下）または backend/docs（Docker mount）
_CANDIDATES = [
    _BACKEND_ROOT / "docs" / "12_personal_strategy.md",          # Docker /app/docs/
    _BACKEND_ROOT.parent / "docs" / "12_personal_strategy.md",   # ホスト project root
]
STRATEGY_PATH = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])


@pytest.fixture(scope="module")
def real_strategy():
    """実 strategy.md からロードした Strategy インスタンス."""
    assert STRATEGY_PATH.exists(), f"Strategy file missing: {STRATEGY_PATH}"
    return StrategyLoader.load(STRATEGY_PATH)


class TestStrategyLoadedFromRealFile:
    """実ファイルから Strategy をロードし、期待スキーマで読めることを確認."""

    def test_target_buckets_keys(self, real_strategy):
        # group_a / group_b / cash の3カテゴリ
        assert set(real_strategy.target_buckets.keys()) == {"group_a", "group_b", "cash"}

    def test_target_buckets_sum_100(self, real_strategy):
        total = sum(b.weight_pct for b in real_strategy.target_buckets.values())
        assert abs(total - 100.0) < 0.01

    def test_target_holdings_count(self, real_strategy):
        # 採用7銘柄（2026-05-18改訂でA群を1655/314A/1629に整合、1306撤廃、B群4銘柄各10%）
        assert len(real_strategy.target_holdings) == 7

    def test_target_holdings_codes(self, real_strategy):
        codes = {h.code for h in real_strategy.target_holdings}
        # A群: 1655/314A/1629, B群: 1615/2646/1618/200A
        expected = {"1655", "314A", "1629", "1615", "2646", "1618", "200A"}
        assert codes == expected

    def test_mechanical_rules_drift_thresholds(self, real_strategy):
        # 戦略書 §5.2 で定義: drift_ok_pp=3.0, drift_warn_pp=5.0
        assert real_strategy.mechanical_rules.drift_ok_pp == 3.0
        assert real_strategy.mechanical_rules.drift_warn_pp == 5.0


class TestRebalanceServiceWithRealStrategy:
    """実 Strategy を DI した PortfolioRebalanceService の挙動検証."""

    def _make_service(self, real_strategy, *, holdings, summary):
        """モック portfolio_service を持つ PortfolioRebalanceService."""
        mock_ps = MagicMock()
        mock_ps.get_holdings.return_value = holdings
        mock_ps.get_portfolio_summary.return_value = summary
        return PortfolioRebalanceService(
            strategy=real_strategy, portfolio_service=mock_ps
        )

    def test_target_weights_match_strategy(self, real_strategy):
        """plan.target_weights が strategy の target_holdings.weight_pct と一致する."""
        service = self._make_service(
            real_strategy,
            holdings=[],
            summary={
                "total_asset": 1_000_000.0,
                "cash_balance": 100_000.0,
                "daily_change_total_asset_percent": 0.0,
            },
        )
        plan = service.calculate_rebalance_plan(
            user_id=1, as_of_date=date(2026, 5, 14)
        )
        # 採用7銘柄の target_weights が strategy 値と完全一致
        expected = {h.code: h.weight_pct for h in real_strategy.target_holdings}
        assert plan.target_weights == expected

    def test_cash_deviation_pp_calculation(self, real_strategy):
        """現金100%（保有ゼロ）→ cash_deviation_pp = +85.0pp（cash target=15%）."""
        service = self._make_service(
            real_strategy,
            holdings=[],
            summary={
                "total_asset": 1_000_000.0,
                "cash_balance": 1_000_000.0,
                "daily_change_total_asset_percent": 0.0,
            },
        )
        plan = service.calculate_rebalance_plan(
            user_id=1, as_of_date=date(2026, 5, 14)
        )
        # 現金 1,000,000 / 総資産 1,000,000 = 100% → target 15% → 乖離 +85pp
        assert abs(plan.cash_deviation_pp - 85.0) < 0.01

    def test_strategy_drift_thresholds_propagate(self, real_strategy):
        """サービス内で参照される drift_ok_pp / drift_warn_pp が strategy 経由で取得できる."""
        service = self._make_service(
            real_strategy,
            holdings=[],
            summary={
                "total_asset": 1_000_000.0,
                "cash_balance": 100_000.0,
                "daily_change_total_asset_percent": 0.0,
            },
        )
        # property 経由でも参照可能（テンプレ/レンダラからの間接参照を模擬）
        assert service._drift_ok_pp == 3.0
        assert service._drift_warn_pp == 5.0
