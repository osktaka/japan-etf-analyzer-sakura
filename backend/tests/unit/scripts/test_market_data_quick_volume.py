"""market_data_quick の出来高時間帯補正 純粋関数の回帰テスト.

対象（副作用なし・外部依存なし）:
- expected_volume_progress(hour, minute): 時刻別の期待累積出来高割合
- adjust_volume_ratio(raw_ratio, expected_progress): 補正比＋判定ラベル
- 定数 VOLUME_PROGRESS_CURVE / LUNCH_START / LUNCH_END

market_data_quick は冒頭で yfinance 等を import するため、scripts ディレクトリを
sys.path に追加してからモジュール import する（既存 _shared テストと同方式）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# backend/tests/unit/scripts/ -> backend/scripts/
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from market_data_quick import (  # noqa: E402
    LUNCH_END,
    LUNCH_START,
    VOLUME_PROGRESS_CURVE,
    adjust_volume_ratio,
    expected_volume_progress,
)


# ---- 定数 ---------------------------------------------------------------

def test_lunch_constants():
    assert LUNCH_START == 690  # 11:30
    assert LUNCH_END == 750  # 12:30


def test_curve_has_lunch_points():
    # 昼休みフラットの基準値（前場引け）
    assert VOLUME_PROGRESS_CURVE[LUNCH_START] == 0.46
    assert VOLUME_PROGRESS_CURVE[LUNCH_END] == 0.49


# ---- expected_volume_progress: 場前 / 引け後（補正無効化 = 1.0） ----------

@pytest.mark.parametrize(
    "hour,minute",
    [
        (8, 0),    # 場前
        (9, 0),    # 09:00 ちょうどは下限で 1.0
        (15, 30),  # 引け
        (16, 0),   # 引け後
    ],
)
def test_progress_returns_one_outside_session(hour, minute):
    assert expected_volume_progress(hour, minute) == 1.0


# ---- expected_volume_progress: カーブ点に一致 ----------------------------

@pytest.mark.parametrize(
    "hour,minute,expected",
    [
        (10, 0, 0.27),
        (10, 30, 0.34),
        (15, 0, 0.82),
    ],
)
def test_progress_matches_curve_points(hour, minute, expected):
    assert expected_volume_progress(hour, minute) == pytest.approx(expected)


# ---- expected_volume_progress: 補間途中 ----------------------------------

def test_progress_interpolated_between_points():
    # 09:45 は 09:30(0.18) と 10:00(0.27) の間
    v = expected_volume_progress(9, 45)
    assert 0.18 < v < 0.27
    # 線形補間の理論値 0.225 とも一致
    assert v == pytest.approx(0.225)


# ---- expected_volume_progress: 昼休みフラット（今回の修正の核心） --------

@pytest.mark.parametrize(
    "hour,minute",
    [
        (11, 30),  # 前場引け = LUNCH_START
        (11, 45),
        (12, 0),
        (12, 29),  # LUNCH_END の直前
    ],
)
def test_progress_flat_during_lunch(hour, minute):
    # 昼休みは線形補間で上昇させず 0.46 固定
    assert expected_volume_progress(hour, minute) == pytest.approx(0.46)


def test_progress_resumes_at_afternoon_open():
    # 12:30 後場寄りで補間再開し 0.49 に戻る
    assert expected_volume_progress(12, 30) == pytest.approx(0.49)


# ---- adjust_volume_ratio: ユーザー実例 -----------------------------------

def test_adjust_user_example():
    result = adjust_volume_ratio(0.58, 0.46)
    assert result["adjusted"] == pytest.approx(1.26)
    assert result["judgment"] == "やや多め"
    assert result["expected_progress"] == pytest.approx(0.46)


# ---- adjust_volume_ratio: 判定ラベル境界 ---------------------------------

@pytest.mark.parametrize(
    "raw,expected_label",
    [
        (1.3, "急増"),
        (1.1, "やや多め"),
        (0.8, "ほぼ平常"),
        (0.6, "やや薄商い"),
        (0.5, "薄商い"),
    ],
)
def test_adjust_judgment_thresholds(raw, expected_label):
    # progress=1.0 なら corrected == raw となり閾値を直接検証できる
    result = adjust_volume_ratio(raw, 1.0)
    assert result["judgment"] == expected_label


# ---- adjust_volume_ratio: 後方互換 / ゼロガード --------------------------

def test_adjust_backward_compatible_when_progress_one():
    # expected_progress=1.0 のとき adjusted == raw
    assert adjust_volume_ratio(0.93, 1.0)["adjusted"] == pytest.approx(0.93)


def test_adjust_zero_guard_no_exception():
    # progress=0 は raw 据え置きで例外を出さない
    result = adjust_volume_ratio(1.0, 0)
    assert result["adjusted"] == pytest.approx(1.0)
