"""AdvisorRunner: 通知系バッチの共通ランナー.

Step 4 の中核. 戦略ロード → コンテキスト組立 → Markdownファイル出力 → メール送信.
部分成功時は warning を返し、致命的失敗のみ非ゼロ終了.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")

KindT = Literal["morning", "evening", "weekly", "alert"]


def _import_late():
    """循環参照や副作用回避のためのlate import."""
    from src.external.email_client import EmailClient
    from src.external.yahoo_finance import YahooFinanceClient
    from src.repositories import (
        BatchLogRepository,
        MechanicalRuleEventRepository,
    )
    from src.repositories.user_repository import UserRepository
    from src.services.daily_advisor_service import (
        build_alert_context,
        build_evening_context,
        build_morning_context,
        build_weekly_context,
        classify_buckets,
        compute_allocation_drift,
        compute_return_from_history,
        evaluate_mechanical_rules,
        make_fingerprint,
    )
    from src.services.notification_renderer import NotificationRenderer
    from src.services.portfolio_rebalance_service import (
        PortfolioRebalanceService,
    )
    from src.services.portfolio_service import PortfolioService
    from src.services.strategy_loader import StrategyLoader

    return {
        "EmailClient": EmailClient,
        "YahooFinanceClient": YahooFinanceClient,
        "BatchLogRepository": BatchLogRepository,
        "MechanicalRuleEventRepository": MechanicalRuleEventRepository,
        "UserRepository": UserRepository,
        "build_alert_context": build_alert_context,
        "build_evening_context": build_evening_context,
        "build_morning_context": build_morning_context,
        "build_weekly_context": build_weekly_context,
        "classify_buckets": classify_buckets,
        "compute_allocation_drift": compute_allocation_drift,
        "compute_return_from_history": compute_return_from_history,
        "evaluate_mechanical_rules": evaluate_mechanical_rules,
        "make_fingerprint": make_fingerprint,
        "NotificationRenderer": NotificationRenderer,
        "PortfolioRebalanceService": PortfolioRebalanceService,
        "PortfolioService": PortfolioService,
        "StrategyLoader": StrategyLoader,
    }


def _resolve_user_id(user_repo_cls, user_id_str: str) -> Optional[int]:
    """user_id 文字列(=user_id列) → users.id (int) を解決.

    PortfolioService は users.id (int) を要求するため.
    """
    repo = user_repo_cls()
    user = repo.get_by_user_id(user_id_str) if hasattr(repo, "get_by_user_id") else None
    if user is None:
        # 代替: 全件取得して文字列マッチ
        try:
            from src.models.user import User
            from src.models import db
            user = (
                db.session.query(User)
                .filter(User.user_id == user_id_str)
                .first()
            )
        except Exception:
            return None
    return user.id if user else None


class AdvisorRunner:
    """通知バッチの共通ランナー."""

    def __init__(
        self,
        *,
        project_root: Path,
        strategy_file: Path,
        reports_dir: Path,
        user_id_str: str,
        dry_run: bool = False,
    ):
        self.project_root = project_root
        self.strategy_file = strategy_file
        self.reports_dir = reports_dir
        self.user_id_str = user_id_str
        self.dry_run = dry_run
        # alert で永続化した event の id（送信成功時に notified=True へ更新する）
        self._alert_pending_event_ids: List[int] = []

    def run(self, kind: KindT) -> int:
        """0=完全成功, 1=致命的失敗 (部分成功 0)."""
        deps = _import_late()
        try:
            strategy = deps["StrategyLoader"].load(self.strategy_file)
        except Exception as e:
            logger.exception("Strategy load failed: %s", e)
            return 1

        today = datetime.now(JST).date()
        ctx = self._build_context(kind, strategy, deps, today)
        if ctx is None:
            logger.error("Failed to build context for kind=%s", kind)
            return 1

        # alert kind で triggers が空なら何もしない
        if kind == "alert" and len(ctx.triggers) == 0:
            logger.info("alert: no triggers, skipping notification")
            return 0

        renderer = deps["NotificationRenderer"]()
        try:
            md, html = renderer.render(ctx)
        except Exception as e:
            logger.exception("Render failed: %s", e)
            return 1

        # ファイル出力
        out_path = self._write_markdown(kind, today, md)
        logger.info("Markdown written: %s", out_path)

        # メール送信
        subject = renderer.subject_for(ctx)
        if self.dry_run:
            logger.info("[DRY-RUN] Would send email: %s", subject)
            return 0

        client = deps["EmailClient"]()
        ok = client.send(subject, md, html)
        if ok and kind == "alert" and self._alert_pending_event_ids:
            # 送信成功時のみ notified=True に更新（失敗時は次回再送される）
            try:
                repo = deps["MechanicalRuleEventRepository"]()
                for ev_id in self._alert_pending_event_ids:
                    repo.mark_notified(ev_id)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to mark notified: %s", e)
        if not ok:
            logger.warning("Email send failed but file written; will retry next cycle")
        return 0

    # ------------------------------------------------------------
    # Context builders by kind
    # ------------------------------------------------------------
    def _build_context(self, kind: KindT, strategy, deps, today: date):
        if kind == "alert":
            return self._build_alert_context(strategy, deps, today)

        # morning/evening/weekly は portfolio が必要
        user_id_int = _resolve_user_id(deps["UserRepository"], self.user_id_str)
        if user_id_int is None:
            logger.warning(
                "User %r not found, building empty context", self.user_id_str
            )
            summary = {"total_asset": 0.0, "total_value": 0.0, "cash_balance": 0.0,
                       "holdings_count": 0}
            holdings: List[Dict] = []
        else:
            try:
                ps = deps["PortfolioService"]()
                summary = ps.get_portfolio_summary(user_id_int)
                holdings = ps.get_holdings(user_id_int)
            except Exception as e:
                logger.exception("Portfolio query failed: %s", e)
                summary = {"total_asset": 0.0, "total_value": 0.0,
                           "cash_balance": 0.0, "holdings_count": 0}
                holdings = []

        if kind == "morning":
            # リバランス計画（配分テーブル・採用外保有・カウントダウン・四半期末アクション）を統合
            rebalance_plan = None
            if user_id_int is not None:
                try:
                    rebalance_plan = deps["PortfolioRebalanceService"](
                        strategy
                    ).calculate_rebalance_plan(
                        user_id=user_id_int,
                        as_of_date=today,
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Rebalance plan calculation failed (continuing without it): %s",
                        e,
                    )
            return deps["build_morning_context"](
                strategy=strategy, today=today, user_id=self.user_id_str,
                summary=summary, rebalance_plan=rebalance_plan, triggers=(),
            )

        # evening/weekly: 配分・トリガー計算
        actual = deps["classify_buckets"](
            holdings=holdings,
            cash_balance=float(summary.get("cash_balance", 0.0)),
            strategy=strategy,
        )
        drifts = deps["compute_allocation_drift"](
            strategy=strategy,
            actual_buckets=actual,
        )
        n225_change = self._fetch_n225_change(deps)
        triggers = deps["evaluate_mechanical_rules"](
            strategy=strategy, holdings=holdings,
            n225_change_pct=n225_change,
            allocation_drifts=drifts,
            today=today, user_id=self.user_id_str,
        )

        if kind == "evening":
            return deps["build_evening_context"](
                strategy=strategy, today=today, user_id=self.user_id_str,
                summary=summary, drifts=drifts, triggers=triggers,
            )

        # weekly
        portfolio_ret = self._fetch_portfolio_return(deps, user_id_int)
        benchmark_ret = self._fetch_benchmark_return()
        return deps["build_weekly_context"](
            strategy=strategy, today=today, user_id=self.user_id_str,
            summary=summary, drifts=drifts, triggers=triggers,
            portfolio_return_pct=portfolio_ret,
            benchmark_return_pct=benchmark_ret,
            period_label="過去5営業日",
        )

    def _build_alert_context(self, strategy, deps, today: date):
        """watcher用: 個別銘柄/N225チェック → 新規 trigger のみ."""
        user_id_int = _resolve_user_id(deps["UserRepository"], self.user_id_str)
        if user_id_int is None:
            holdings: List[Dict] = []
            summary = {"cash_balance": 0.0}
        else:
            try:
                ps = deps["PortfolioService"]()
                holdings = ps.get_holdings(user_id_int)
                summary = ps.get_portfolio_summary(user_id_int)
            except Exception:
                holdings = []
                summary = {"cash_balance": 0.0}

        n225_change = self._fetch_n225_change(deps)
        # watcher は配分逸脱を見ない（場中ではノイズ多）
        all_triggers = deps["evaluate_mechanical_rules"](
            strategy=strategy, holdings=holdings,
            n225_change_pct=n225_change,
            allocation_drifts=(),  # 配分は夕方バッチに任せる
            today=today, user_id=self.user_id_str,
        )

        # 重複抑止: 送信済(notified=True)はスキップ、未送信は再送対象として扱う
        repo = deps["MechanicalRuleEventRepository"]()
        new_triggers = []
        self._alert_pending_event_ids = []
        for t in all_triggers:
            if repo.exists_for_today(t.fingerprint):
                logger.info("Skip duplicate trigger: %s", t.fingerprint)
                continue
            # 既存のevent（notified=False）があれば再利用、なければ新規作成
            try:
                existing = repo.get_by_fingerprint(t.fingerprint)
                if existing is not None:
                    event = existing
                else:
                    event = repo.create_event(
                        fingerprint=t.fingerprint,
                        occurred_on=today,
                        rule_kind=t.rule_kind,
                        user_id=self.user_id_str,
                        etf_code=t.code,
                        severity=t.severity,
                        payload_json=json.dumps(
                            t.payload, default=str, ensure_ascii=False
                        ),
                    )
            except Exception as e:  # noqa: BLE001
                logger.exception("Failed to record event: %s", e)
                continue
            self._alert_pending_event_ids.append(event.id)
            new_triggers.append(t)

        return deps["build_alert_context"](
            strategy=strategy, today=today, user_id=self.user_id_str,
            triggers=tuple(new_triggers),
        )

    # ------------------------------------------------------------
    # External fetchers
    # ------------------------------------------------------------
    def _fetch_portfolio_return(
        self, deps, user_id_int: Optional[int]
    ) -> Optional[float]:
        """過去5営業日のポートフォリオリターン(%) を計算.

        PortfolioService.get_valuation_history(period='1m') から取得し、
        末尾の5営業日 + 基準日でリターンを算出.
        """
        if user_id_int is None:
            return None
        try:
            ps = deps["PortfolioService"]()
            history = ps.get_valuation_history(user_id_int, period="1m")
            return deps["compute_return_from_history"](
                history, lookback_days=5, value_key="value"
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to compute portfolio return: %s", e)
            return None

    def _fetch_benchmark_return(self) -> Optional[float]:
        """過去5営業日のN225リターン(%) を計算."""
        try:
            import yfinance as yf

            ticker = yf.Ticker("^N225")
            df = ticker.history(period="10d", auto_adjust=False)
            if df is None or len(df) < 6:
                return None
            base = float(df["Close"].iloc[-6])
            latest = float(df["Close"].iloc[-1])
            if base == 0:
                return None
            return round((latest - base) / base * 100.0, 2)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to fetch benchmark return: %s", e)
            return None

    def _fetch_n225_change(self, deps) -> Optional[float]:
        """N225 当日価格 - 前日終値ベースで変化率を取得.

        YahooFinanceClient.get_current_price は東証ETF (`{code}.T`) 用なので、
        指数 (^N225) は yfinance を直接使用.
        失敗時はNone (None = ルール未発火扱い).
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker("^N225")
            df = ticker.history(period="5d", auto_adjust=False)
            if df is None or len(df) < 2:
                return None
            prev_close = float(df["Close"].iloc[-2])
            current_close = float(df["Close"].iloc[-1])
            if prev_close == 0:
                return None
            return round((current_close - prev_close) / prev_close * 100.0, 2)
        except Exception as e:
            logger.warning("Failed to fetch N225: %s", e)
            return None

    def _write_markdown(self, kind: KindT, today: date, md: str) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        suffix = today.strftime("%Y%m%d")
        if kind == "alert":
            now = datetime.now(JST)
            path = self.reports_dir / f"{suffix}_{kind}_{now.strftime('%H%M%S')}.md"
        else:
            path = self.reports_dir / f"{suffix}_{kind}.md"
        path.write_text(md, encoding="utf-8")
        return path
