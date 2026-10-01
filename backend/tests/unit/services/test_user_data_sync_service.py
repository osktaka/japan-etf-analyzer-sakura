"""Tests for user data (trades / cash flows) sync service."""
from datetime import date, datetime

import sqlite3

import pytest

from src.models import ETF, CashFlow, Category, Trade, User
from src.services.user_data_sync_service import (
    SyncError,
    backup_sqlite,
    classify_diff,
    diff_rows,
    read_user_data_from_sqlite,
    export_user_data,
    replace_user_data,
    summarize,
)


@pytest.fixture
def seeded(db_session):
    cat = Category(name="c")
    db_session.add(cat)
    db_session.commit()
    for code in ("1615", "200A"):
        db_session.add(ETF(code=code, name=code, category_id=cat.id))
    user = User(user_id="test", password_hash="x", username="t")
    other = User(user_id="other", password_hash="x", username="o")
    db_session.add_all([user, other])
    db_session.commit()
    return user, other


def _trade(user_pk, code="1615", qty=10, price=100.0, d=date(2026, 9, 1), memo=None):
    return Trade(
        user_id=user_pk,
        etf_code=code,
        trade_type="buy",
        quantity=qty,
        price=price,
        trade_date=d,
        memo=memo,
    )


class TestExport:
    def test_export_contains_only_target_user_without_ids(self, db_session, seeded):
        user, other = seeded
        db_session.add_all([_trade(user.id, memo="m"), _trade(other.id, qty=99)])
        db_session.add(
            CashFlow(
                user_id=user.id,
                flow_type="deposit",
                amount=1000,
                flow_date=date(2026, 9, 1),
            )
        )
        db_session.commit()

        data = export_user_data(user.id)

        assert [t["quantity"] for t in data["trades"]] == [10]
        assert data["trades"][0]["memo"] == "m"
        assert "id" not in data["trades"][0]
        assert "user_id" not in data["trades"][0]
        assert data["cash_flows"][0]["amount"] == 1000.0
        assert data["summary"] == summarize(data["trades"], data["cash_flows"])


class TestReplace:
    def _payload(self):
        return {
            "trades": [
                {
                    "etf_code": "200A",
                    "trade_type": "buy",
                    "quantity": 5,
                    "price": 200.5,
                    "trade_date": "2026-09-02",
                    "memo": None,
                    "created_at": "2026-09-02T10:00:00",
                },
            ],
            "cash_flows": [
                {
                    "flow_type": "deposit",
                    "amount": 5000.0,
                    "flow_date": "2026-09-02",
                    "memo": "d",
                    "created_at": "2026-09-02T10:00:00",
                },
            ],
        }

    def test_replaces_target_user_only(self, db_session, seeded):
        user, other = seeded
        db_session.add_all([_trade(user.id, qty=1), _trade(other.id, qty=99)])
        db_session.commit()

        replace_user_data(user.id, self._payload())

        mine = Trade.query.filter_by(user_id=user.id).all()
        assert [(t.etf_code, t.quantity) for t in mine] == [("200A", 5)]
        assert mine[0].created_at == datetime(2026, 9, 2, 10, 0, 0)
        assert Trade.query.filter_by(user_id=other.id).count() == 1
        assert CashFlow.query.filter_by(user_id=user.id).count() == 1

    def test_summary_matches_after_replace(self, db_session, seeded):
        user, _ = seeded
        payload = self._payload()
        replace_user_data(user.id, payload)
        local = export_user_data(user.id)
        assert local["summary"] == summarize(payload["trades"], payload["cash_flows"])

    def test_unknown_etf_aborts_without_change(self, db_session, seeded):
        user, _ = seeded
        db_session.add(_trade(user.id, qty=1))
        db_session.commit()
        payload = self._payload()
        payload["trades"][0]["etf_code"] = "9999"

        with pytest.raises(SyncError, match="9999"):
            replace_user_data(user.id, payload)

        assert [t.quantity for t in Trade.query.filter_by(user_id=user.id)] == [1]

    def test_empty_payload_rejected_unless_allowed(self, db_session, seeded):
        user, _ = seeded
        db_session.add(_trade(user.id, qty=1))
        db_session.commit()
        empty = {"trades": [], "cash_flows": []}

        with pytest.raises(SyncError, match="empty"):
            replace_user_data(user.id, empty)
        assert Trade.query.filter_by(user_id=user.id).count() == 1

        replace_user_data(user.id, empty, allow_empty=True)
        assert Trade.query.filter_by(user_id=user.id).count() == 0

    def test_failure_after_delete_rolls_back(self, db_session, seeded):
        """DELETE 実行後（追加中）に失敗しても元のデータが残る."""
        user, _ = seeded
        db_session.add(_trade(user.id, qty=1))
        db_session.commit()
        payload = self._payload()
        payload["trades"].append({**payload["trades"][0], "trade_date": "bad"})

        with pytest.raises(ValueError):
            replace_user_data(user.id, payload)

        assert [t.quantity for t in Trade.query.filter_by(user_id=user.id)] == [1]


def _export(trades, cash_flows=()):
    return {"trades": list(trades), "cash_flows": list(cash_flows)}


def _t(**kw):
    base = {
        "etf_code": "1615",
        "trade_type": "buy",
        "quantity": 10,
        "price": 100.0,
        "trade_date": "2026-09-01",
        "memo": None,
        "created_at": "2026-09-01T10:00:00",
    }
    return {**base, **kw}


class TestDiffRows:
    def test_identical_has_no_diff(self):
        d = diff_rows(_export([_t()]), _export([_t()]))
        assert not any(d.values())

    def test_edit_that_keeps_summary_is_detected(self):
        """buy→sell の訂正は件数・数量・金額の合計が変わらないが差分になる."""
        local, remote = _export([_t()]), _export([_t(trade_type="sell")])
        assert summarize(local["trades"], []) == summarize(remote["trades"], [])
        d = diff_rows(local, remote)
        assert len(d["trades_only_local"]) == 1
        assert len(d["trades_only_remote"]) == 1

    def test_cash_flow_type_edit_detected(self):
        cf = {
            "flow_type": "deposit",
            "amount": 100.0,
            "flow_date": "2026-09-01",
            "memo": None,
            "created_at": "2026-09-01T10:00:00",
        }
        d = diff_rows(
            _export([], [cf]), _export([], [{**cf, "flow_type": "withdrawal"}])
        )
        assert d["cash_flows_only_local"] and d["cash_flows_only_remote"]

    def test_duplicate_rows_counted_as_multiset(self):
        d = diff_rows(_export([_t(), _t()]), _export([_t()]))
        assert len(d["trades_only_local"]) == 1
        assert not d["trades_only_remote"]


class TestBackupSqlite:
    def test_includes_uncheckpointed_wal_data(self, tmp_path):
        src = tmp_path / "etf.db"
        conn = sqlite3.connect(src)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=0")
        conn.execute("CREATE TABLE t (v INTEGER)")
        conn.execute("INSERT INTO t VALUES (42)")
        conn.commit()  # 本体ファイルへは未反映（WAL のみ）

        dest = backup_sqlite(src, tmp_path / "backups")

        assert sqlite3.connect(dest).execute("SELECT v FROM t").fetchall() == [(42,)]
        conn.close()

    def test_keeps_only_latest_n(self, tmp_path):
        src = tmp_path / "etf.db"
        sqlite3.connect(src).execute("CREATE TABLE t (v)").connection.close()
        d = tmp_path / "backups"
        d.mkdir()
        for i in range(4):
            (d / f"etf.db.backup_sync_2026010{i}_000000").write_text("x")

        backup_sqlite(src, d, keep=2)

        assert len(list(d.glob("etf.db.backup_sync_*"))) == 2

    def test_sidecar_files_not_counted_in_retention(self, tmp_path):
        src = tmp_path / "etf.db"
        sqlite3.connect(src).execute("CREATE TABLE t (v)").connection.close()
        d = tmp_path / "backups"
        d.mkdir()
        for i in range(2):
            (d / f"etf.db.backup_sync_2026010{i}_000000").write_text("x")
            (d / f"etf.db.backup_sync_2026010{i}_000000-wal").write_text("x")

        backup_sqlite(src, d, keep=3)

        assert len(list(d.glob("etf.db.backup_sync_????????_??????"))) == 3
        assert len(list(d.glob("*-wal"))) == 2


class TestClassifyDiff:
    def test_created_at_only_is_separated_from_real_rows(self):
        local = _export([_t(created_at="2026-01-01T00:00:00"), _t(quantity=7)])
        remote = _export([_t(created_at="2026-02-02T00:00:00"), _t(quantity=9)])
        c = classify_diff(diff_rows(local, remote))["trades"]
        assert c["created_at_only"] == 1
        assert [r[2] for r in c["local_only"]] == [7]
        assert [r[2] for r in c["remote_only"]] == [9]


class TestReadUserDataFromSqlite:
    def _make_db(self, path):
        conn = sqlite3.connect(path)
        conn.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, user_id TEXT);
            CREATE TABLE trades (id INTEGER PRIMARY KEY, user_id INT, etf_code TEXT,
              trade_type TEXT, quantity INT, price NUMERIC, trade_date DATE,
              memo TEXT, created_at DATETIME);
            CREATE TABLE cash_flows (id INTEGER PRIMARY KEY, user_id INT,
              flow_type TEXT, amount NUMERIC, flow_date DATE, memo TEXT,
              created_at DATETIME);
            INSERT INTO users VALUES (2, 'test'), (3, 'other');
            INSERT INTO trades VALUES
              (1, 2, '1615', 'buy', 10, 100.5, '2026-09-01', NULL,
               '2026-09-01 10:00:00.123456'),
              (2, 3, '1615', 'buy', 99, 1, '2026-09-01', NULL,
               '2026-09-01 10:00:00.000000');
            INSERT INTO cash_flows VALUES
              (1, 2, 'deposit', 500, '2026-09-01', 'm', '2026-09-01 10:00:00.000000');
            """
        )
        conn.commit()
        conn.close()

    def test_reads_only_target_user_in_export_format(self, tmp_path):
        src = tmp_path / "src.db"
        self._make_db(src)
        # 実運用の入力は backup_sqlite の出力（WAL ヘッダ付き）
        conn = sqlite3.connect(src)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()
        db = backup_sqlite(src, tmp_path / "backups")

        data = read_user_data_from_sqlite(db, "test")

        assert data["trades"] == [
            _t(price=100.5, created_at="2026-09-01T10:00:00.123456")
        ]
        assert data["cash_flows"][0]["amount"] == 500.0
        assert data["summary"]["trade_count"] == 1
        assert [p.name for p in db.parent.iterdir()] == [
            db.name
        ]  # 付随ファイルを作らない

    def test_missing_path_raises_without_creating_file(self, tmp_path):
        missing = tmp_path / "nonexist.db"
        with pytest.raises(SyncError, match="not found"):
            read_user_data_from_sqlite(missing, "test")
        assert not missing.exists()

    def test_path_with_special_characters(self, tmp_path):
        d = tmp_path / "dir with space#x"
        d.mkdir()
        db = d / "b.db"
        self._make_db(db)
        assert read_user_data_from_sqlite(db, "test")["summary"]["trade_count"] == 1

    def test_unknown_user_raises(self, tmp_path):
        db = tmp_path / "b.db"
        self._make_db(db)
        with pytest.raises(SyncError, match="nobody"):
            read_user_data_from_sqlite(db, "nobody")


class TestBackupProtect:
    def test_protected_source_survives_retention(self, tmp_path):
        src = tmp_path / "etf.db"
        sqlite3.connect(src).close()
        dest = tmp_path / "backups"
        dest.mkdir()
        oldest = dest / "etf.db.backup_sync_20200101_000000"
        oldest.write_bytes(b"x")
        for i in range(2, 6):
            (dest / f"etf.db.backup_sync_2020010{i}_000000").write_bytes(b"x")

        backup_sqlite(src, dest, keep=5, protect=oldest)

        assert oldest.exists()
