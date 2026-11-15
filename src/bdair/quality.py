"""Row-level data-quality checks.

Bad rows are never silently dropped: they are split into a quarantine frame
with the reason attached, so they can be inspected and counted.
"""
from __future__ import annotations

import pandas as pd

# Physically plausible upper bounds (µg/m³). Anything above is treated as a sensor/model glitch.
UPPER_BOUNDS = {
    "pm2_5": 1000.0,
    "pm10": 2000.0,
    "nitrogen_dioxide": 2000.0,
    "sulphur_dioxide": 2000.0,
    "ozone": 1000.0,
    "carbon_monoxide": 50000.0,
    "temperature_2m": 60.0,
    "relative_humidity_2m": 100.0,
    "wind_speed_10m": 300.0,
    "precipitation": 500.0,
}
NON_NEGATIVE = set(UPPER_BOUNDS) - {"temperature_2m"}


def validate(df: pd.DataFrame, value_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean, quarantine). Quarantine has an extra `reason` column."""
    if df.empty:
        return df, df.assign(reason=pd.Series(dtype="object"))

    reasons = pd.Series("", index=df.index, dtype="object")

    def flag(mask: pd.Series, reason: str) -> None:
        mask = mask.fillna(False)
        reasons.loc[mask] = (reasons.loc[mask] + ";" + reason).str.lstrip(";")

    flag(df["city_id"].isna() | df["observed_at"].isna(), "missing_key")
    flag(df.duplicated(subset=["city_id", "observed_at"], keep="first"), "duplicate_key")
    for col in value_cols:
        if col in NON_NEGATIVE:
            flag(df[col] < 0, f"negative_{col}")
        if col in UPPER_BOUNDS:
            flag(df[col] > UPPER_BOUNDS[col], f"out_of_range_{col}")

    bad = reasons != ""
    return df[~bad].copy(), df[bad].assign(reason=reasons[bad])


def drop_unavailable(df: pd.DataFrame, value_cols: list[str]) -> tuple[pd.DataFrame, int]:
    """Drop hours the API has not published yet (every value null). These are
    missing data, not bad data, so they are counted rather than quarantined."""
    if df.empty:
        return df, 0
    empty = df[value_cols].isna().all(axis=1)
    return df[~empty].copy(), int(empty.sum())


def completeness(df: pd.DataFrame, expected_hours: int) -> pd.DataFrame:
    """Share of expected hourly rows present per city."""
    counts = df.groupby("city_id").size().rename("rows").reset_index()
    counts["completeness"] = (counts["rows"] / expected_hours).round(4)
    return counts
