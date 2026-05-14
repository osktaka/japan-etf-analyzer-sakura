"""Unit tests: PortfolioRebalanceService の構造バグ修正検証.

保有ゼロの採用銘柄（例: 新規にA群追加された 1547 S&P500）が、
ETFマスタの market_price をフォールバック価格として使うことで
buy_actions に含まれることを確認する.

修正前: holdings に該当コードがない場合 current_price=0.0 固定 →
    買付判定 `current_price > 0 and ...` で必ず FALSE → buy_candidates から脱落.
修正後: etf_repository.get_by_codes() でマスタ価格を取得 → current_price に反映.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.services.portfolio_rebalance_service import PortfolioRebalanceService


@pytest.fixture
def fake_strategy():
    """採用2銘柄＋現金の最小 Strategy（実装スキーマに合わせたモック）.

    - 1547: weight_pct=15.0（保有ゼロ想定）
    - 1306: weight_pct=75.0（保有あり想定）
    - cash: weight_pct=10.0
    """
    holding_1547 = MagicMock()
    holding_1547.code = "1547"
    holding_1547.name = "1547 S&P500"
    holding_1547.weight_pct = 15.0

    holding_1306 = MagicMock()
    holding_1306.code = "1306"
    holding_1306.name = "1306 TOPIX"
    holding_1306.weight_pct = 75.0

    cash_bucket = MagicMock()
    cash_bucket.weight_pct = 10.0

    strategy = MagicMock()
    strategy.target_holdings = [holding_1547, holding_1306]
    strategy.target_buckets = {"cash": cash_bucket}
    strategy.mechanical_rules.drift_ok_pp = 3.0
    strategy.mechanical_rules.drift_warn_pp = 5.0
    return strategy


def _make_etf_mock(code: str, market_price: float):
    etf = MagicMock()
    etf.code = code
    etf.market_price = market_price
    return etf


class TestBuyActionsForUnheldAdoptedEtf:
    """保有ゼロの採用銘柄が buy_actions に含まれることを検証."""

    def test_unheld_adopted_etf_uses_master_price_fallback(self, fake_strategy):
        """1547 を保有していない状態でも、マスタ価格 12,785円から数量計算され
        buy_actions に出現することを確認.

        - target_pct=15% / total_asset=1,000,000 → target_amount=150,000
        - current_value=0 → diff_amount=+150,000
        - market_price=12,785 → quantity=floor(150,000/12,785)=11
        - amount=11*12,785=140,635
        """
        # 1306 のみ保有（1547 は保有なし）
        mock_ps = MagicMock()
        mock_ps.get_holdings.return_value = [
            {
                "etf_code": "1306",
                "current_price": 3000.0,
                "current_value": 750_000.0,
                "quantity": 250.0,
                "unrealized_pnl_percent": 0.0,
            },
        ]
        mock_ps.get_portfolio_summary.return_value = {
            "total_asset": 1_000_000.0,
            "cash_balance": 250_000.0,
            "daily_change_total_asset_percent": 0.0,
        }

        # ETFマスタ: 1547=12,785円 / 1306=3,000円
        mock_repo = MagicMock()
        mock_repo.get_by_codes.return_value = {
            "1547": _make_etf_mock("1547", 12_785.0),
            "1306": _make_etf_mock("1306", 3_000.0),
        }

        service = PortfolioRebalanceService(
            strategy=fake_strategy,
            portfolio_service=mock_ps,
            etf_repository=mock_repo,
        )
        plan = service.calculate_rebalance_plan(
            user_id=1, as_of_date=date(2026, 5, 14)
        )

        # 1547 が buy_actions に含まれる
        buy_codes = {a.etf_code for a in plan.buy_actions}
        assert "1547" in buy_codes, (
            f"1547 (unheld adopted ETF) must appear in buy_actions, "
            f"got {buy_codes}"
        )

        # 1547 のアクション内容を検証
        action_1547 = next(a for a in plan.buy_actions if a.etf_code == "1547")
        assert action_1547.action_type == "buy"
        # target_amount=150,000, price=12,785 → qty=floor(150,000/12,785)=11
        assert action_1547.quantity == 11
        # amount = 11 * 12,785 = 140,635
        assert action_1547.amount == pytest.approx(11 * 12_785.0)

        # snapshot 側でも current_price がマスタ価格にフォールバック
        snap_1547 = next(
            s for s in plan.holdings_snapshots if s.etf_code == "1547"
        )
        assert snap_1547.current_price == pytest.approx(12_785.0)
        assert snap_1547.quantity == 0.0
        assert snap_1547.current_value == 0.0
        assert snap_1547.is_adopted is True

    def test_unheld_adopted_etf_without_master_price_falls_back_to_zero(
        self, fake_strategy
    ):
        """マスタにも価格がない（None または 0）銘柄は従来通り 0.0 で安全フォールバック.

        buy_candidates に入らないため buy_actions にも出現しない.
        """
        mock_ps = MagicMock()
        mock_ps.get_holdings.return_value = []
        mock_ps.get_portfolio_summary.return_value = {
            "total_asset": 1_000_000.0,
            "cash_balance": 1_000_000.0,
            "daily_change_total_asset_percent": 0.0,
        }

        # 1547 はマスタ price=None / 1306 もマスタ取得不可
        mock_repo = MagicMock()
        etf_1547 = MagicMock()
        etf_1547.code = "1547"
        etf_1547.market_price = None
        mock_repo.get_by_codes.return_value = {"1547": etf_1547}

        service = PortfolioRebalanceService(
            strategy=fake_strategy,
            portfolio_service=mock_ps,
            etf_repository=mock_repo,
        )
        plan = service.calculate_rebalance_plan(
            user_id=1, as_of_date=date(2026, 5, 14)
        )

        # 1547 は price=0 のため買付候補に入らない（安全フォールバック）
        buy_codes = {a.etf_code for a in plan.buy_actions}
        assert "1547" not in buy_codes

        snap_1547 = next(
            s for s in plan.holdings_snapshots if s.etf_code == "1547"
        )
        assert snap_1547.current_price == 0.0

    def test_master_price_fetch_failure_falls_back_safely(self, fake_strategy):
        """etf_repository.get_by_codes() が例外を投げても処理は継続する."""
        mock_ps = MagicMock()
        mock_ps.get_holdings.return_value = []
        mock_ps.get_portfolio_summary.return_value = {
            "total_asset": 1_000_000.0,
            "cash_balance": 1_000_000.0,
            "daily_change_total_asset_percent": 0.0,
        }

        mock_repo = MagicMock()
        mock_repo.get_by_codes.side_effect = RuntimeError("DB down")

        service = PortfolioRebalanceService(
            strategy=fake_strategy,
            portfolio_service=mock_ps,
            etf_repository=mock_repo,
        )
        # 例外を投げずに RebalancePlan を返す
        plan = service.calculate_rebalance_plan(
            user_id=1, as_of_date=date(2026, 5, 14)
        )
        # マスタ価格取れず → buy_actions 空でも OK（クラッシュしないことが本旨）
        assert plan.total_asset == 1_000_000.0
