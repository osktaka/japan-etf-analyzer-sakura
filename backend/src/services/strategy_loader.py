"""Strategy loader: parse YAML frontmatter from personal strategy markdown."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TargetHolding:
    """目標保有銘柄."""

    code: str
    name: str
    weight: float


@dataclass(frozen=True)
class SellAction:
    """売却スケジュール項目."""

    date: date
    code: str
    name: str
    quantity: int
    action: str  # "all" | "half" | "quarter" 等
    reason: str


@dataclass(frozen=True)
class BuyAction:
    """DCA買付スケジュール項目."""

    date: date
    code: str
    quantity: int


@dataclass(frozen=True)
class MechanicalRules:
    """機械ルール閾値."""

    min_holding_months: int
    loss_cut_pct: float
    take_profit_pct: Tuple[float, ...]
    n225_drawdown_trigger_pct: float
    n225_drawdown_basis: str
    n225_dca_lookback_days: int
    alpha_deviation_threshold_pp: float
    rebalance_threshold_pct: float
    rebalance_check_basis: str


@dataclass(frozen=True)
class Strategy:
    """戦略SSOT."""

    revision: date
    owner: str
    benchmark: str
    review_frequency: str
    target_allocation: Dict[str, float]
    target_holdings_core: Tuple[TargetHolding, ...]
    target_holdings_theme: Tuple[TargetHolding, ...]
    sell_schedule: Tuple[SellAction, ...]
    buy_dca_schedule: Tuple[BuyAction, ...]
    mechanical_rules: MechanicalRules
    body_markdown: str = ""

    def all_target_holdings(self) -> Tuple[TargetHolding, ...]:
        """コア＋テーマの全目標銘柄."""
        return self.target_holdings_core + self.target_holdings_theme

    def get_sells_on(self, target_date: date) -> List[SellAction]:
        """指定日の売却予定."""
        return [s for s in self.sell_schedule if s.date == target_date]

    def get_buys_on(self, target_date: date) -> List[BuyAction]:
        """指定日のDCA買付予定."""
        return [b for b in self.buy_dca_schedule if b.date == target_date]


class StrategyLoader:
    """戦略YAMLフロントマターをパース."""

    REQUIRED_TOP_KEYS = (
        "revision",
        "owner",
        "benchmark",
        "target_allocation",
        "target_holdings",
        "sell_schedule",
        "buy_dca_schedule",
        "mechanical_rules",
    )

    @staticmethod
    def _split_frontmatter(text: str) -> Tuple[str, str]:
        """フロントマター部分と本文を分離."""
        if not text.startswith("---"):
            raise ValueError("Strategy file must start with YAML frontmatter (---)")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Strategy file frontmatter is not properly closed (---)")
        return parts[1], parts[2]

    @staticmethod
    def _parse_date(value: Any, field_name: str) -> date:
        """日付変換."""
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValueError(f"Invalid date format for {field_name}: {value}") from e
        raise ValueError(f"Invalid date type for {field_name}: {type(value).__name__}")

    @classmethod
    def _validate_top_keys(cls, data: Dict[str, Any]) -> None:
        """トップレベル必須キーの検証."""
        missing = [k for k in cls.REQUIRED_TOP_KEYS if k not in data]
        if missing:
            raise ValueError(f"Strategy missing required keys: {missing}")

    @classmethod
    def _build_holdings(cls, raw: List[Dict]) -> Tuple[TargetHolding, ...]:
        result = []
        for item in raw or []:
            if "code" not in item or "name" not in item or "weight" not in item:
                raise ValueError(f"target_holdings item missing fields: {item}")
            result.append(
                TargetHolding(
                    code=str(item["code"]),
                    name=str(item["name"]),
                    weight=float(item["weight"]),
                )
            )
        return tuple(result)

    @classmethod
    def _build_sells(cls, raw: List[Dict]) -> Tuple[SellAction, ...]:
        result = []
        for item in raw or []:
            for f in ("date", "code", "name", "quantity", "action", "reason"):
                if f not in item:
                    raise ValueError(f"sell_schedule item missing '{f}': {item}")
            result.append(
                SellAction(
                    date=cls._parse_date(item["date"], "sell_schedule.date"),
                    code=str(item["code"]),
                    name=str(item["name"]),
                    quantity=int(item["quantity"]),
                    action=str(item["action"]),
                    reason=str(item["reason"]),
                )
            )
        return tuple(result)

    @classmethod
    def _build_buys(cls, raw: List[Dict]) -> Tuple[BuyAction, ...]:
        result = []
        for item in raw or []:
            for f in ("date", "code", "quantity"):
                if f not in item:
                    raise ValueError(f"buy_dca_schedule item missing '{f}': {item}")
            result.append(
                BuyAction(
                    date=cls._parse_date(item["date"], "buy_dca_schedule.date"),
                    code=str(item["code"]),
                    quantity=int(item["quantity"]),
                )
            )
        return tuple(result)

    @classmethod
    def _build_rules(cls, raw: Dict[str, Any]) -> MechanicalRules:
        required = (
            "min_holding_months",
            "loss_cut_pct",
            "take_profit_pct",
            "n225_drawdown_trigger_pct",
            "n225_drawdown_basis",
            "n225_dca_lookback_days",
            "alpha_deviation_threshold_pp",
            "rebalance_threshold_pct",
            "rebalance_check_basis",
        )
        missing = [k for k in required if k not in raw]
        if missing:
            raise ValueError(f"mechanical_rules missing keys: {missing}")
        tp = raw["take_profit_pct"]
        if not isinstance(tp, list) or not tp:
            raise ValueError("mechanical_rules.take_profit_pct must be non-empty list")
        return MechanicalRules(
            min_holding_months=int(raw["min_holding_months"]),
            loss_cut_pct=float(raw["loss_cut_pct"]),
            take_profit_pct=tuple(float(x) for x in tp),
            n225_drawdown_trigger_pct=float(raw["n225_drawdown_trigger_pct"]),
            n225_drawdown_basis=str(raw["n225_drawdown_basis"]),
            n225_dca_lookback_days=int(raw["n225_dca_lookback_days"]),
            alpha_deviation_threshold_pp=float(raw["alpha_deviation_threshold_pp"]),
            rebalance_threshold_pct=float(raw["rebalance_threshold_pct"]),
            rebalance_check_basis=str(raw["rebalance_check_basis"]),
        )

    @classmethod
    def load(cls, file_path: str | Path) -> Strategy:
        """戦略ファイル(.md)を読み込みStrategyを返す."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Strategy file not found: {path}")
        text = path.read_text(encoding="utf-8")
        return cls.loads(text)

    @classmethod
    def loads(cls, text: str) -> Strategy:
        """文字列から戦略をロード."""
        fm_text, body = cls._split_frontmatter(text)
        try:
            data = yaml.safe_load(fm_text)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("Strategy frontmatter must be a YAML mapping")

        cls._validate_top_keys(data)

        target_holdings = data["target_holdings"]
        if not isinstance(target_holdings, dict):
            raise ValueError("target_holdings must be a mapping with core/theme keys")
        target_allocation = data["target_allocation"]
        if not isinstance(target_allocation, dict):
            raise ValueError("target_allocation must be a mapping")

        return Strategy(
            revision=cls._parse_date(data["revision"], "revision"),
            owner=str(data["owner"]),
            benchmark=str(data["benchmark"]),
            review_frequency=str(data.get("review_frequency", "weekly_friday")),
            target_allocation={k: float(v) for k, v in target_allocation.items()},
            target_holdings_core=cls._build_holdings(target_holdings.get("core") or []),
            target_holdings_theme=cls._build_holdings(target_holdings.get("theme") or []),
            sell_schedule=cls._build_sells(data.get("sell_schedule") or []),
            buy_dca_schedule=cls._build_buys(data.get("buy_dca_schedule") or []),
            mechanical_rules=cls._build_rules(data["mechanical_rules"]),
            body_markdown=body.strip(),
        )
