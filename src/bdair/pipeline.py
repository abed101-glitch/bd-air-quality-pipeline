"""Command-line entry point: `python -m bdair.pipeline backfill|incremental`."""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

import psycopg

from . import extract, load, quality
from .config import AIR_QUALITY_VARS, DEFAULT_START, WEATHER_VARS, database_url

log = logging.getLogger("bdair")

SOURCES = {
    "air_quality": ("raw.air_quality_hourly", extract.fetch_air_quality, list(AIR_QUALITY_VARS)),
    "weather": ("raw.weather_hourly", extract.fetch_weather, list(WEATHER_VARS)),
}


def run_source(conn: psycopg.Connection, source: str, start: date, end: date) -> dict:
    table, fetch, cols = SOURCES[source]
    raw = fetch(start, end)
    received = len(raw)
    available, unavailable = quality.drop_unavailable(raw, cols)
    clean, bad = quality.validate(available, cols)
    loaded = load.upsert(conn, table, clean)
    quarantined = load.quarantine(conn, source, bad)
    load.log_run(conn, source, start, end, received, loaded, quarantined)
    stats = {"source": source, "start": str(start), "end": str(end), "received": received,
                 "unavailable": unavailable, "loaded": loaded, "quarantined": quarantined}
    log.info("%s", stats)
    return stats


def run(start: date, end: date, sources: list[str]) -> list[dict]:
    with psycopg.connect(database_url(), autocommit=False) as conn:
        load.ensure_schema(conn)
        conn.commit()
        results = []
        for source in sources:
            results.append(run_source(conn, source, start, end))
            conn.commit()  # one transaction per source: a failure never leaves half a window
        return results


def incremental_window(conn: psycopg.Connection, table: str, lookback_days: int = 7) -> date:
    """Re-pull the last `lookback_days` so late-arriving / revised values are corrected."""
    latest = load.latest_loaded(conn, table)
    if latest is None:
        return date.fromisoformat(DEFAULT_START)
    return latest.date() - timedelta(days=lookback_days)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Bangladesh air-quality ingestion")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("--start", default=DEFAULT_START)
    b.add_argument("--end", default=str(date.today() - timedelta(days=1)))
    sub.add_parser("incremental")
    args = p.parse_args(argv)

    end = date.today() - timedelta(days=1)
    if args.cmd == "backfill":
        run(date.fromisoformat(args.start), date.fromisoformat(args.end), list(SOURCES))
    else:
        with psycopg.connect(database_url()) as conn:
            load.ensure_schema(conn)
            conn.commit()
            starts = {s: incremental_window(conn, SOURCES[s][0]) for s in SOURCES}
        for source, start in starts.items():
            run(start, end, [source])


if __name__ == "__main__":
    main()
