"""Idempotent loading into PostgreSQL (raw schema)."""
from __future__ import annotations

import io
import json
from datetime import UTC, datetime

import pandas as pd
import psycopg

DDL = """
create schema if not exists raw;

create table if not exists raw.air_quality_hourly (
    city_id text not null,
    observed_at timestamp not null,
    pm2_5 double precision,
    pm10 double precision,
    nitrogen_dioxide double precision,
    sulphur_dioxide double precision,
    ozone double precision,
    carbon_monoxide double precision,
    loaded_at timestamptz not null default now(),
    primary key (city_id, observed_at)
);

create table if not exists raw.weather_hourly (
    city_id text not null,
    observed_at timestamp not null,
    temperature_2m double precision,
    relative_humidity_2m double precision,
    wind_speed_10m double precision,
    precipitation double precision,
    loaded_at timestamptz not null default now(),
    primary key (city_id, observed_at)
);

create table if not exists raw.quarantine (
    id bigserial primary key,
    source text not null,
    reason text not null,
    record jsonb not null,
    quarantined_at timestamptz not null default now()
);

create table if not exists raw.load_log (
    id bigserial primary key,
    source text not null,
    window_start date,
    window_end date,
    rows_received int,
    rows_loaded int,
    rows_quarantined int,
    run_at timestamptz not null default now()
);
"""


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(DDL)


def upsert(conn: psycopg.Connection, table: str, df: pd.DataFrame) -> int:
    """COPY into a temp table, then INSERT ... ON CONFLICT DO UPDATE. Returns rows written."""
    if df.empty:
        return 0
    cols = list(df.columns)
    col_list = ", ".join(cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in ("city_id", "observed_at"))
    tmp = f"tmp_{table.split('.')[-1]}"
    with conn.cursor() as cur:
        cur.execute(f"create temp table {tmp} (like {table} including defaults) on commit drop")
        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False, na_rep="\\N")
        buf.seek(0)
        with cur.copy(f"copy {tmp} ({col_list}) from stdin with (format csv, null '\\N')") as cp:
            cp.write(buf.read())
        cur.execute(
            f"insert into {table} ({col_list}) select {col_list} from {tmp} "
            f"on conflict (city_id, observed_at) do update set {updates}, loaded_at = now()"
        )
        return cur.rowcount


def quarantine(conn: psycopg.Connection, source: str, bad: pd.DataFrame) -> int:
    if bad.empty:
        return 0
    rows = [
        (source, r.pop("reason"), json.dumps(r, default=str))
        for r in bad.to_dict(orient="records")
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "insert into raw.quarantine (source, reason, record) values (%s, %s, %s::jsonb)", rows
        )
    return len(rows)


def log_run(conn, source, start, end, received, loaded, quarantined) -> None:
    conn.execute(
        "insert into raw.load_log (source, window_start, window_end, rows_received, rows_loaded, "
        "rows_quarantined) values (%s, %s, %s, %s, %s, %s)",
        (source, start, end, received, loaded, quarantined),
    )


def latest_loaded(conn: psycopg.Connection, table: str) -> datetime | None:
    row = conn.execute(f"select max(observed_at) from {table}").fetchone()
    return row[0] if row else None


def utcnow() -> datetime:
    return datetime.now(UTC)
