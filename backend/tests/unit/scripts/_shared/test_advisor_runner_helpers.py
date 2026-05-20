"""AdvisorRunner の Step 2 で追加されたヘルパ関数の回帰テスト.

対象:
- _calculate_rebalance_plan: PortfolioRebalanceService.calculate_rebalance_plan を委譲
- _persist_evening_summary: 夕方サマリ JSON を reports_dir に書き出す
- _load_previous_evening_summary: 当日→5日前まで JSON fallback 読み込み
- _fetch_overnight_safe: market_data_quick.fetch_overnight_data の安全呼び出し

外部依存（PortfolioRebalanceService / market_data_quick / yfinance / DB）は
すべてモックで遮断する.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _shared.advisor_runner import AdvisorRunner  # noqa: E402


def _make_runner(tmp_path) -> AdvisorRunner:
    """共通: テスト用 AdvisorRunner インスタンス（dry_run）を生成."""
    return AdvisorRunner(
        project_root=tmp_path,
        strategy_file=tmp_path / "dummy_strategy.md",
        reports_dir=tmp_path / "reports",
        user_id_str="test",
        dry_run=True,
    )


# ==============================================================
# _calculate_rebalance_plan
# ==============================================================


class TestCalculateRebalancePlan:
    def test_success(self, tmp_path):
        """PortfolioRebalanceService.calculate_rebalance_plan の戻り値が返る."""
        runner = _make_runner(tmp_path)
        fake_plan = MagicMock(name="RebalancePlan")
        fake_service = MagicMock()
        fake_service.calculate_rebalance_plan.return_value = fake_plan
        # PortfolioRebalanceService(strategy) → service インスタンス
        fake_service_cls = MagicMock(return_value=fake_service)
        deps = {"PortfolioRebalanceService": fake_service_cls}
        strategy = MagicMock(name="Strategy")

        plan = runner._calculate_rebalance_plan(
            deps, strategy, user_id_int=42, today=date(2026, 5, 7)
        )

        assert plan is fake_plan
        fake_service_cls.assert_called_once_with(strategy)
        fake_service.calculate_rebalance_plan.assert_called_once_with(
            user_id=42, as_of_date=date(2026, 5, 7)
        )

    def test_returns_none_when_user_id_missing(self, tmp_path):
        """user_id_int=None なら計算スキップで None を返す（DB問い合わせしない）."""
        runner = _make_runner(tmp_path)
        deps = {"PortfolioRebalanceService": MagicMock()}
        assert runner._calculate_rebalance_plan(
            deps, MagicMock(), user_id_int=None, today=date(2026, 5, 7)
        ) is None
        deps["PortfolioRebalanceService"].assert_not_called()

    def test_returns_none_on_exception(self, tmp_path):
        """サービスが例外を投げても None で握り潰す（メール本処理を止めない）."""
        runner = _make_runner(tmp_path)
        fake_service = MagicMock()
        fake_service.calculate_rebalance_plan.side_effect = RuntimeError("boom")
        deps = {"PortfolioRebalanceService": MagicMock(return_value=fake_service)}
        result = runner._calculate_rebalance_plan(
            deps, MagicMock(), user_id_int=42, today=date(2026, 5, 7)
        )
        assert result is None


# ==============================================================
# _persist_evening_summary
# ==============================================================


def _make_plan(
    *,
    is_rebalance_day=False,
    next_rebalance_date=date(2026, 6, 30),
    days_to_next=54,
    sell_actions=(),
    buy_actions=(),
    holdings_snapshots=(),
):
    """RebalancePlan モック生成ヘルパ."""
    plan = MagicMock()
    plan.is_rebalance_day = is_rebalance_day
    plan.next_rebalance_date = next_rebalance_date
    plan.days_to_next_rebalance = days_to_next
    plan.sell_actions = sell_actions
    plan.buy_actions = buy_actions
    plan.holdings_snapshots = holdings_snapshots
    return plan


def _make_action(etf_code, amount):
    a = MagicMock()
    a.etf_code = etf_code
    a.amount = amount
    return a


def _make_snapshot(etf_code, name, *, drift_pp: float = 5.0, is_adopted: bool = True):
    """テスト用 HoldingSnapshot モック.

    DISPLAY_THRESHOLD_PP=2.0 を超える drift_pp をデフォルトとし、
    既存テストは表示フィルタを通過する前提で組まれている.
    """
    s = MagicMock()
    s.etf_code = etf_code
    s.name = name
    s.drift_pp = drift_pp
    s.is_adopted = is_adopted
    return s


class TestPersistEveningSummary:
    def test_writes_json_with_expected_keys(self, tmp_path):
        """期待されるキー（date, is_rebalance_day, sell_top3 等）を含む JSON を書く."""
        runner = _make_runner(tmp_path)
        plan = _make_plan(
            is_rebalance_day=False,
            sell_actions=(_make_action("1306", 30000), _make_action("1615", 10000)),
            buy_actions=(_make_action("2559", 50000),),
            holdings_snapshots=(
                _make_snapshot("1306", "TOPIX"),
                _make_snapshot("1615", "銀行"),
                _make_snapshot("2559", "オルカン"),
            ),
        )

        runner._persist_evening_summary(date(2026, 5, 7), plan)

        out_path = runner.reports_dir / "evening_summary_20260507.json"
        assert out_path.exists()
        data = json.loads(out_path.read_text(encoding="utf-8"))
        # 必須キー
        for key in [
            "date", "is_rebalance_day", "next_rebalance_date",
            "days_to_next_rebalance", "sell_actions_count", "buy_actions_count",
            "sell_top3", "buy_top3",
        ]:
            assert key in data
        # 値の整合性
        assert data["date"] == "2026-05-07"
        assert data["is_rebalance_day"] is False
        assert data["sell_actions_count"] == 2
        assert data["buy_actions_count"] == 1
        # 金額降順で sell_top3 がソートされていること
        assert data["sell_top3"][0]["etf_code"] == "1306"
        assert data["sell_top3"][0]["name"] == "TOPIX"
        assert data["sell_top3"][0]["amount"] == 30000

    def test_silent_failure_does_not_raise(self, tmp_path):
        """内部例外を伝搬しない（warning ログのみ）.

        days_to_next_rebalance が int 変換不可な場合、json 構築前に
        TypeError が発生する想定. 例外を握り潰すこと.
        """
        runner = _make_runner(tmp_path)
        bad_plan = MagicMock()
        bad_plan.is_rebalance_day = False
        bad_plan.next_rebalance_date = None
        bad_plan.days_to_next_rebalance = "not-an-int"  # int() で失敗
        bad_plan.sell_actions = ()
        bad_plan.buy_actions = ()
        bad_plan.holdings_snapshots = ()

        # 例外が伝搬しないこと（呼び出し自体が raise しないことを assert）
        runner._persist_evening_summary(date(2026, 5, 7), bad_plan)

    def test_uses_shared_compute_top_n_actions(self, tmp_path):
        """compute_top_n_actions 経由で sell_top3 / buy_top3 が生成される.

        共通化リファクタの回帰テスト. ロジックは
        ``src.services.daily_advisor_service.compute_top_n_actions`` に集約済み.

        DISPLAY_THRESHOLD_PP=2.0 フィルタ導入後は、snapshot の drift_pp が
        閾値以上のアクションのみが top3 に含まれる.
        """
        from src.services.daily_advisor_service import (
            compute_top_n_actions,
            filter_actions_for_display,
        )

        runner = _make_runner(tmp_path)
        sells = (
            _make_action("1306", 10000),
            _make_action("1615", 30000),
        )
        # 両方とも drift_pp=5.0（デフォルト）でフィルタを通過
        snaps = (
            _make_snapshot("1306", "TOPIX"),
            _make_snapshot("1615", "銀行"),
        )
        plan = _make_plan(
            sell_actions=sells,
            buy_actions=(),
            holdings_snapshots=snaps,
        )

        runner._persist_evening_summary(date(2026, 5, 7), plan)

        out_path = runner.reports_dir / "evening_summary_20260507.json"
        data = json.loads(out_path.read_text(encoding="utf-8"))
        # フィルタ適用後の compute_top_n_actions と一致
        filtered = filter_actions_for_display(sells, snaps, action_type="sell")
        expected = compute_top_n_actions(filtered, snaps)
        assert data["sell_top3"] == expected

    def test_filters_below_threshold_and_keeps_non_adopted(self, tmp_path):
        """閾値未満の採用済み銘柄は JSON に残らず、採用外はスルーで残る.

        sell_actions_count / buy_actions_count もフィルタ後の値で永続化される.
        """
        runner = _make_runner(tmp_path)
        # 売却: 採用済み閾値未満 (除外) + 採用済み閾値以上 (残る) + 採用外 (スルーで残る)
        sells = (
            _make_action("A001", 1000),   # |drift|=1.9 → 除外
            _make_action("A002", 50000),  # |drift|=5.0 → 残る
            _make_action("X999", 500),    # 採用外 → 残る
        )
        # 買付: 採用済み閾値未満 (除外) + 採用済み閾値以上 (残る)
        buys = (
            _make_action("B001", 1000),   # |drift|=1.9 → 除外
            _make_action("B002", 50000),  # |drift|=5.0 → 残る
        )
        snaps = (
            _make_snapshot("A001", "Aほぼ均衡", drift_pp=1.9, is_adopted=True),
            _make_snapshot("A002", "A超過", drift_pp=5.0, is_adopted=True),
            _make_snapshot("X999", "採用外", drift_pp=0.5, is_adopted=False),
            _make_snapshot("B001", "Bほぼ均衡", drift_pp=-1.9, is_adopted=True),
            _make_snapshot("B002", "B不足", drift_pp=-5.0, is_adopted=True),
        )
        plan = _make_plan(
            sell_actions=sells,
            buy_actions=buys,
            holdings_snapshots=snaps,
        )

        runner._persist_evening_summary(date(2026, 5, 7), plan)

        out_path = runner.reports_dir / "evening_summary_20260507.json"
        data = json.loads(out_path.read_text(encoding="utf-8"))

        # count はフィルタ後の値（sell: 2 件 = A002 + X999、buy: 1 件 = B002）
        assert data["sell_actions_count"] == 2
        assert data["buy_actions_count"] == 1

        sell_codes = [s["etf_code"] for s in data["sell_top3"]]
        assert "A002" in sell_codes
        assert "X999" in sell_codes  # 採用外はスルー
        assert "A001" not in sell_codes  # 閾値未満は除外

        buy_codes = [b["etf_code"] for b in data["buy_top3"]]
        assert "B002" in buy_codes
        assert "B001" not in buy_codes  # 閾値未満は除外


# ==============================================================
# _load_previous_evening_summary
# ==============================================================


class TestLoadPreviousEveningSummary:
    def _write_summary(self, reports_dir: Path, d: date, payload: dict) -> None:
        reports_dir.mkdir(parents=True, exist_ok=True)
        f = reports_dir / f"evening_summary_{d.strftime('%Y%m%d')}.json"
        f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_fallback_loads_two_days_ago(self, tmp_path):
        """当日無し → 2 日前のファイルがあれば読み込む."""
        runner = _make_runner(tmp_path)
        today = date(2026, 5, 7)
        # 2日前のサマリのみ存在
        self._write_summary(
            runner.reports_dir, today.replace(day=5),
            {"date": "2026-05-05", "is_rebalance_day": False},
        )

        result = runner._load_previous_evening_summary(today)

        assert result is not None
        assert result["date"] == "2026-05-05"

    def test_returns_none_when_older_than_5_days(self, tmp_path):
        """6日前のファイルしかない場合は None（fallback 範囲は 5 日まで）."""
        runner = _make_runner(tmp_path)
        today = date(2026, 5, 7)
        # 6 日前のみ存在
        self._write_summary(
            runner.reports_dir, date(2026, 5, 1),
            {"date": "2026-05-01", "is_rebalance_day": False},
        )

        assert runner._load_previous_evening_summary(today) is None

    def test_returns_none_when_no_files(self, tmp_path):
        """ファイルが一切無ければ None."""
        runner = _make_runner(tmp_path)
        assert runner._load_previous_evening_summary(date(2026, 5, 7)) is None


# ==============================================================
# _fetch_overnight_safe
# ==============================================================


class TestFetchOvernightSafe:
    def test_handles_failure_returns_none(self, tmp_path):
        """fetch_overnight_data が例外を投げると None を返す（warning ログのみ）."""
        runner = _make_runner(tmp_path)
        fake_module = MagicMock()
        fake_module.fetch_overnight_data.side_effect = RuntimeError("yfinance down")

        with patch.dict(sys.modules, {"market_data_quick": fake_module}):
            result = runner._fetch_overnight_safe()

        assert result is None
        fake_module.fetch_overnight_data.assert_called_once()

    def test_success_returns_payload(self, tmp_path):
        """成功時は fetch_overnight_data の返り値をそのまま返す."""
        runner = _make_runner(tmp_path)
        payload = {
            "sp500": {"price": 5_100.0, "change_pct": 0.3, "status": "closed"},
            "errors": [],
        }
        fake_module = MagicMock()
        fake_module.fetch_overnight_data.return_value = payload

        with patch.dict(sys.modules, {"market_data_quick": fake_module}):
            result = runner._fetch_overnight_safe()

        assert result is payload
