"""Tiny schema upgrade for databases created by an older version.

db.create_all() only creates MISSING TABLES; it never adds a column to a table
that already exists. Columns added after a database was first created are
listed here and added with ALTER TABLE (works on SQLite and PostgreSQL).
Existing data is untouched; running it again does nothing.
"""

from sqlalchemy import inspect, text

from library.extensions import db

# table -> [(column, SQL type)]
NEW_COLUMNS = {
    "pv_assets": [("location", "VARCHAR(120)"), ("owner", "VARCHAR(20)")],
    "issues": [("hold_days", "INTEGER DEFAULT 0"), ("held_since", "DATE")],
}


def ensure_columns():
    _upgrade_columns()
    # Scanning is by Serial Number only now, so the old "mismatch" status no
    # longer exists: those assets simply go back to "Not Checked".
    if "pv_assets" in set(inspect(db.engine).get_table_names()):
        with db.engine.begin() as conn:
            conn.execute(text("UPDATE pv_assets SET scan_status = 'pending' WHERE scan_status = 'mismatch'"))


def _upgrade_columns():
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in NEW_COLUMNS.items():
        if table not in existing_tables:
            continue  # create_all() has just created it with every column
        present = {c["name"] for c in inspector.get_columns(table)}
        for name, sql_type in columns:
            if name not in present:
                with db.engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
