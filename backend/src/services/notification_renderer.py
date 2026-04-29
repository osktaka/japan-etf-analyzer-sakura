"""Notification renderer: render NotificationContext into Markdown/HTML."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from src.services.daily_advisor_service import NotificationContext

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "advisor"


class NotificationRenderer:
    """通知コンテキストをMarkdown/HTMLにレンダリング."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("html",), default=False),
            trim_blocks=False,
            lstrip_blocks=False,
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

    @staticmethod
    def _context_to_params(ctx: NotificationContext) -> dict:
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
        }

    def subject_for(self, ctx: NotificationContext) -> str:
        """件名を生成."""
        date_str = ctx.today.strftime("%Y-%m-%d")
        if ctx.kind == "morning":
            return f"[ETF朝] {date_str} {ctx.user_id} のタスク"
        if ctx.kind == "evening":
            return f"[ETF夕] {date_str} {ctx.user_id} の終値レビュー"
        if ctx.kind == "weekly":
            return f"[ETF週次] {date_str} {ctx.user_id} の週次振り返り"
        if ctx.kind == "alert":
            severities = {t.severity for t in ctx.triggers}
            sev = "critical" if "critical" in severities else (
                "warn" if "warn" in severities else "info"
            )
            return f"[ETF{sev}] 機械ルールアラート {date_str}"
        return f"[ETF] {ctx.kind} {date_str}"
