"""Reference US EPA AQI implementation (2024 PM2.5 breakpoints).

The warehouse computes AQI in SQL from the `aqi_breakpoints` seed; this module
is the independent reference that the test suite checks the SQL against.
"""
from __future__ import annotations

import math
from decimal import ROUND_DOWN, Decimal

# (c_low, c_high, i_low, i_high, category)
PM25 = (
    (0.0, 9.0, 0, 50, "Good"),
    (9.1, 35.4, 51, 100, "Moderate"),
    (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups"),
    (55.5, 125.4, 151, 200, "Unhealthy"),
    (125.5, 225.4, 201, 300, "Very Unhealthy"),
    (225.5, 325.4, 301, 500, "Hazardous"),
)
PM10 = (
    (0, 54, 0, 50, "Good"),
    (55, 154, 51, 100, "Moderate"),
    (155, 254, 101, 150, "Unhealthy for Sensitive Groups"),
    (255, 354, 151, 200, "Unhealthy"),
    (355, 424, 201, 300, "Very Unhealthy"),
    (425, 604, 301, 500, "Hazardous"),
)
TABLES = {"pm2_5": (PM25, 1), "pm10": (PM10, 0)}


def _truncate(value: float, digits: int) -> float:
    # Decimal avoids binary float artefacts (73.4 * 10 == 733.9999...)
    return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_DOWN))


def aqi(pollutant: str, concentration: float) -> tuple[int, str]:
    """AQI and category for a 24-hour average concentration (µg/m³)."""
    table, digits = TABLES[pollutant]
    c = _truncate(max(concentration, 0.0), digits)
    for c_lo, c_hi, i_lo, i_hi, cat in table:
        if c_lo <= c <= c_hi:
            # round half away from zero, matching PostgreSQL's round()
            return math.floor((i_hi - i_lo) / (c_hi - c_lo) * (c - c_lo) + i_lo + 0.5), cat
    return 500, "Hazardous"  # beyond the top breakpoint
