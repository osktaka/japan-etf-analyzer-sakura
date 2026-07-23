"""Tests for etf_rating_notifier（短文フォーマットの movers/cautions 抽出とフォールバック描画）."""
from __future__ import annotations

from datetime import datetime

from src.services.etf_rating_notifier import (
    JST,
    _render,
    _select_cautions,
    _select_movers,
)


def _rating(code, net=65.0, delta=1.0, downside=20.0, **overrides):
    base = {
        "code": code,
        "name": f"銘柄{code}",
        "net_score": net,
        "upside_weighted": 70.0,
        "downside_weighted": downside,
        "delta_net": delta,
        "executive_note": f"{code} のコメントです。",
        "top_drivers_bullish_labels": ["A-1 追い風要因"],
        "top_drivers_bearish_labels": ["B-1 リスク要因"],
    }
    base.update(overrides)
    return base


TODAY = datetime(2026, 7, 22, 18, 15, tzinfo=JST)


class TestSelectMovers:
    def test_sorts_by_absolute_delta_and_keeps_large_drop(self):
        # 上昇5件 + 大幅下落1件: 絶対値順なら -9.0 が先頭に残る
        ratings = [
            _rating("A1", delta=3.5),
            _rating("A2", delta=3.2),
            _rating("A3", delta=3.1),
            _rating("A4", delta=3.05),
            _rating("A5", delta=3.01),
            _rating("D1", delta=-9.0),
        ]
        movers = _select_movers(ratings)
        assert len(movers) == 5
        assert movers[0]["code"] == "D1"
        assert "A5" not in [r["code"] for r in movers]

    def test_excludes_below_threshold_and_none(self):
        ratings = [
            _rating("A1", delta=2.9),
            _rating("A2", delta=None),
            _rating("A3", delta=-3.0),
        ]
        assert [r["code"] for r in _select_movers(ratings)] == ["A3"]


class TestSelectCautions:
    def test_selects_warning_or_high_downside(self):
        ratings = [
            _rating("OK", net=72.0, downside=25.0),
            _rating("WARN", net=35.0, downside=30.0),
            _rating("DOWN", net=65.0, downside=46.0),
        ]
        codes = [r["code"] for r in _select_cautions(ratings)]
        # 下落リスク降順
        assert codes == ["DOWN", "WARN"]

    def test_tolerates_missing_keys(self):
        ratings = [
            {"code": "X1", "net_score": 35.0},  # downside_weighted 欠損
            {"code": "X2"},  # net_score も欠損
        ]
        assert [r["code"] for r in _select_cautions(ratings)] == ["X1"]

    def test_caps_at_three(self):
        ratings = [_rating(f"C{i}", net=30.0, downside=50.0 + i) for i in range(5)]
        assert len(_select_cautions(ratings)) == 3


class TestRenderFallback:
    def test_renders_short_format(self):
        payload = {
            "summary_text": "総評です。",
            "ratings": [
                _rating("1629", net=74.3, delta=0.7),
                _rating("1618", net=71.4, delta=6.7),
                _rating("314A", net=58.4, delta=5.4, downside=46.1),
            ],
            "flags": [{"code": "1629", "type": "strong_tailwind"}],
        }
        subject, plain, html = _render(payload, TODAY)
        assert "強い追い風 1銘柄" in subject
        assert "■ 動きがあった銘柄" in plain
        assert "1618" in plain and "▲" in plain
        assert "■ 注意ポイント" in plain and "314A" in plain
        # 旧フォーマットの銘柄別詳細ブロックが無いこと
        assert "3ヶ月の見通し" not in plain
        assert "<details" not in html
        assert len(plain) < 2000

    def test_survives_sparse_payload(self):
        # 欠損だらけの payload でも例外にならずレンダリングできる（fail-soft の安全網）
        payload = {
            "ratings": [
                {
                    "code": "X1",
                    "net_score": 35.0,
                    "delta_net": -9.0,
                    "top_drivers_bearish_labels": None,
                },
                {"code": "X2", "net_score": 65.0},
            ],
            "flags": [],
        }
        subject, plain, html = _render(payload, TODAY)
        assert "X1" in plain
        assert "本日は" not in plain  # movers に X1(-9.0) が載る
        assert "▼" in plain

    def test_empty_ratings(self):
        subject, plain, html = _render({"ratings": [], "flags": []}, TODAY)
        assert "0銘柄" in subject
        assert "本日は大きなスコア変動はありません" in plain
