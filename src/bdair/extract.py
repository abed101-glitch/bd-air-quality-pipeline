"""Extract hourly air-quality and weather data from the Open-Meteo APIs.

Requests are chunked by date range and retried with exponential backoff, and
every response is reshaped into one tidy long-format DataFrame per source.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import pandas as pd
import requests

from .config import (
    AIR_QUALITY_URL,
    AIR_QUALITY_VARS,
    CITIES,
    TIMEZONE,
    WEATHER_URL,
    WEATHER_VARS,
    City,
)

log = logging.getLogger(__name__)

CHUNK_DAYS = 92  # keep each request comfortably under API limits
MAX_RETRIES = 5


def _get(url: str, params: dict, session: requests.Session) -> list[dict]:
    """GET with exponential backoff. Always returns a list of location payloads."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            payload = resp.json()
            return payload if isinstance(payload, list) else [payload]
        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = 2**attempt
            log.warning("Request failed (%s), retry %d in %ds", exc, attempt, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def date_chunks(start: date, end: date, days: int = CHUNK_DAYS):
    """Yield inclusive (chunk_start, chunk_end) pairs covering [start, end]."""
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=days - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def payload_to_frame(payload: dict, city: City, variables: tuple[str, ...]) -> pd.DataFrame:
    hourly = payload.get("hourly") or {}
    if "time" not in hourly:
        return pd.DataFrame()
    df = pd.DataFrame({"observed_at": pd.to_datetime(hourly["time"])})
    for var in variables:
        df[var] = pd.to_numeric(pd.Series(hourly.get(var, [None] * len(df))), errors="coerce")
    df.insert(0, "city_id", city.city_id)
    return df


def _fetch(url: str, variables: tuple[str, ...], start: date, end: date,
           cities: tuple[City, ...] = CITIES) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with requests.Session() as session:
        for c_start, c_end in date_chunks(start, end):
            params = {
                "latitude": ",".join(str(c.lat) for c in cities),
                "longitude": ",".join(str(c.lon) for c in cities),
                "hourly": ",".join(variables),
                "start_date": c_start.isoformat(),
                "end_date": c_end.isoformat(),
                "timezone": TIMEZONE,
            }
            payloads = _get(url, params, session)
            if len(payloads) != len(cities):
                raise ValueError(f"Expected {len(cities)} locations, got {len(payloads)}")
            for city, payload in zip(cities, payloads):
                frames.append(payload_to_frame(payload, city, variables))
            log.info("%s %s..%s: %d locations", url.split("/")[2], c_start, c_end, len(payloads))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def fetch_air_quality(start: date, end: date) -> pd.DataFrame:
    return _fetch(AIR_QUALITY_URL, AIR_QUALITY_VARS, start, end)


def fetch_weather(start: date, end: date) -> pd.DataFrame:
    return _fetch(WEATHER_URL, WEATHER_VARS, start, end)
