"""Tests for NotificationRenderer."""
from __future__ import annotations

from datetime import date

import pytest

from src.services.daily_advisor_service import (
    AllocationDrift,
    NotificationContext,
    RuleTrigger,
)
from src.services.notification_renderer import NotificationRenderer


@pytest.fixture
def renderer():
    return NotificationRenderer()


def _morning_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="morning",
        today=date(2026, 5, 7),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        daily_change_pct=0.5,
        holdings_count=6,
    )
    base.update(overrides)
    return NotificationContext(**base)


def _evening_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="evening",
        today=date(2026, 4, 29),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        daily_change_pct=-0.3,
        holdings_count=6,
        allocation_drifts=(
            AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=43.0, drift_pp=-2.0, warn_threshold_pp=5.0),
            AllocationDrift(bucket="group_b", target_pct=45.0, actual_pct=47.0, drift_pp=2.0, warn_threshold_pp=5.0),
        ),
        triggers=(),
    )
    base.update(overrides)
    return NotificationContext(**base)


def _weekly_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="weekly",
        today=date(2026, 5, 1),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        holdings_count=6,
        allocation_drifts=(
            AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=40.0, drift_pp=-5.0, warn_threshold_pp=5.0),
        ),
        triggers=(),
        alpha_pp=-1.0,
        period_label="過去5営業日",
        portfolio_return_pct=2.0,
        benchmark_return_pct=3.0,
    )
    base.update(overrides)
    return NotificationContext(**base)


def _alert_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="alert",
        today=date(2026, 4, 29),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        triggers=(
            RuleTrigger(
                rule_kind="n225_drawdown", code=None, severity="warn",
                message="N225 急落 -6%", fingerprint="abc",
                payload={"change_pct": -6.0, "threshold_pct": -5.0},
            ),
        ),
    )
    base.update(overrides)
    return NotificationContext(**base)


class TestRender:
    def test_morning(self, renderer):
        md, html = renderer.render(_morning_ctx())
        assert "朝のタスク" in md
        assert "前日比: +0.50%" in md
        # h1 はインラインスタイル付与のため部分一致
        assert "<h1" in html
        assert "1,000,000" in md
        # 旧「今日の発注」セクションは削除済み
        assert "今日の発注" not in md
        # rebalance_plan なしの通常日 → 「静観」
        assert "**静観**" in md

    def test_evening(self, renderer):
        md, html = renderer.render(_evening_ctx())
        assert "夕方のレビュー" in md
        # bucket は翻訳マクロで「A群（コア・ヘッジ）」「B群（日本株テーマ）」表記
        assert "A群（コア・ヘッジ）" in md
        assert "B群（日本株テーマ）" in md
        assert "<h1" in html
        # リード文
        assert "本日 -0.30%" in md
        assert "**静観**" in md

    def test_weekly_with_alpha(self, renderer):
        md, html = renderer.render(_weekly_ctx())
        assert "週次レビュー" in md
        assert "α" in md
        assert "-1.00pp" in md
        assert "過去5営業日" in md
        # 推奨アクション (drift_pp = -5.0 は abs >5 でないが、α<=-2.0 でもないため、推奨セクション無し)
        # → ここは静観 or 要確認 に応じた追加検証は別テスト
        assert "**静観**" in md

    def test_weekly_with_negative_alpha_recommends_action(self, renderer):
        # α=-3.0 で α<=-2 → 推奨アクションセクション出る
        ctx = _weekly_ctx(alpha_pp=-3.0)
        md, _ = renderer.render(ctx)
        assert "来週の推奨アクション" in md
        # bucket 翻訳済み: group_a → A群（コア・ヘッジ）
        assert "A群（コア・ヘッジ）ETFの追加買付" in md
        assert "**要確認**" in md

    def test_alert(self, renderer):
        md, html = renderer.render(_alert_ctx())
        assert "機械ルール" in md
        assert "n225_drawdown" in md
        assert "N225 急落" in md
        assert "<h1" in html
        # 推奨アクション
        assert "推奨アクション" in md
        assert "静観 or 戦略書の急落時方針" in md


class TestSubject:
    """件名フォーマット.

    朝/夕構成見直し後の仕様:
    - morning: `【寄り付き前】Daily Advisor / M/D [補足]`
    - evening: `【終値ベース】Daily Advisor / M/D [変動率] [補足]`
    - weekly/alert: 旧仕様 `[M/D 区分] 結論` を維持
    """

    def test_morning_subject_quiet(self, renderer):
        # rebalance_plan なし & 警告なし → 末尾補足なし
        ctx = _morning_ctx()
        s = renderer.subject_for(ctx)
        assert s == f"【寄り付き前】Daily Advisor / {ctx.today.month}/{ctx.today.day}"
        # user_id (test) は件名に含めない
        assert "test" not in s

    def test_evening_subject_quiet(self, renderer):
        # 警告 drift なし → `【終値ベース】Daily Advisor / 4/29 -0.3%`
        ctx = _evening_ctx()
        s = renderer.subject_for(ctx)
        assert s.startswith(
            f"【終値ベース】Daily Advisor / {ctx.today.month}/{ctx.today.day}"
        )
        # 静観時は変動率のみ・配分逸脱件数が含まれない
        assert "逸脱" not in s

    def test_weekly_subject(self, renderer):
        # α=-1.0 (>-2.0) かつ警告なし → `[5/1 週次] α -1.0pp`
        ctx = _weekly_ctx()
        s = renderer.subject_for(ctx)
        assert s.startswith(f"[{ctx.today.month}/{ctx.today.day} 週次]")
        assert "α" in s
        assert "pp" in s

    def test_alert_critical_subject(self, renderer):
        ctx = NotificationContext(
            kind="alert",
            today=date(2026, 4, 29),
            user_id="test",
            strategy_revision=date(2026, 4, 29),
            benchmark="^N225",
            drift_ok_pp=3.0,
            drift_warn_pp=5.0,
            triggers=(
                RuleTrigger(
                    rule_kind="loss_cut", code="1306", severity="critical",
                    message="loss cut", fingerprint="x",
                ),
            ),
        )
        s = renderer.subject_for(ctx)
        # `[4/29 緊急] 損切到達: 1306` 形式
        assert s.startswith(f"[{ctx.today.month}/{ctx.today.day} 緊急]")
        assert "1306" in s

    def test_alert_warn_subject(self, renderer):
        ctx = _alert_ctx()
        s = renderer.subject_for(ctx)
        # `[4/29 要確認] N225急落` 形式
        assert s.startswith(f"[{ctx.today.month}/{ctx.today.day} 要確認]")


class TestUrgencyTag:
    def test_critical_in_morning(self, renderer):
        ctx = _morning_ctx(triggers=(
            RuleTrigger(
                rule_kind="loss_cut", code="1306", severity="critical",
                message="x", fingerprint="f1",
            ),
        ))
        assert renderer.urgency_tag(ctx) == "緊急"

    def test_warn_in_evening(self, renderer):
        ctx = _evening_ctx(triggers=(
            RuleTrigger(
                rule_kind="allocation_drift", code=None, severity="warn",
                message="drift", fingerprint="f2",
            ),
        ))
        assert renderer.urgency_tag(ctx) == "要確認"

    def test_weekly_alpha_loss(self, renderer):
        ctx = _weekly_ctx(alpha_pp=-3.0)
        assert renderer.urgency_tag(ctx) == "要確認"

    def test_quiet(self, renderer):
        ctx = _morning_ctx(triggers=())
        assert renderer.urgency_tag(ctx) == "静観"

    def test_alert_info(self, renderer):
        ctx = _alert_ctx(triggers=(
            RuleTrigger(
                rule_kind="n225_drawdown", code=None, severity="info",
                message="x", fingerprint="f3",
            ),
        ))
        assert renderer.urgency_tag(ctx) == "情報"


class TestSummary:
    def test_morning_critical(self, renderer):
        ctx = _morning_ctx(triggers=(
            RuleTrigger(
                rule_kind="loss_cut", code="1306", severity="critical",
                message="x", fingerprint="f1",
            ),
        ))
        s = renderer.summary_for(ctx)
        assert "緊急" in s
        assert "loss_cut" in s

    def test_morning_quiet(self, renderer):
        # rebalance_plan なし & 警告なし → 静観
        ctx = _morning_ctx()
        s = renderer.summary_for(ctx)
        assert "発注予定なし" in s

    def test_morning_no_double_count_allocation_drift(self, renderer):
        # allocation_drift trigger と is_warn drift のダブルカウント防止
        ctx = _morning_ctx(
            allocation_drifts=(
                AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=35.0, drift_pp=-10.0, warn_threshold_pp=5.0),
            ),
            triggers=(
                RuleTrigger(
                    rule_kind="allocation_drift", code=None, severity="warn",
                    message="配分逸脱: group_a", fingerprint="a"
                ),
            ),
        )
        s = renderer.summary_for(ctx)
        assert "配分逸脱1件継続中" in s

    def test_evening_with_change(self, renderer):
        s = renderer.summary_for(_evening_ctx())
        assert "本日 -0.30%" in s
        assert "配分・ルール異常なし" in s

    def test_evening_with_warn(self, renderer):
        ctx = _evening_ctx(allocation_drifts=(
            AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=35.0, drift_pp=-10.0, warn_threshold_pp=5.0),
        ))
        s = renderer.summary_for(ctx)
        assert "本日 -0.30%" in s
        assert "配分逸脱1件あり" in s

    def test_evening_no_double_count(self, renderer):
        # allocation_drift trigger と is_warn drift を二重に数えないこと
        ctx = _evening_ctx(
            allocation_drifts=(
                AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=35.0, drift_pp=-10.0, warn_threshold_pp=5.0),
                AllocationDrift(bucket="group_b", target_pct=45.0, actual_pct=30.0, drift_pp=-15.0, warn_threshold_pp=5.0),
            ),
            triggers=(
                RuleTrigger(rule_kind="allocation_drift", code=None, severity="warn",
                            message="配分逸脱: group_a", fingerprint="a"),
                RuleTrigger(rule_kind="allocation_drift", code=None, severity="warn",
                            message="配分逸脱: group_b", fingerprint="b"),
            ),
        )
        s = renderer.summary_for(ctx)
        assert "配分逸脱2件" in s
        assert "ルール警告" not in s

    def test_evening_other_rule_warn(self, renderer):
        # allocation_drift 以外の warn は ルール警告として別カウント
        ctx = _evening_ctx(
            allocation_drifts=(
                AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=35.0, drift_pp=-10.0, warn_threshold_pp=5.0),
            ),
            triggers=(
                RuleTrigger(rule_kind="n225_drawdown", code=None, severity="warn",
                            message="N225 -6%", fingerprint="x"),
            ),
        )
        s = renderer.summary_for(ctx)
        assert "配分逸脱1件" in s
        assert "ルール警告1件" in s

    def test_weekly_negative_alpha(self, renderer):
        ctx = _weekly_ctx(alpha_pp=-3.0)
        s = renderer.summary_for(ctx)
        assert "α -3.00pp" in s
        assert "負け" in s

    def test_weekly_outperform(self, renderer):
        ctx = _weekly_ctx(alpha_pp=3.5)
        s = renderer.summary_for(ctx)
        assert "アウトパフォーム" in s

    def test_weekly_no_alpha(self, renderer):
        ctx = _weekly_ctx(alpha_pp=None, portfolio_return_pct=None, benchmark_return_pct=None)
        s = renderer.summary_for(ctx)
        assert "算出不可" in s

    def test_alert_warn(self, renderer):
        s = renderer.summary_for(_alert_ctx())
        assert "warnアラート1件" in s
        assert "n225_drawdown" in s

    def test_alert_many_triggers(self, renderer):
        triggers = tuple(
            RuleTrigger(
                rule_kind=f"loss_cut", code=str(1300 + i), severity="critical",
                message="m", fingerprint=f"f{i}",
            )
            for i in range(5)
        )
        ctx = _alert_ctx(triggers=triggers)
        s = renderer.summary_for(ctx)
        assert "criticalアラート5件" in s
        assert "他2件" in s


class TestRecommendedAction:
    def test_known_kinds(self, renderer):
        for kind, expect_substr in [
            ("loss_cut", "売却検討"),
            ("take_profit_1", "段階的売却（第1段）"),
            ("take_profit_2", "段階的売却（第2段）"),
            ("n225_drawdown", "戦略書の急落時方針"),
            ("allocation_drift", "配分是正"),
        ]:
            t = RuleTrigger(
                rule_kind=kind, code=None, severity="warn",
                message="x", fingerprint=f"f-{kind}",
            )
            assert expect_substr in renderer.recommended_action(t)

    def test_unknown_kind(self, renderer):
        t = RuleTrigger(
            rule_kind="unknown_rule_xxx", code=None, severity="info",
            message="x", fingerprint="f-unk",
        )
        assert renderer.recommended_action(t) == "戦略書を確認してください。"


# ============================================================
# 朝/夕構成見直し（Step 3）で追加された新セクションの
# レンダリング回帰テスト. StrictUndefined のため、テンプレート
# 側で参照される全フィールドが揃っているかを確認する.
# ============================================================
def _make_rebalance_plan(
    *,
    is_rebalance_day=False,
    days_to_next=10,
    holdings_snapshots=(),
    sell_actions=(),
    buy_actions=(),
):
    """テンプレ描画用の最小 RebalancePlan モック."""
    from src.services.portfolio_rebalance_service import RebalancePlan

    return RebalancePlan(
        target_weights={"2559": 15.0, "1306": 9.0},
        current_weights={"2559": 14.5, "1306": 9.5, "CASH": 10.0},
        deviations={"2559": -0.5, "1306": 0.5},
        sell_actions=tuple(sell_actions),
        buy_actions=tuple(buy_actions),
        total_asset=1_000_000.0,
        target_cash=100_000.0,
        target_cash_pct=10.0,
        current_cash=100_000.0,
        cash_deviation_pp=0.0,
        days_to_next_rebalance=days_to_next,
        next_rebalance_date=date(2026, 6, 30),
        is_rebalance_day=is_rebalance_day,
        daily_pnl_pct=None,
        holdings_snapshots=tuple(holdings_snapshots),
        warn_count=0,
        critical_count=0,
    )


def _overnight_payload():
    """fetch_overnight_data 戻り値の最小再現."""
    return {
        "sp500": {"price": 5_100.5, "change_pct": 0.32, "status": "closed"},
        "nasdaq": {"price": 16_200.0, "change_pct": 0.45, "status": "closed"},
        "dow": {"price": 38_900.0, "change_pct": 0.10, "status": "closed"},
        "vix": {"price": 14.5, "change_pct": -2.0, "change": -0.3, "status": "closed"},
        "usdjpy": {"price": 156.30, "change_pct": 0.18, "status": "closed"},
        "nikkei_futures": {"price": 39_200.0, "change_pct": 0.5, "status": "closed"},
        "fetched_at": "2026-05-07T07:00:00+09:00",
        "errors": [],
    }


def _previous_evening_summary(*, has_actions=True):
    return {
        "date": "2026-05-06",
        "is_rebalance_day": False,
        "next_rebalance_date": "2026-06-30",
        "days_to_next_rebalance": 54,
        "sell_actions_count": 2 if has_actions else 0,
        "buy_actions_count": 1 if has_actions else 0,
        "sell_top3": [
            {"etf_code": "1306", "name": "TOPIX", "amount": 30000},
            {"etf_code": "1615", "name": "銀行", "amount": 10000},
        ] if has_actions else [],
        "buy_top3": [
            {"etf_code": "2559", "name": "オルカン", "amount": 50000},
        ] if has_actions else [],
    }


class TestMorningTemplateNewSections:
    """朝テンプレ: overnight / 前夜サマリの有無の組合せで render が成功する."""

    def test_render_with_overnight_only(self, renderer):
        ctx = _morning_ctx(overnight=_overnight_payload())
        md, html = renderer.render(ctx)
        assert "overnight 市況サマリ" in md
        # 主要ティッカーが本文に展開される
        assert "S&P500" in md
        assert "USD/JPY" in md
        # html 側にも overnight テーブルが出る
        assert "overnight" in html.lower() or "S&amp;P500" in html or "S&P500" in html

    def test_render_with_previous_evening_summary_only(self, renderer):
        ctx = _morning_ctx(
            previous_evening_summary=_previous_evening_summary(has_actions=True),
        )
        md, _ = renderer.render(ctx)
        assert "前夜決定事項リマインダー" in md
        assert "売却 2 件" in md
        assert "買付 1 件" in md
        # top3 の銘柄コードが本文に出る
        assert "1306" in md and "2559" in md

    def test_render_with_both_sections(self, renderer):
        ctx = _morning_ctx(
            overnight=_overnight_payload(),
            previous_evening_summary=_previous_evening_summary(has_actions=False),
        )
        md, _ = renderer.render(ctx)
        # 両セクションとも表示される（previous_evening_summary は売買 0 件）
        assert "overnight 市況サマリ" in md
        assert "前夜決定事項リマインダー" in md
        assert "売買アクションなし" in md or "通常運用" in md

    def test_render_without_new_sections(self, renderer):
        """overnight も previous_evening_summary も無くても render 成功."""
        ctx = _morning_ctx()
        md, _ = renderer.render(ctx)
        # 各セクションが出ないこと
        assert "overnight 市況サマリ" not in md
        assert "前夜決定事項リマインダー" not in md


class TestEveningTemplateRebalancePlan:
    """夕方テンプレ: rebalance_plan ありなし両方で render が成功する."""

    def test_render_without_rebalance_plan(self, renderer):
        """rebalance_plan が None でも StrictUndefined エラーが出ない."""
        ctx = _evening_ctx()
        md, _ = renderer.render(ctx)
        # 銘柄別配分セクションは出ない
        assert "採用銘柄配分" not in md
        # 売買プラン概要セクションも出ない（rebalance_plan が無いため）
        assert "売買プラン概要" not in md
        # A群/B群サマリは出る
        assert "A群（コア・ヘッジ）" in md

    def test_render_with_rebalance_plan(self, renderer):
        """rebalance_plan あり: 銘柄別配分・売買プランが描画される."""
        from src.services.portfolio_rebalance_service import (
            HoldingSnapshot,
            RebalanceAction,
        )

        snapshots = (
            HoldingSnapshot(
                etf_code="2559", name="オルカン", quantity=10.0,
                current_price=15000.0, current_value=150_000.0,
                pnl_pct=2.0, target_pct=15.0, actual_pct=15.0,
                drift_pp=0.0, classification="OK", is_adopted=True,
            ),
        )
        actions = (
            RebalanceAction(
                etf_code="2559", action_type="buy", quantity=1,
                amount=15000.0, reason="目標到達",
            ),
        )
        plan = _make_rebalance_plan(
            holdings_snapshots=snapshots, buy_actions=actions,
        )

        ctx = _evening_ctx(
            rebalance_plan=plan,
            buy_top3=(
                {"etf_code": "2559", "name": "オルカン", "amount": 15000},
            ),
            buy_filtered_count=1,
            rebalance_detail_threshold_days=3,
        )
        md, html = renderer.render(ctx)
        # 銘柄別配分テーブルが含まれる
        assert "採用銘柄配分" in md
        assert "2559" in md
        # 売買プラン概要が常時表示
        assert "売買プラン概要" in md
        assert "売却 0 件 / 買付 1 件" in md
        # HTML 側もエラーなく生成
        assert "<h1" in html
        assert "売買プラン概要" in html


class TestEveningTemplateDetailGating:
    """売買プラン詳細表が日数閾値で表示/非表示になるかの分岐検証."""

    def _plan_with_action(self, *, days_to_next: int, is_rebalance_day: bool):
        from src.services.portfolio_rebalance_service import (
            HoldingSnapshot,
            RebalanceAction,
        )

        snapshots = (
            HoldingSnapshot(
                etf_code="2559", name="オルカン", quantity=10.0,
                current_price=15000.0, current_value=150_000.0,
                pnl_pct=2.0, target_pct=15.0, actual_pct=15.0,
                drift_pp=0.0, classification="OK", is_adopted=True,
            ),
        )
        actions = (
            RebalanceAction(
                etf_code="2559", action_type="buy", quantity=1,
                amount=15000.0, reason="目標到達",
            ),
        )
        return _make_rebalance_plan(
            is_rebalance_day=is_rebalance_day,
            days_to_next=days_to_next,
            holdings_snapshots=snapshots,
            buy_actions=actions,
        )

    def test_detail_hidden_when_far_from_rebalance(self, renderer):
        """基準日まで 10 日 (> 閾値 3) → 詳細表セクションは出ず概要のみ."""
        plan = self._plan_with_action(days_to_next=10, is_rebalance_day=False)
        ctx = _evening_ctx(
            rebalance_plan=plan,
            buy_top3=(
                {"etf_code": "2559", "name": "オルカン", "amount": 15000},
            ),
            rebalance_detail_threshold_days=3,
        )
        md, _ = renderer.render(ctx)
        # 概要は出る
        assert "売買プラン概要" in md
        # 「（詳細）」見出し（または「本日のリバランス実行」）は出ない
        assert "（詳細）" not in md
        assert "本日のリバランス実行" not in md

    def test_detail_hidden_at_threshold_plus_one(self, renderer):
        """基準日まで 4 日 (= 閾値 3 の +1, off-by-one 境界) → 詳細表は出ない."""
        plan = self._plan_with_action(days_to_next=4, is_rebalance_day=False)
        ctx = _evening_ctx(
            rebalance_plan=plan,
            buy_top3=(
                {"etf_code": "2559", "name": "オルカン", "amount": 15000},
            ),
            rebalance_detail_threshold_days=3,
        )
        md, _ = renderer.render(ctx)
        assert "売買プラン概要" in md
        assert "（詳細）" not in md

    def test_detail_shown_when_within_threshold(self, renderer):
        """基準日まで 3 日 (== 閾値) → 詳細表セクションが出る."""
        plan = self._plan_with_action(days_to_next=3, is_rebalance_day=False)
        ctx = _evening_ctx(
            rebalance_plan=plan,
            buy_top3=(
                {"etf_code": "2559", "name": "オルカン", "amount": 15000},
            ),
            rebalance_detail_threshold_days=3,
        )
        md, _ = renderer.render(ctx)
        assert "売買プラン概要" in md
        assert "（詳細）" in md

    def test_detail_shown_on_rebalance_day(self, renderer):
        """基準日当日（残り 0 日相当）→ 「本日のリバランス実行」が出る."""
        plan = self._plan_with_action(days_to_next=0, is_rebalance_day=True)
        ctx = _evening_ctx(
            rebalance_plan=plan,
            buy_top3=(
                {"etf_code": "2559", "name": "オルカン", "amount": 15000},
            ),
            rebalance_detail_threshold_days=3,
        )
        md, _ = renderer.render(ctx)
        assert "売買プラン概要" in md
        assert "本日のリバランス実行" in md


# ============================================================
# DISPLAY_THRESHOLD_PP=2.0 フィルタ導入に伴う「該当なし」表示の検証
# ============================================================


class TestEveningTradeSummaryNoCandidates:
    """sell_top3 / buy_top3 が空のとき「該当なし」が表示される."""

    def _plan_without_actions(self):
        """RebalancePlan モック（sell_actions / buy_actions も空）."""
        from src.services.portfolio_rebalance_service import RebalancePlan

        return RebalancePlan(
            target_weights={"2559": 15.0},
            current_weights={"2559": 15.0, "CASH": 10.0},
            deviations={"2559": 0.0},
            sell_actions=(),
            buy_actions=(),
            total_asset=1_000_000.0,
            target_cash=100_000.0,
            target_cash_pct=10.0,
            current_cash=100_000.0,
            cash_deviation_pp=0.0,
            days_to_next_rebalance=10,
            next_rebalance_date=date(2026, 6, 30),
            is_rebalance_day=False,
            daily_pnl_pct=None,
            holdings_snapshots=(),
            warn_count=0,
            critical_count=0,
        )

    def test_evening_renders_no_candidates_md(self, renderer):
        """sell_top3 / buy_top3 が両方空 → MD 側に「該当なし」が 2 回出る."""
        plan = self._plan_without_actions()
        ctx = _evening_ctx(
            rebalance_plan=plan,
            sell_top3=(),
            buy_top3=(),
            rebalance_detail_threshold_days=3,
        )
        md, _ = renderer.render(ctx)
        assert "売買プラン概要" in md
        # 主な売却候補・主な買付候補それぞれの直下に「該当なし」
        assert md.count("該当なし") >= 2

    def test_evening_renders_no_candidates_html(self, renderer):
        """sell_top3 / buy_top3 が両方空 → HTML 側にも「該当なし」が 2 回出る."""
        plan = self._plan_without_actions()
        ctx = _evening_ctx(
            rebalance_plan=plan,
            sell_top3=(),
            buy_top3=(),
            rebalance_detail_threshold_days=3,
        )
        _, html = renderer.render(ctx)
        assert "売買プラン概要" in html
        assert html.count("該当なし") >= 2

    def test_evening_renders_no_candidates_for_sell_only(self, renderer):
        """sell_top3 空 / buy_top3 ありの混在ケース."""
        plan = self._plan_without_actions()
        ctx = _evening_ctx(
            rebalance_plan=plan,
            sell_top3=(),
            buy_top3=(
                {"etf_code": "2559", "name": "オルカン", "amount": 50000},
            ),
            rebalance_detail_threshold_days=3,
        )
        md, _ = renderer.render(ctx)
        # 売却側に「該当なし」が出て、買付側には 2559 が出る
        assert "該当なし" in md
        assert "2559" in md


class TestMorningPreviousSummaryNoCandidates:
    """morning の前夜サマリで sell_top3 / buy_top3 が空のとき「該当なし」が出る."""

    def test_morning_renders_no_candidates_when_top3_empty(self, renderer):
        """sell_actions_count / buy_actions_count > 0 だが top3 配列が空のケース.

        フィルタが入った後の朝メールで実際に起こりうるシナリオではないが、
        テンプレ側の分岐網羅として、top3 が空でも render が壊れないことを確認.
        """
        # 件数 > 0 で top3 を空にする（テンプレ分岐検証用の人工的なデータ）
        summary = {
            "date": "2026-05-06",
            "is_rebalance_day": False,
            "next_rebalance_date": "2026-06-30",
            "days_to_next_rebalance": 54,
            "sell_actions_count": 1,
            "buy_actions_count": 1,
            "sell_top3": [],
            "buy_top3": [],
        }
        ctx = _morning_ctx(previous_evening_summary=summary)
        md, html = renderer.render(ctx)
        assert "前夜決定事項リマインダー" in md
        # 売却候補・買付候補それぞれに「該当なし」が出る
        assert md.count("該当なし") >= 2
        assert html.count("該当なし") >= 2
