"""東証の営業日判定.

本番crontabは曜日指定（1-5）しか持たず祝日を判別できないため、祝日の実行抑止は
各バッチスクリプトの責務になる。判定を3スクリプトで重複させると片方だけ直る事故が
起きるため、ここを唯一の実装とする。
"""
from datetime import date, timedelta


def is_market_open_day(target: date) -> bool:
    """指定日が東証の営業日（平日かつ非祝日）か."""
    import jpholiday

    if target.weekday() >= 5:
        return False
    if jpholiday.is_holiday(target):
        return False
    return True


def get_previous_market_day(target: date) -> date:
    """指定日の前営業日を返す."""
    prev_day = target - timedelta(days=1)
    while not is_market_open_day(prev_day):
        prev_day -= timedelta(days=1)
    return prev_day


def get_next_market_day(target: date) -> date:
    """指定日の翌営業日を返す."""
    next_day = target + timedelta(days=1)
    while not is_market_open_day(next_day):
        next_day += timedelta(days=1)
    return next_day
