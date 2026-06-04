"""Strategy loader: parse YAML frontmatter from personal strategy markdown."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TargetHolding:
    """目標保有銘柄（フラット配列の1要素）."""

    code: str
    name: str
    bucket: str  # "group_a" | "group_b"
    weight_pct: float  # 0〜100


@dataclass(frozen=True)
class BucketDef:
    """バケット定義（group_a / group_b / cash）."""

    code: str  # "group_a" | "group_b" | "cash"
    label_ja: str
    weight_pct: float  # 0〜100


@dataclass(frozen=True)
class MechanicalRules:
    """機械ルール閾値."""

    min_holding_months: int
    loss_cut_pct: float
    n225_drawdown_trigger_pct: float
    n225_drawdown_basis: str
    n225_dca_lookback_days: int
    alpha_deviation_threshold_pp: float
    drift_ok_pp: float
    drift_warn_pp: float
    rebalance_check_basis: str


@dataclass(frozen=True)
class Strategy:
    """戦略SSOT.

    A群/B群モデル統一後のスキーマ.

    Attributes:
        target_buckets: {"group_a": BucketDef, "group_b": BucketDef, "cash": BucketDef}
        target_holdings: 採用銘柄のフラット配列（bucket フィールドで群を識別）
    """

    revision: date
    owner: str
    benchmark: str
    review_frequency: str
    target_buckets: Dict[str, BucketDef]
    target_holdings: Tuple[TargetHolding, ...]
    mechanical_rules: MechanicalRules
    body_markdown: str = ""

    def holdings_by_bucket(self, bucket: str) -> Tuple[TargetHolding, ...]:
        """指定バケットに属する採用銘柄."""
        return tuple(h for h in self.target_holdings if h.bucket == bucket)


class StrategyLoader:
    """戦略YAMLフロントマターをパース."""

    REQUIRED_TOP_KEYS = (
        "revision",
        "owner",
        "benchmark",
        "target_buckets",
        "target_holdings",
        "mechanical_rules",
    )

    REQUIRED_BUCKET_KEYS = ("group_a", "group_b", "cash")

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
    def _build_buckets(cls, raw: Any) -> Dict[str, BucketDef]:
        """target_buckets をパース."""
        if not isinstance(raw, dict):
            raise ValueError("target_buckets must be a mapping")
        missing = [k for k in cls.REQUIRED_BUCKET_KEYS if k not in raw]
        if missing:
            raise ValueError(f"target_buckets missing keys: {missing}")
        buckets: Dict[str, BucketDef] = {}
        for key in cls.REQUIRED_BUCKET_KEYS:
            item = raw[key]
            if not isinstance(item, dict):
                raise ValueError(f"target_buckets.{key} must be a mapping")
            for f in ("label_ja", "weight_pct"):
                if f not in item:
                    raise ValueError(f"target_buckets.{key} missing '{f}'")
            buckets[key] = BucketDef(
                code=key,
                label_ja=str(item["label_ja"]),
                weight_pct=float(item["weight_pct"]),
            )
        total = sum(b.weight_pct for b in buckets.values())
        if abs(total - 100.0) >= 0.001:
            raise ValueError(
                f"target_buckets weight_pct must sum to 100.0, got {total}"
            )
        return buckets

    @classmethod
    def _build_holdings(
        cls, raw: Any, buckets: Dict[str, BucketDef]
    ) -> Tuple[TargetHolding, ...]:
        """target_holdings (フラット配列) をパース."""
        if not isinstance(raw, list):
            raise ValueError("target_holdings must be a list")
        result: List[TargetHolding] = []
        valid_buckets = set(buckets.keys()) - {"cash"}
        for item in raw:
            for f in ("code", "name", "bucket", "weight_pct"):
                if f not in item:
                    raise ValueError(f"target_holdings item missing '{f}': {item}")
            bucket = str(item["bucket"])
            if bucket not in valid_buckets:
                raise ValueError(
                    f"target_holdings item bucket '{bucket}' is invalid; "
                    f"must be one of {sorted(valid_buckets)}: {item}"
                )
            result.append(
                TargetHolding(
                    code=str(item["code"]),
                    name=str(item["name"]),
                    bucket=bucket,
                    weight_pct=float(item["weight_pct"]),
                )
            )
        # 各 bucket 内の weight_pct 合計が buckets[bucket].weight_pct と一致するか検証
        for bucket_key in valid_buckets:
            actual = sum(h.weight_pct for h in result if h.bucket == bucket_key)
            expected = buckets[bucket_key].weight_pct
            if abs(actual - expected) >= 0.001:
                raise ValueError(
                    f"target_holdings weight_pct sum for bucket '{bucket_key}' "
                    f"is {actual}, expected {expected} (from target_buckets)"
                )
        return tuple(result)

    @classmethod
    def _build_rules(cls, raw: Dict[str, Any]) -> MechanicalRules:
        required = (
            "min_holding_months",
            "loss_cut_pct",
            "n225_drawdown_trigger_pct",
            "n225_drawdown_basis",
            "n225_dca_lookback_days",
            "alpha_deviation_threshold_pp",
            "drift_ok_pp",
            "drift_warn_pp",
            "rebalance_check_basis",
        )
        missing = [k for k in required if k not in raw]
        if missing:
            raise ValueError(f"mechanical_rules missing keys: {missing}")
        drift_ok = float(raw["drift_ok_pp"])
        drift_warn = float(raw["drift_warn_pp"])
        if not (drift_ok < drift_warn):
            raise ValueError(
                f"mechanical_rules.drift_ok_pp ({drift_ok}) must be less than "
                f"drift_warn_pp ({drift_warn})"
            )
        return MechanicalRules(
            min_holding_months=int(raw["min_holding_months"]),
            loss_cut_pct=float(raw["loss_cut_pct"]),
            n225_drawdown_trigger_pct=float(raw["n225_drawdown_trigger_pct"]),
            n225_drawdown_basis=str(raw["n225_drawdown_basis"]),
            n225_dca_lookback_days=int(raw["n225_dca_lookback_days"]),
            alpha_deviation_threshold_pp=float(raw["alpha_deviation_threshold_pp"]),
            drift_ok_pp=drift_ok,
            drift_warn_pp=drift_warn,
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

        buckets = cls._build_buckets(data["target_buckets"])
        holdings = cls._build_holdings(data["target_holdings"], buckets)

        return Strategy(
            revision=cls._parse_date(data["revision"], "revision"),
            owner=str(data["owner"]),
            benchmark=str(data["benchmark"]),
            review_frequency=str(data.get("review_frequency", "weekly_friday")),
            target_buckets=buckets,
            target_holdings=holdings,
            mechanical_rules=cls._build_rules(data["mechanical_rules"]),
            body_markdown=body.strip(),
        )
