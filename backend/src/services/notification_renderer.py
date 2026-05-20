"""Notification renderer: render NotificationContext into Markdown/HTML."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from src.services.daily_advisor_service import NotificationContext, RuleTrigger

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "advisor"

# rule_kind -> 推奨アクション文字列
_RECOMMENDED_ACTION = {
    "loss_cut": "売却検討。継続保有なら戦略書の例外メモを更新してください。",
    "take_profit_1": "段階的売却（第1段）を検討してください。",
    "take_profit_2": "段階的売却（第2段）を検討してください。",
    "n225_drawdown": "静観 or 戦略書の急落時方針を確認してください。",
    "allocation_drift": "配分是正の買付/売却タイミングを検討してください。",
}
_DEFAULT_RECOMMENDED_ACTION = "戦略書を確認してください。"

# alert kind: severity -> tag
_ALERT_SEVERITY_TAG = {
    "critical": "緊急",
    "warn": "要確認",
    "info": "情報",
}

# 件名長の目安上限（全角 + 半角ASCIIを len() でカウント、25字相当として40文字）
SUBJECT_MAX_LEN = 40


class NotificationRenderer:
    """通知コンテキストをMarkdown/HTMLにレンダリング."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("html",), default=False),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def render(self, ctx: NotificationContext) -> Tuple[str, str]:
        """(markdown, html) を返す."""
        kind = ctx.kind
        md_template = self.env.get_template(f"{kind}.md.j2")
        html_template = self.env.get_template(f"{kind}.html.j2")
        params = self._context_to_params(ctx)
        md = md_template.render(**params)
        html = html_template.render(**params)
        return md, html

    def _context_to_params(self, ctx: NotificationContext) -> dict:
        """NotificationContext を Jinja2 渡し用の dict にする.

        StrictUndefined を使っているため、テンプレートで参照される全フィールドを
        明示的に渡す必要がある.

        配分閾値は ctx.drift_ok_pp / ctx.drift_warn_pp（strategy SSOT 由来）を
        そのまま渡す。導出フォールバック（warn*0.6）は廃止済み。
        """
        return {
            "kind": ctx.kind,
            "today": ctx.today,
            "user_id": ctx.user_id,
            "strategy_revision": ctx.strategy_revision,
            "benchmark": ctx.benchmark,
            "total_asset": ctx.total_asset,
            "total_value": ctx.total_value,
            "cash_balance": ctx.cash_balance,
            "daily_change_pct": ctx.daily_change_pct,
            "holdings_count": ctx.holdings_count,
            "allocation_drifts": ctx.allocation_drifts,
            "triggers": ctx.triggers,
            "alpha_pp": ctx.alpha_pp,
            "period_label": ctx.period_label,
            "benchmark_return_pct": ctx.benchmark_return_pct,
            "portfolio_return_pct": ctx.portfolio_return_pct,
            "month_start_total_asset": ctx.month_start_total_asset,
            "month_start_change_pct": ctx.month_start_change_pct,
            "extra": ctx.extra,
            # リバランス計画（朝/夕構成見直し後:
            # - evening: 銘柄別配分テーブル・採用外保有・売却/買付プランの本体表示
            # - morning: 次回リバランス日カウントダウン・四半期末日の本日アクション表示用要約）
            "rebalance_plan": ctx.rebalance_plan,
            # 朝メール: overnight 市況サマリ（None なら overnight セクション skip）
            "overnight": ctx.overnight,
            # 朝メール: 前夜決定事項リマインダー（None ならリマインダー欄 skip）
            "previous_evening_summary": ctx.previous_evening_summary,
            # 夕方メール: 売買プラン概要セクション（常時表示）の top3
            "sell_top3": ctx.sell_top3,
            "buy_top3": ctx.buy_top3,
            # 夕方メール: 「売却 X 件 / 買付 Y 件」表示用（filter 適用後の総数、
            # top3 と整合させるため）
            "sell_filtered_count": ctx.sell_filtered_count,
            "buy_filtered_count": ctx.buy_filtered_count,
            # 夕方メール: 詳細表ガード閾値（is_rebalance_day or
            # days_to_next_rebalance <= threshold で詳細表を表示）
            "rebalance_detail_threshold_days": ctx.rebalance_detail_threshold_days,
            # 配分閾値（テンプレ動的化用、全 kind 共通、strategy SSOT 直結）
            "drift_warn_pp": ctx.drift_warn_pp,
            "drift_ok_pp": ctx.drift_ok_pp,
            # 件名タグ・リード文
            "urgency_tag": self.urgency_tag(ctx),
            "summary": self.summary_for(ctx),
            "action_count": self.action_count(ctx),
            "estimated_minutes": self.estimated_minutes(ctx),
            "recommended_action": self.recommended_action,
        }

    # ------------------------------------------------------------
    # 件数・所要時間ヘルパ
    # ------------------------------------------------------------
    def action_count(self, ctx: NotificationContext) -> int:
        """当日アクション数. morning kind では rebalance_plan の本日実行件数."""
        if ctx.kind == "morning":
            plan = ctx.rebalance_plan
            if plan is not None and plan.is_rebalance_day:
                return len(plan.sell_actions) + len(plan.buy_actions)
            return 0
        return 0

    def estimated_minutes(self, ctx: NotificationContext) -> int:
        """所要時間の目安（分）. 0件なら0、それ以外は3〜30分の範囲にクリップ."""
        n = self.action_count(ctx)
        if n == 0:
            return 0
        return max(3, min(30, round(2 + 2.5 * n)))

    # ------------------------------------------------------------
    # 緊急度タグ
    # ------------------------------------------------------------
    def urgency_tag(self, ctx: NotificationContext) -> str:
        """対応要否タグ (緊急/要対応/要確認/静観/情報)."""
        # alert は最大severity直結
        if ctx.kind == "alert":
            severities = {t.severity for t in ctx.triggers}
            if "critical" in severities:
                return "緊急"
            if "warn" in severities:
                return "要確認"
            return "情報"

        has_critical = any(t.severity == "critical" for t in ctx.triggers)
        has_warn = any(t.severity == "warn" for t in ctx.triggers)

        # morning: 統合された rebalance_plan を主軸に評価
        if ctx.kind == "morning":
            plan = ctx.rebalance_plan
            if has_critical:
                return "緊急"
            if plan is not None and plan.is_rebalance_day and (
                plan.sell_actions or plan.buy_actions
            ):
                return "要対応"
            if plan is not None and plan.critical_count > 0:
                return "要確認"
            if has_warn:
                return "要確認"
            if plan is not None and plan.warn_count > 0:
                return "要確認"
            return "静観"

        if has_critical:
            return "緊急"
        if has_warn:
            return "要確認"
        if (
            ctx.kind == "weekly"
            and ctx.alpha_pp is not None
            and ctx.alpha_pp <= -2.0
        ):
            return "要確認"
        return "静観"

    # ------------------------------------------------------------
    # リード文（3行構造）
    # ------------------------------------------------------------
    def summary_for(self, ctx: NotificationContext) -> str:
        """リード文 (3行構造: 結論 / 文脈 / 根拠).

        Markdown形式。改行は \\n\\n で段落分け。
        3行目（根拠）は省略可（critical/warnのときのみ表示）。
        """
        if ctx.kind == "morning":
            return self._summary_morning(ctx)
        if ctx.kind == "evening":
            return self._summary_evening(ctx)
        if ctx.kind == "weekly":
            return self._summary_weekly(ctx)
        if ctx.kind == "alert":
            return self._summary_alert(ctx)
        return ""

    @staticmethod
    def _join_lines(lines: list) -> str:
        return "\n\n".join(line for line in lines if line)

    @classmethod
    def _context_line(
        cls,
        ctx: NotificationContext,
        *,
        include_alpha: bool = False,
    ) -> str:
        """2行目（文脈）: 資産・前日比・月初比・α・配分状態."""
        parts = []
        # 資産
        parts.append(f"資産{int(ctx.total_asset):,}円")

        # 前日比
        if ctx.daily_change_pct is not None:
            parts.append(f"前日{ctx.daily_change_pct:+.2f}%")

        # 月初比
        if ctx.month_start_change_pct is not None:
            parts.append(f"月初{ctx.month_start_change_pct:+.2f}%")

        # α (weekly)
        if include_alpha and ctx.alpha_pp is not None:
            parts.append(f"α{ctx.alpha_pp:+.2f}pp")

        # 配分状態
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        if warn_drifts:
            parts.append(f"配分逸脱{len(warn_drifts)}件")
        else:
            parts.append("配分は許容範囲内")

        return "、".join(parts) + "。"

    @classmethod
    def _reason_line(cls, ctx: NotificationContext) -> str:
        """3行目（根拠）: critical/warn の発動理由を簡潔に. なければ空文字."""
        # critical 優先
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        if critical is not None:
            payload = critical.payload or {}
            change = payload.get("change_pct")
            threshold = payload.get("threshold_pct")
            if critical.rule_kind == "n225_drawdown" and change is not None:
                return (
                    f"N225が{change:+.1f}%急落、"
                    "戦略書5.3条のリスクオフ条項に該当。"
                )
            return (
                f"機械ルール{critical.rule_kind}が発動: {critical.message}。"
            )

        # 配分逸脱（warn）
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        if warn_drifts:
            worst = max(warn_drifts, key=lambda d: abs(d.drift_pp))
            warn_pp = worst.warn_threshold_pp
            over = abs(worst.drift_pp) - warn_pp
            return (
                f"警告閾値±{warn_pp:.1f}ppを{over:.1f}pp超過（{worst.bucket}）。"
            )

        # 他のwarn
        warn_other = [
            t for t in ctx.triggers
            if t.severity == "warn" and t.rule_kind != "allocation_drift"
        ]
        if warn_other:
            t = warn_other[0]
            return f"機械ルール{t.rule_kind}が警告レベルで発動: {t.message}。"

        return ""

    @classmethod
    def _summary_morning(cls, ctx: NotificationContext) -> str:
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        plan = ctx.rebalance_plan

        # 1行目: 結論
        if critical is not None:
            conclusion = (
                f"緊急: 機械ルール{critical.rule_kind}が発動中。寄付前に対応判断を。"
            )
        elif plan is not None and plan.is_rebalance_day and (
            plan.sell_actions or plan.buy_actions
        ):
            n_rb_sell = len(plan.sell_actions)
            n_rb_buy = len(plan.buy_actions)
            conclusion = (
                f"本日は四半期末リバランス基準日。売却{n_rb_sell}件・買付{n_rb_buy}件を執行検討。"
            )
        else:
            warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
            warn_other_rules = [
                t for t in ctx.triggers
                if t.severity == "warn" and t.rule_kind != "allocation_drift"
            ]
            n_rb_critical = plan.critical_count if plan is not None else 0
            n_rb_warn = plan.warn_count if plan is not None else 0
            if warn_drifts or warn_other_rules:
                n_warn = (
                    len(warn_drifts) if warn_drifts else len(warn_other_rules)
                )
                conclusion = (
                    f"配分逸脱{n_warn}件継続中。"
                    "発注はなし、週次メールで方針確認。"
                )
            elif n_rb_critical > 0 or n_rb_warn > 0:
                if plan is not None:
                    conclusion = (
                        f"次回リバランスまで{plan.days_to_next_rebalance}日。"
                        f"配分逸脱 CRITICAL{n_rb_critical}件 / WARN{n_rb_warn}件、本日は監視のみ。"
                    )
                else:
                    conclusion = (
                        f"配分逸脱 CRITICAL{n_rb_critical}件 / WARN{n_rb_warn}件、本日は監視のみ。"
                    )
            elif plan is not None:
                conclusion = (
                    f"本日は通常運用日。次回リバランス（{plan.next_rebalance_date.strftime('%Y-%m-%d')}）まで{plan.days_to_next_rebalance}日。"
                )
            else:
                conclusion = "今日は発注予定なし。市場は静観でOK。通常運用継続。"

        context_line = cls._context_line(ctx)
        reason = cls._reason_line(ctx)
        return cls._join_lines([conclusion, context_line, reason])

    @classmethod
    def _summary_evening(cls, ctx: NotificationContext) -> str:
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        warn_other_rules = [
            t for t in ctx.triggers
            if t.severity == "warn" and t.rule_kind != "allocation_drift"
        ]
        n_drift = len(warn_drifts)
        n_rule = len(warn_other_rules)

        # 1行目: 結論
        if critical is not None:
            conclusion = (
                f"緊急: 機械ルール{critical.rule_kind}が発動。即対応検討を。"
            )
        else:
            if ctx.daily_change_pct is not None:
                if n_drift or n_rule:
                    parts = []
                    if n_drift:
                        parts.append(f"配分逸脱{n_drift}件")
                    if n_rule:
                        parts.append(f"ルール警告{n_rule}件")
                    conclusion = (
                        f"本日 {ctx.daily_change_pct:+.2f}%。"
                        f"{' / '.join(parts)}あり、明日の見直し対象。"
                    )
                else:
                    conclusion = (
                        f"本日 {ctx.daily_change_pct:+.2f}%。"
                        "配分・ルール異常なし。"
                    )
            else:
                suffix = "あり" if (n_drift or n_rule) else "なし"
                conclusion = (
                    f"終値ベースのレビュー。配分逸脱{n_drift}件{suffix}。"
                )

        context_line = cls._context_line(ctx)
        reason = cls._reason_line(ctx)
        return cls._join_lines([conclusion, context_line, reason])

    @classmethod
    def _summary_weekly(cls, ctx: NotificationContext) -> str:
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        n_warn = len(warn_drifts)
        suffix = "あり" if n_warn > 0 else "なし"

        # 1行目: 結論
        if ctx.alpha_pp is None:
            conclusion = (
                f"5営業日リターン算出不可。配分逸脱{n_warn}件{suffix}。"
            )
        elif ctx.alpha_pp <= -2.0:
            conclusion = (
                f"今週 α {ctx.alpha_pp:+.2f}pp（{ctx.benchmark}に負け）。"
                "配分是正の買付/売却を推奨。"
            )
        elif ctx.alpha_pp <= 2.0:
            conclusion = (
                f"今週 α {ctx.alpha_pp:+.2f}pp（ベンチマーク並み）。"
                f"配分逸脱{n_warn}件{suffix}。"
            )
        else:
            conclusion = (
                f"今週 α {ctx.alpha_pp:+.2f}pp（アウトパフォーム）。"
                f"配分逸脱{n_warn}件{suffix}。"
            )

        context_line = cls._context_line(ctx, include_alpha=True)
        reason = cls._reason_line(ctx)
        return cls._join_lines([conclusion, context_line, reason])

    @classmethod
    def _summary_alert(cls, ctx: NotificationContext) -> str:
        n = len(ctx.triggers)
        if n == 0:
            return "アラートなし。"

        severities = {t.severity for t in ctx.triggers}
        if "critical" in severities:
            sev_label = "critical"
        elif "warn" in severities:
            sev_label = "warn"
        else:
            sev_label = "info"

        kinds = [t.rule_kind for t in ctx.triggers]
        if len(kinds) <= 3:
            kinds_str = ", ".join(kinds)
        else:
            kinds_str = ", ".join(kinds[:3]) + f" ... 他{len(kinds) - 3}件"
        conclusion = f"{sev_label}アラート{n}件: {kinds_str}"

        # alertは資産情報がない可能性が高い → context_lineは出さない
        # 根拠だけ追加
        reason = cls._reason_line(ctx)
        return cls._join_lines([conclusion, reason])

    # ------------------------------------------------------------
    # 推奨アクション
    # ------------------------------------------------------------
    @staticmethod
    def recommended_action(trigger: RuleTrigger) -> str:
        """RuleTrigger 1件に対する推奨アクション文字列."""
        return _RECOMMENDED_ACTION.get(trigger.rule_kind, _DEFAULT_RECOMMENDED_ACTION)

    # ------------------------------------------------------------
    # 件名（短縮 M/D + アクション/警告/α 表記）
    # ------------------------------------------------------------
    def subject_for(self, ctx: NotificationContext) -> str:
        """件名を生成（短縮M/D + 状況サマリ）.

        フォーマット例（朝/夕構成見直し後）:
        - morning静観:    `【寄り付き前】Daily Advisor / 4/30`
        - morningリバランス: `【寄り付き前】Daily Advisor / 4/30 リバランス売2買3`
        - morning警告:    `【寄り付き前】Daily Advisor / 4/30 逸脱2件`
        - evening静観:    `【終値ベース】Daily Advisor / 4/30 +0.5%`
        - evening警告:    `【終値ベース】Daily Advisor / 4/30 -1.2% 逸脱2件`
        - weekly:        `[4/30 週次] α +0.3pp` または `[4/30 週次] α -2.5pp / 来週3件`
        - alert単発:     `[4/30 緊急] 損切到達: 1306`
        - alert複数:     `[4/30 緊急] 機械ルール3件発動`
        """
        date_str = f"{ctx.today.month}/{ctx.today.day}"

        if ctx.kind == "morning":
            subject = self._subject_morning(ctx, date_str)
        elif ctx.kind == "evening":
            subject = self._subject_evening(ctx, date_str)
        elif ctx.kind == "weekly":
            subject = self._subject_weekly(ctx, date_str)
        elif ctx.kind == "alert":
            subject = self._subject_alert(ctx, date_str)
        else:
            subject = f"[{date_str} {ctx.kind}]"

        # 件名40字超は自動切り詰め（末尾省略）
        if len(subject) > SUBJECT_MAX_LEN:
            logger.warning(
                "subject exceeds %d chars (len=%d), truncating: %s",
                SUBJECT_MAX_LEN, len(subject), subject,
            )
            subject = subject[: SUBJECT_MAX_LEN - 1] + "…"
        return subject

    def _subject_morning(self, ctx: NotificationContext, date_str: str) -> str:
        """朝メール件名: 「【寄り付き前】Daily Advisor / {today}」基準.

        critical / リバランス実行日 / warn / 通常 の状態を末尾の補足タグで示す.
        """
        plan = ctx.rebalance_plan
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        if critical is not None:
            return f"【寄り付き前】Daily Advisor / {date_str} 緊急"
        # 四半期末リバランス基準日: アクションがあれば件名末尾に補足
        if plan is not None and plan.is_rebalance_day and (
            plan.sell_actions or plan.buy_actions
        ):
            n_sell = len(plan.sell_actions)
            n_buy = len(plan.buy_actions)
            return (
                f"【寄り付き前】Daily Advisor / {date_str} "
                f"リバランス売{n_sell}買{n_buy}"
            )
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        warn_other = [
            t for t in ctx.triggers
            if t.severity == "warn" and t.rule_kind != "allocation_drift"
        ]
        n_rb_critical = plan.critical_count if plan is not None else 0
        if warn_drifts or warn_other:
            n_warn = len(warn_drifts) or len(warn_other)
            return f"【寄り付き前】Daily Advisor / {date_str} 逸脱{n_warn}件"
        if n_rb_critical > 0:
            return (
                f"【寄り付き前】Daily Advisor / {date_str} 逸脱{n_rb_critical}件"
            )
        return f"【寄り付き前】Daily Advisor / {date_str}"

    def _subject_evening(self, ctx: NotificationContext, date_str: str) -> str:
        """夕方メール件名: 「【終値ベース】Daily Advisor / {today}」基準."""
        if ctx.daily_change_pct is not None:
            change_str = f"{ctx.daily_change_pct:+.1f}%"
        else:
            change_str = "-"

        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        warn_other = [
            t for t in ctx.triggers
            if t.severity == "warn" and t.rule_kind != "allocation_drift"
        ]
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        if critical is not None:
            return f"【終値ベース】Daily Advisor / {date_str} 緊急"
        if warn_drifts or warn_other:
            n_warn = len(warn_drifts) or len(warn_other)
            return (
                f"【終値ベース】Daily Advisor / {date_str} "
                f"{change_str} 逸脱{n_warn}件"
            )
        return f"【終値ベース】Daily Advisor / {date_str} {change_str}"

    def _subject_weekly(self, ctx: NotificationContext, date_str: str) -> str:
        if ctx.alpha_pp is None:
            alpha_str = "α 算出不可"
        else:
            alpha_str = f"α {ctx.alpha_pp:+.1f}pp"

        # 来週のアクション件数（sells/buys は週次にはないが、警告件数を併記）
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        n_warn = len(warn_drifts)
        if ctx.alpha_pp is not None and ctx.alpha_pp <= -2.0:
            if n_warn > 0:
                return f"[{date_str} 週次] {alpha_str} / 来週{n_warn}件"
            return f"[{date_str} 週次] {alpha_str}"
        if n_warn > 0:
            return f"[{date_str} 週次] {alpha_str} / 配分{n_warn}件"
        return f"[{date_str} 週次] {alpha_str}"

    def _subject_alert(self, ctx: NotificationContext, date_str: str) -> str:
        n = len(ctx.triggers)
        tag = self.urgency_tag(ctx)  # 緊急/要確認/情報

        if n == 0:
            return f"[{date_str} {tag}] アラートなし"
        if n >= 2:
            return f"[{date_str} {tag}] 機械ルール{n}件発動"

        # 単発トリガー
        t = ctx.triggers[0]
        # 既知ルールで簡潔表記
        rule_label = {
            "loss_cut": "損切到達",
            "take_profit_1": "利確第1段",
            "take_profit_2": "利確第2段",
            "n225_drawdown": "N225急落",
            "allocation_drift": "配分逸脱",
        }.get(t.rule_kind, t.rule_kind)

        if t.code:
            return f"[{date_str} {tag}] {rule_label}: {t.code}"
        return f"[{date_str} {tag}] {rule_label}"
