"""
Bring a database created by an older version of the app up to date.

`create_all` makes missing tables but never changes one that exists, so a
table whose shape changed is rebuilt here. Used at start-up and by the matching
Alembic migration, so both routes give the same result. Each step is safe to
run more than once.
"""

from sqlalchemy import inspect, text

ENGAGEMENT_COLUMNS = [
    "id", "analysis_id", "key", "packet", "imported_at", "strategy_draft",
    "hypotheses", "hypothesis_seq", "grades", "relates", "created_at", "updated_at",
]


def upgrade_engagements(conn) -> bool:
    """
    One link per upload became one link per (upload, country). An existing row
    becomes the whole-organization link (country ""); nothing is lost.
    Returns True when the table was rebuilt.
    """
    from .models import Engagement  # noqa: F401 — the new table definition

    insp = inspect(conn)
    if "engagements" not in insp.get_table_names():
        return False
    if "country" in {c["name"] for c in insp.get_columns("engagements")}:
        return False

    conn.execute(text("ALTER TABLE engagements RENAME TO engagements_before_countries"))
    # Index names belong to the old table; drop them so the new table can create its own
    for ix in inspect(conn).get_indexes("engagements_before_countries"):
        conn.execute(text(f'DROP INDEX IF EXISTS "{ix["name"]}"'))
    Engagement.__table__.create(conn)
    cols = ", ".join(ENGAGEMENT_COLUMNS)
    conn.execute(text(
        f"INSERT INTO engagements ({cols}, country, role_matches, role_match_log, role_reasons) "
        f"SELECT {cols}, '', '{{}}', '[]', '{{}}' FROM engagements_before_countries"
    ))
    conn.execute(text("DROP TABLE engagements_before_countries"))
    return True
