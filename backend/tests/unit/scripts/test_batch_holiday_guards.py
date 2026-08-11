"""非営業日・無変更時にバッチが重い処理を走らせないことを保証する。

本番crontabは曜日指定のみで祝日を判別できないため、祝日ガードはスクリプト側の
責務になる。2026-08-11（山の日）に本番で sync_from_minkabu が466件フルスクレイプし、
update_etf_data が取得ゼロのまま performance_cache を全再計算していた退行を防ぐ。
"""

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from src.utils.market_calendar import (  # noqa: E402
    get_next_market_day,
    get_previous_market_day,
    is_market_open_day,
)

# 2026年の実在する日付で固定する（jpholidayの判定を実データで検証するため）
WEEKDAY = date(2026, 8, 12)  # 水曜・平日
SATURDAY = date(2026, 8, 15)
SUNDAY = date(2026, 8, 16)
MOUNTAIN_DAY = date(2026, 8, 11)  # 火曜・山の日（本番で無駄バッチが走った日）


class TestMarketCalendar:
    def test_weekday_is_market_open(self):
        assert is_market_open_day(WEEKDAY) is True

    @pytest.mark.parametrize("day", [SATURDAY, SUNDAY])
    def test_weekend_is_closed(self, day):
        assert is_market_open_day(day) is False

    def test_national_holiday_is_closed(self):
        assert is_market_open_day(MOUNTAIN_DAY) is False

    def test_previous_market_day_skips_holiday(self):
        # 山の日(火)の前営業日は月曜
        assert get_previous_market_day(MOUNTAIN_DAY) == date(2026, 8, 10)

    def test_next_market_day_skips_holiday(self):
        # 月曜の翌営業日は山の日(火)を飛ばして水曜
        assert get_next_market_day(date(2026, 8, 10)) == WEEKDAY


class TestSharedCalendarIsSingleSource:
    """営業日判定は3スクリプトで共通実装を参照する（重複定義の再発防止）。"""

    def test_update_etf_data_reuses_shared_helper(self):
        import update_etf_data

        assert update_etf_data.is_market_open_day is is_market_open_day

    def test_update_scores_reuses_shared_helper(self):
        import update_scores

        assert update_scores.is_market_open_day is is_market_open_day

    def test_sync_from_minkabu_reuses_shared_helper(self):
        import sync_from_minkabu

        assert sync_from_minkabu.is_market_open_day is is_market_open_day


class TestSyncFromMinkabuHolidayGuard:
    """祝日・土日は minkabu への466リクエストを一切出さない。"""

    def _build_script(self, force=False):
        import sync_from_minkabu

        script = sync_from_minkabu.SyncFromMinkabuScript()
        script.args = SimpleNamespace(
            codes=None, limit=None, dry_run=False, rate_limit=1.5, force=force
        )
        return sync_from_minkabu, script

    def test_skips_on_non_market_day(self):
        module, script = self._build_script()

        with patch.object(
            module, "is_market_open_day", return_value=False
        ), patch.object(module, "_load_all_etf_codes") as load_codes, patch.object(
            module, "fetch_minkabu_data"
        ) as fetch:
            assert script.execute() == 0

        # DBにも外部サイトにも触れない
        load_codes.assert_not_called()
        fetch.assert_not_called()

    def test_force_flag_bypasses_guard(self):
        module, script = self._build_script(force=True)

        with patch.object(
            module, "is_market_open_day", return_value=False
        ), patch.object(module, "_load_all_etf_codes", return_value=[]) as load_codes:
            script.execute()

        load_codes.assert_called_once()


class TestUpdateScoresHolidayGuard:
    def test_skips_on_non_market_day(self):
        import update_scores

        script = update_scores.UpdateScoresBatch()
        script.args = SimpleNamespace(limit=None, dry_run=False, resume=None)

        with patch.object(update_scores, "is_market_open_day", return_value=False):
            assert script.execute() == 0


class TestPerformanceCacheRecalcCondition:
    """価格データが1件も更新されなかった実行では再計算しない。

    祝日は全銘柄が事前スキップされ success_count=0 になるため、
    カレンダー判定を持たずにこの条件だけで祝日の5分CPUが消える。
    """

    def test_skipped_when_nothing_updated(self):
        from update_etf_data import should_recalc_performance

        assert (
            should_recalc_performance(
                success_count=0, skip_performance=False, dry_run=False
            )
            is False
        )

    def test_runs_when_prices_updated(self):
        from update_etf_data import should_recalc_performance

        assert (
            should_recalc_performance(
                success_count=1, skip_performance=False, dry_run=False
            )
            is True
        )

    @pytest.mark.parametrize(
        "skip_performance,dry_run", [(True, False), (False, True), (True, True)]
    )
    def test_existing_flags_still_win(self, skip_performance, dry_run):
        from update_etf_data import should_recalc_performance

        assert (
            should_recalc_performance(
                success_count=466, skip_performance=skip_performance, dry_run=dry_run
            )
            is False
        )


class TestModuleLoggerDefined:
    """save_to_db / check_and_register_split は引数で logger を受け取らない。

    モジュールスコープの logger が無いと、NaN行を含む銘柄の保存時や分割検知の
    失敗時に警告を出そうとして NameError になり、その銘柄が failed に落ちる。
    """

    def test_update_etf_data_has_module_logger(self):
        import logging

        import update_etf_data

        assert isinstance(update_etf_data.logger, logging.Logger)


class TestLogVolume:
    """1銘柄あたり8行出ていたキャッシュヒットログをDEBUGへ落とす。"""

    def test_cache_hit_is_not_logged_at_info(self, caplog):
        from src.external.yahoo_finance import YahooFinanceClient

        cached = [{"date": "2026-08-10", "close": 100.0}]

        with patch(
            "src.external.yahoo_finance._is_mock_mode", return_value=False
        ), patch.object(YahooFinanceClient, "_get_from_cache", return_value=cached):
            with caplog.at_level("INFO", logger="src.external.yahoo_finance"):
                YahooFinanceClient.get_chart_data("1306", "1y")

        assert not [r for r in caplog.records if "Using cached data" in r.message]

    def test_cache_hit_still_available_at_debug(self, caplog):
        from src.external.yahoo_finance import YahooFinanceClient

        cached = [{"date": "2026-08-10", "close": 100.0}]

        with patch(
            "src.external.yahoo_finance._is_mock_mode", return_value=False
        ), patch.object(YahooFinanceClient, "_get_from_cache", return_value=cached):
            with caplog.at_level("DEBUG", logger="src.external.yahoo_finance"):
                YahooFinanceClient.get_chart_data("1306", "1y")

        assert [r for r in caplog.records if "Using cached data" in r.message]


class TestLogRotationThreshold:
    """8.7MB/日のログが10MB閾値に1日で届かず2日分溜まっていた問題への対処。"""

    def test_threshold_rotates_within_a_day(self):
        import rotate_logs

        assert rotate_logs.SIZE_THRESHOLD_MB == 5
