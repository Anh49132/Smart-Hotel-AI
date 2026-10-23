"""Transfer a consistent SQLite snapshot to an EMPTY, migrated database.

Run: python -m scripts.transfer_sqlite --source data/hotel.db
Target is read only from TRANSFER_DATABASE_URL (never printed).
"""
import argparse
import os
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import Numeric, func, inspect, select, text

from core.db_engine import build_engine
from core.database import Base
from backend import models  # noqa: F401 - register tables


def transfer(source_path, target_url):
    source_path = Path(source_path).resolve(strict=True)
    target = build_engine(target_url)
    try:
        if target.dialect.name == "sqlite" and Path(target.url.database).resolve() == source_path:
            raise ValueError("Source and target must be different databases")
        with TemporaryDirectory(prefix="hotel-transfer-") as directory:
            snapshot = Path(directory) / "snapshot.db"
            with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(snapshot)) as backup:
                    source.backup(backup)
                    if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or backup.execute("PRAGMA foreign_key_check").fetchall():
                        raise ValueError("Source database failed integrity checks")
            source_engine = build_engine("sqlite:///" + snapshot.as_posix())
            try:
                tables = list(Base.metadata.sorted_tables)
                counts = {}
                with source_engine.connect() as src, target.begin() as dst:
                    inspector = inspect(dst)
                    if not all(inspector.has_table(table.name) for table in tables):
                        raise ValueError("Run alembic upgrade head on the target first")
                    if target.dialect.name == "postgresql":
                        names = ", ".join(dst.dialect.identifier_preparer.quote(t.name) for t in tables)
                        dst.execute(text(f"LOCK TABLE {names} IN ACCESS EXCLUSIVE MODE"))
                    elif target.dialect.name == "sqlite":
                        dst.exec_driver_sql("BEGIN IMMEDIATE")
                    if any(dst.scalar(select(func.count()).select_from(t)) for t in tables):
                        raise ValueError("Target must be empty; no data was overwritten")
                    source_tables = set(inspect(src).get_table_names())
                    for table in tables:
                        if table.name not in source_tables:
                            raise ValueError(f"Missing source table: {table.name}; migrate a copy of the source first")
                        # Read only columns present in the source. New columns use target defaults.
                        columns = {c['name'] for c in inspect(src).get_columns(table.name)}
                        selected = [c for c in table.columns if c.name in columns]
                        rows = [dict(row) for row in src.execute(select(*selected)).mappings()]
                        if rows:
                            dst.execute(table.insert(), rows)
                        counts[table.name] = len(rows)
                        if dst.scalar(select(func.count()).select_from(table)) != len(rows):
                            raise ValueError(f"Count mismatch: {table.name}")
                        for column in selected:
                            if isinstance(column.type, Numeric):
                                expected = sum((Decimal(str(r[column.name])) for r in rows if r[column.name] is not None), Decimal(0))
                                actual = dst.scalar(select(func.coalesce(func.sum(column), 0)))
                                if Decimal(str(actual)) != expected:
                                    raise ValueError(f"Numeric total mismatch: {table.name}.{column.name}")
                    if target.dialect.name == "postgresql":
                        for table in tables:
                            dst.execute(text("SELECT setval(pg_get_serial_sequence(:table, 'id'), COALESCE((SELECT MAX(id) FROM " + dst.dialect.identifier_preparer.quote(table.name) + "), 1), EXISTS(SELECT 1 FROM " + dst.dialect.identifier_preparer.quote(table.name) + "))"), {"table": table.name})
                return counts
            finally:
                source_engine.dispose()
    finally:
        target.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    target = os.environ.get("TRANSFER_DATABASE_URL")
    if not target:
        parser.error("Set TRANSFER_DATABASE_URL securely in the environment")
    try:
        counts = transfer(args.source, target)
    except Exception as exc:
        # Driver errors can contain DSNs, data or credentials: do not echo them.
        raise SystemExit(f"Transfer aborted ({type(exc).__name__}); target transaction rolled back. Check source/schema/empty target.") from None
    print("Transfer verified:", counts)


if __name__ == "__main__":
    main()
