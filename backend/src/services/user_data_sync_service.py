"""Export / replace a user's trades and cash flows (prod -> local mirror).

取引は本番を正とし、ローカルは本番の写しとして置換する。id は環境ごとに
異なるため交換せず、user は呼び出し側が環境ごとの PK で解決する。
"""
import sqlite3
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.models import ETF, CashFlow, Trade, db


class SyncError(Exception):
    """Raised when a sync payload cannot be applied safely."""


def _trade_row(t: Trade) -> Dict[str, Any]:
    return {
        "etf_code": t.etf_code,
        "trade_type": t.trade_type,
        "quantity": t.quantity,
        "price": float(t.price),
        "trade_date": t.trade_date.isoformat(),
        "memo": t.memo,
        "created_at": t.created_at.isoformat(),
    }


def _cash_flow_row(c: CashFlow) -> Dict[str, Any]:
    return {
        "flow_type": c.flow_type,
        "amount": float(c.amount),
        "flow_date": c.flow_date.isoformat(),
        "memo": c.memo,
        "created_at": c.created_at.isoformat(),
    }


def summarize(trades: List[Dict], cash_flows: List[Dict]) -> Dict[str, Any]:
    """Count/total digest for display. Sync checks use diff_rows (row level)."""
    # 浮動小数の誤差で比較が割れないよう Decimal で厳密に合算する
    trade_amount = sum(
        (Decimal(str(t["price"])) * t["quantity"] for t in trades), Decimal(0)
    )
    cash_total = sum((Decimal(str(c["amount"])) for c in cash_flows), Decimal(0))
    return {
        "trade_count": len(trades),
        "trade_quantity": sum(t["quantity"] for t in trades),
        "trade_amount": float(trade_amount),
        "cash_flow_count": len(cash_flows),
        "cash_flow_amount": float(cash_total),
    }


def _row_key(kind: str, row: Dict[str, Any]) -> Tuple:
    """Normalized identity of a row; id-less so prod and local rows compare."""
    if kind == "trade":
        return (
            row["etf_code"],
            row["trade_type"],
            row["quantity"],
            f"{row['price']:.2f}",
            row["trade_date"],
            row["memo"] or "",
            row["created_at"],
        )
    return (
        row["flow_type"],
        f"{row['amount']:.2f}",
        row["flow_date"],
        row["memo"] or "",
        row["created_at"],
    )


def diff_rows(local: Dict[str, Any], remote: Dict[str, Any]) -> Dict[str, List]:
    """Row-level difference between two exports (multiset comparison).

    summary は件数・合計しか見ないため、売買区分・日付・メモ・入出金区分の
    訂正のように合計が変わらない編集を検出できない。同期済み判定は行単位で行う。
    """
    out: Dict[str, List] = {}
    for kind, name in (("trade", "trades"), ("cash", "cash_flows")):
        lc = Counter(_row_key(kind, r) for r in local[name])
        rc = Counter(_row_key(kind, r) for r in remote[name])
        out[f"{name}_only_local"] = sorted((lc - rc).elements())
        out[f"{name}_only_remote"] = sorted((rc - lc).elements())
    return out


def row_keys(payload: Dict[str, Any]) -> Dict[str, List]:
    """Sorted row keys of an export, JSON-serializable (the "last synced" snapshot)."""
    return {
        name: sorted(list(_row_key(kind, r)) for r in payload[name])
        for kind, name in (("trade", "trades"), ("cash", "cash_flows"))
    }


def locally_registered_rows(
    diff: Dict[str, List], snapshot: Optional[Dict[str, List]]
) -> List[Tuple]:
    """local-only rows that were NOT in the last synced snapshot.

    前回同期した行が local-only になるのは、本番で訂正・削除されたとき（置換でよい）。
    スナップショットに無い local-only 行は、ローカルで登録された行なので消してはいけない。
    スナップショットが無いときは判別できないため、すべてを該当として扱う（安全側）。
    """
    out: List[Tuple] = []
    for name in ("trades", "cash_flows"):
        have = Counter(tuple(k) for k in (snapshot or {}).get(name, []))
        extra = Counter(tuple(k) for k in diff[f"{name}_only_local"]) - have
        out.extend(extra.elements())
    return out


def classify_diff(diff: Dict[str, List]) -> Dict[str, Dict[str, Any]]:
    """Split a diff into created_at-only differences and real add/delete rows.

    二重登録していた取引は内容が同じでも created_at が環境ごとに違う。これを
    「削除+追加」と数えると、本当にローカルにしか無い行が埋もれるため分けて出す。
    created_at は _row_key の末尾要素。
    """
    out: Dict[str, Dict[str, Any]] = {}
    for name in ("trades", "cash_flows"):
        lo = Counter(k[:-1] for k in diff[f"{name}_only_local"])
        ro = Counter(k[:-1] for k in diff[f"{name}_only_remote"])
        same = lo & ro
        out[name] = {
            "created_at_only": sum(same.values()),
            "local_only": sorted((lo - same).elements()),
            "remote_only": sorted((ro - same).elements()),
        }
    return out


def read_user_data_from_sqlite(path: Path, user_id: str) -> Dict[str, Any]:
    """Read a user's trades / cash flows from a SQLite file (e.g. a sync backup).

    バックアップから対象ユーザー分だけを戻すための読み出し。DB 全体の差し替えは
    他テーブル（batch_logs 等）まで巻き戻すため避ける。mode=ro で存在しないパスに
    空ファイルを作らず、immutable=1 で付随ファイルも作らない。immutable=1 は WAL を
    読まないため、稼働中の DB ではなく backup_sqlite の出力（WAL 取り込み済み）を渡す。
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise SyncError(f"backup file not found: {path}")
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            raise SyncError(f"user not found in {path}: {user_id}")

        def iso(v: str) -> str:
            return datetime.fromisoformat(v).isoformat()

        trades = [
            {
                "etf_code": c,
                "trade_type": t,
                "quantity": q,
                "price": float(p),
                "trade_date": d,
                "memo": m,
                "created_at": iso(ca),
            }
            for c, t, q, p, d, m, ca in conn.execute(
                "SELECT etf_code, trade_type, quantity, price, trade_date, memo,"
                " created_at FROM trades WHERE user_id = ? ORDER BY id",
                (row[0],),
            )
        ]
        cash_flows = [
            {
                "flow_type": ft,
                "amount": float(a),
                "flow_date": d,
                "memo": m,
                "created_at": iso(ca),
            }
            for ft, a, d, m, ca in conn.execute(
                "SELECT flow_type, amount, flow_date, memo, created_at"
                " FROM cash_flows WHERE user_id = ? ORDER BY id",
                (row[0],),
            )
        ]
    finally:
        conn.close()
    return {
        "trades": trades,
        "cash_flows": cash_flows,
        "summary": summarize(trades, cash_flows),
    }


def backup_sqlite(
    src: Path, dest_dir: Path, keep: int = 5, protect: Optional[Path] = None
) -> Path:
    """Consistent snapshot of a SQLite DB, including uncheckpointed WAL data.

    本DBは WAL モード。ファイルコピーでは etf.db-wal 内の直近コミットが
    バックアップに入らないため、SQLite のオンラインバックアップ API を使う。
    protect は保持数の整理で消さないファイル（--restore-from の取得元）。
    """
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / f"etf.db.backup_sync_{datetime.now():%Y%m%d_%H%M%S}"
    source = sqlite3.connect(str(src))
    target = sqlite3.connect(str(dest))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    # 保持数は keep（既定5）。1回約200MB のため無制限に溜めない。-wal/-shm 等の付随ファイルは数えない
    keep_path = Path(protect).resolve() if protect else None
    old = sorted(dest_dir.glob("etf.db.backup_sync_????????_??????"))[:-keep]
    for f in old:
        if f.resolve() != keep_path:
            f.unlink()
    return dest


def export_user_data(user_pk: int) -> Dict[str, Any]:
    """Return the user's trades and cash flows without ids, plus a summary."""
    trades = [
        _trade_row(t)
        for t in Trade.query.filter_by(user_id=user_pk).order_by(Trade.id).all()
    ]
    cash_flows = [
        _cash_flow_row(c)
        for c in CashFlow.query.filter_by(user_id=user_pk).order_by(CashFlow.id).all()
    ]
    return {
        "trades": trades,
        "cash_flows": cash_flows,
        "summary": summarize(trades, cash_flows),
    }


def validate_payload(payload: Dict[str, Any], allow_empty: bool = False) -> None:
    """Raise SyncError if the payload cannot be applied safely.

    バックアップを取る前（dry-run の段階）でも呼べるよう、置換処理から切り出している。
    """
    trades = payload.get("trades", [])
    cash_flows = payload.get("cash_flows", [])
    # 取得失敗や本番側の誤操作で空が返ったとき、ローカルを全消去しないための歯止め
    if not trades and not cash_flows and not allow_empty:
        raise SyncError("payload is empty; refusing to wipe local data")

    known = {code for (code,) in db.session.query(ETF.code).all()}
    missing = sorted({t["etf_code"] for t in trades} - known)
    if missing:
        raise SyncError(f"etf_code not in local etfs master: {', '.join(missing)}")


def replace_user_data(
    user_pk: int, payload: Dict[str, Any], allow_empty: bool = False
) -> None:
    """Replace the user's trades and cash flows with payload in one transaction."""
    validate_payload(payload, allow_empty)
    trades = payload["trades"]
    cash_flows = payload["cash_flows"]

    try:
        Trade.query.filter_by(user_id=user_pk).delete()
        CashFlow.query.filter_by(user_id=user_pk).delete()
        for t in trades:
            db.session.add(
                Trade(
                    user_id=user_pk,
                    etf_code=t["etf_code"],
                    trade_type=t["trade_type"],
                    quantity=t["quantity"],
                    price=t["price"],
                    trade_date=date.fromisoformat(t["trade_date"]),
                    memo=t.get("memo"),
                    created_at=datetime.fromisoformat(t["created_at"]),
                )
            )
        for c in cash_flows:
            db.session.add(
                CashFlow(
                    user_id=user_pk,
                    flow_type=c["flow_type"],
                    amount=c["amount"],
                    flow_date=date.fromisoformat(c["flow_date"]),
                    memo=c.get("memo"),
                    created_at=datetime.fromisoformat(c["created_at"]),
                )
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
