"""
Admin-side access to the exchange_rates table.

Reads use the read-only `forex_data` connection. Deletes use the separate `forex_admin`
connection (same database, write-enabled) so the public site can never modify data.

An "extraction" = one day, or (day + run) when the table has a column that identifies
the extraction run/time (auto-detected, see RUN_CANDIDATES, or set
BANKRATES_RUN_COLUMN in settings).
"""
import re
from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.db import connections, transaction

READ, WRITE = "forex_data", "forex_admin"
RUN_CANDIDATES = ("extracted_at", "extraction_id", "run_id", "batch_id", "scraped_at",
                  "fetched_at", "created_at", "inserted_at", "updated_at")
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _rows(alias, sql, params=None):
    with connections[alias].cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def run_column():
    """Column that distinguishes several extractions on one day, or None."""
    override = getattr(settings, "BANKRATES_RUN_COLUMN", "auto")
    if override != "auto":
        if override and not _IDENT.match(override):
            raise ValueError("BANKRATES_RUN_COLUMN must be a plain column name")
        return override or None

    def detect():
        have = {r["column_name"] for r in _rows(
            READ, "SELECT column_name FROM information_schema.columns WHERE table_name = 'exchange_rates'")}
        return next((c for c in RUN_CANDIDATES if c in have), "")

    return cache.get_or_set("cp:bank:runcol", detect, 3600) or None


def _run_expr(col, prefix=""):
    return f"COALESCE({prefix}{col}::text, '')"


def _target(day, run, prefix=""):
    """WHERE fragment + params selecting one extraction."""
    cond, params = [f"{prefix}rate_date = %(day)s"], {"day": day}
    col = run_column()
    if col:
        cond.append(f"{_run_expr(col, prefix)} = %(run)s")
        params["run"] = run or ""
    return " AND ".join(cond), params


def summary():
    return _rows(READ, """SELECT count(DISTINCT rate_date)::int AS days, max(rate_date) AS latest,
                                 count(*)::int AS records FROM exchange_rates""")[0]


def list_extractions(page=1, per_page=20, date_from=None, date_to=None):
    col = run_column()
    where, params = [], {}
    if date_from:
        where.append("rate_date >= %(df)s"); params["df"] = date_from
    if date_to:
        where.append("rate_date <= %(dt)s"); params["dt"] = date_to
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    group = "rate_date" + (f", {_run_expr(col)}" if col else "")
    run_sel = f"{_run_expr(col)} AS run," if col else ""

    total = _rows(READ, f"SELECT count(*)::int AS n FROM (SELECT 1 FROM exchange_rates {where_sql} GROUP BY {group}) t",
                  params)[0]["n"]
    pages = max(1, -(-total // per_page))
    page = min(max(1, page), pages)
    rows = _rows(READ, f"""
        SELECT rate_date AS day, {run_sel}
               count(*)::int AS records,
               count(DISTINCT bank_id)::int AS banks,
               count(DISTINCT currency_code)::int AS currencies
        FROM exchange_rates {where_sql}
        GROUP BY {group}
        ORDER BY rate_date DESC{', run DESC' if col else ''}
        LIMIT %(limit)s OFFSET %(offset)s""",
        {**params, "limit": per_page, "offset": (page - 1) * per_page})
    return {"rows": rows, "page": page, "pages": pages, "total": total, "run_col": col}


def detail(day, run, limit=5000):
    """All records of one extraction, pivoted: one row per (bank, currency)."""
    cond, params = _target(day, run, "r.")
    recs = _rows(READ, f"""
        SELECT b.bank_name AS bank, r.currency_code AS currency, r.rate_type, r.rate::float8 AS rate
        FROM exchange_rates r JOIN banks b USING (bank_id)
        WHERE {cond} ORDER BY r.currency_code, b.bank_name, r.rate_type LIMIT %(limit)s""",
        {**params, "limit": limit + 1})
    truncated = len(recs) > limit
    recs = recs[:limit]
    types = sorted({r["rate_type"] for r in recs})
    pivot = {}
    for r in recs:
        row = pivot.setdefault((r["bank"], r["currency"]),
                               {"bank": r["bank"], "currency": r["currency"], "rates": {}})
        row["rates"][r["rate_type"]] = r["rate"]
    return {"types": types, "rows": list(pivot.values()), "records": len(recs),
            "banks": len({r["bank"] for r in recs}), "truncated": truncated}


def count_target(day, run):
    cond, params = _target(day, run)
    return _rows(READ, f"SELECT count(*)::int AS n FROM exchange_rates WHERE {cond}", params)[0]["n"]


def delete_target(day, run):
    """Delete one extraction on the write connection. Returns the number of rows removed."""
    cond, params = _target(day, run)
    with transaction.atomic(using=WRITE):
        with connections[WRITE].cursor() as cur:
            cur.execute(f"DELETE FROM exchange_rates WHERE {cond}", params)
            deleted = cur.rowcount
    cache.delete("forex:meta")  # the public rates page caches the list of dates
    return deleted


def parse_day(value):
    return date.fromisoformat(str(value))
