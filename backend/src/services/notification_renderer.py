"""Notification renderer: render NotificationContext into Markdown/HTML."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from src.services.daily_advisor_service import NotificationContext, RuleTrigger

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
        """
        return {
            "kind": ctx.kind,
            "today": ctx.today,
            "user_id": ctx.user_id,
            "strategy_revision": ctx.strategy_revision,
            "benchmark": ctx.benchmark,
            "sells_today": ctx.sells_today,
            "buys_today": ctx.buys_today,
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
            "extra": ctx.extra,
            # 新規: 件名タグ・リード文
            "urgency_tag": self.urgency_tag(ctx),
            "summary": self.summary_for(ctx),
            "recommended_action": self.recommended_action,
        }

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
        has_action = bool(ctx.sells_today or ctx.buys_today)

        if has_critical:
            return "緊急"
        if ctx.kind == "morning" and has_action:
            return "要対応"
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
    # リード文
    # ------------------------------------------------------------
    def summary_for(self, ctx: NotificationContext) -> str:
        """リード文 (1〜2文)."""
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
    def _summary_morning(ctx: NotificationContext) -> str:
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        if critical is not None:
            return (
                f"緊急: 機械ルール{critical.rule_kind}が発動中。寄付前に対応判断を。"
            )

        n_sell = len(ctx.sells_today)
        n_buy = len(ctx.buys_today)
        if n_sell and n_buy:
            return f"今日 売却{n_sell}件・買付{n_buy}件の発注予定。"
        if n_sell:
            return f"今日 売却{n_sell}件の発注予定。"
        if n_buy:
            return f"今日 買付{n_buy}件のDCA予定。"

        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        warn_other_rules = [
            t for t in ctx.triggers
            if t.severity == "warn" and t.rule_kind != "allocation_drift"
        ]
        if warn_drifts or warn_other_rules:
            n_warn = len(warn_drifts) if warn_drifts else len(warn_other_rules)
            return (
                f"配分逸脱{n_warn}件継続中。発注はなし、週次メールで方針確認。"
            )

        return "今日は発注予定なし。市場は静観でOK。"

    @staticmethod
    def _summary_evening(ctx: NotificationContext) -> str:
        critical = next(
            (t for t in ctx.triggers if t.severity == "critical"), None
        )
        if critical is not None:
            return f"緊急: 機械ルール{critical.rule_kind}が発動。即対応検討を。"

        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        warn_other_rules = [
            t for t in ctx.triggers
            if t.severity == "warn" and t.rule_kind != "allocation_drift"
        ]
        n_drift = len(warn_drifts)
        n_rule = len(warn_other_rules)

        if ctx.daily_change_pct is not None:
            if n_drift or n_rule:
                parts = []
                if n_drift:
                    parts.append(f"配分逸脱{n_drift}件")
                if n_rule:
                    parts.append(f"ルール警告{n_rule}件")
                return (
                    f"本日 {ctx.daily_change_pct:+.2f}%。"
                    f"{' / '.join(parts)}あり、明日の見直し対象。"
                )
            return f"本日 {ctx.daily_change_pct:+.2f}%。配分・ルール異常なし。"

        suffix = "あり" if (n_drift or n_rule) else "なし"
        return f"終値ベースのレビュー。配分逸脱{n_drift}件{suffix}。"

    @staticmethod
    def _summary_weekly(ctx: NotificationContext) -> str:
        warn_drifts = [d for d in ctx.allocation_drifts if d.is_warn]
        n_warn = len(warn_drifts)
        suffix = "あり" if n_warn > 0 else "なし"

        if ctx.alpha_pp is None:
            return f"5営業日リターン算出不可。配分逸脱{n_warn}件{suffix}。"

        if ctx.alpha_pp <= -2.0:
            return (
                f"今週 α {ctx.alpha_pp:+.2f}pp（{ctx.benchmark}に負け）。"
                f"配分是正の買付/売却を推奨。"
            )
        if ctx.alpha_pp <= 2.0:
            return (
                f"今週 α {ctx.alpha_pp:+.2f}pp（ベンチマーク並み）。"
                f"配分逸脱{n_warn}件{suffix}。"
            )
        return (
            f"今週 α {ctx.alpha_pp:+.2f}pp（アウトパフォーム）。"
            f"配分逸脱{n_warn}件{suffix}。"
        )

    @staticmethod
    def _summary_alert(ctx: NotificationContext) -> str:
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
        return f"{sev_label}アラート{n}件: {kinds_str}"

    # ------------------------------------------------------------
    # 推奨アクション
    # ------------------------------------------------------------
    @staticmethod
    def recommended_action(trigger: RuleTrigger) -> str:
        """RuleTrigger 1件に対する推奨アクション文字列."""
        return _RECOMMENDED_ACTION.get(trigger.rule_kind, _DEFAULT_RECOMMENDED_ACTION)

    # ------------------------------------------------------------
    # 件名
    # ------------------------------------------------------------
    def subject_for(self, ctx: NotificationContext) -> str:
        """件名を生成 (タグ付き新形式)."""
        date_str = ctx.today.strftime("%Y-%m-%d")
        tag = self.urgency_tag(ctx)
        if ctx.kind == "morning":
            return f"[ETF朝/{tag}] {date_str} {ctx.user_id}"
        if ctx.kind == "evening":
            return f"[ETF夕/{tag}] {date_str} {ctx.user_id}"
        if ctx.kind == "weekly":
            return f"[ETF週次/{tag}] {date_str} {ctx.user_id}"
        if ctx.kind == "alert":
            return f"[ETF/{tag}] 機械ルール {date_str}"
        return f"[ETF/{tag}] {ctx.kind} {date_str}"
