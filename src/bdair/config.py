"""Static configuration: cities, variables and connection settings."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    city_id: str
    name: str
    division: str
    lat: float
    lon: float


# The eight divisional headquarters of Bangladesh.
CITIES: tuple[City, ...] = (
    City("DHK", "Dhaka", "Dhaka", 23.8103, 90.4125),
    City("CTG", "Chattogram", "Chattogram", 22.3569, 91.7832),
    City("KHL", "Khulna", "Khulna", 22.8456, 89.5403),
    City("RAJ", "Rajshahi", "Rajshahi", 24.3745, 88.6042),
    City("SYL", "Sylhet", "Sylhet", 24.8949, 91.8687),
    City("BAR", "Barishal", "Barishal", 22.7010, 90.3535),
    City("RNG", "Rangpur", "Rangpur", 25.7439, 89.2752),
    City("MYM", "Mymensingh", "Mymensingh", 24.7471, 90.4203),
)

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

AIR_QUALITY_VARS = (
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "carbon_monoxide",
)
WEATHER_VARS = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation",
)

TIMEZONE = "Asia/Dhaka"
DEFAULT_START = "2024-01-01"


def database_url() -> str:
    return os.environ.get(
        "BDAIR_DATABASE_URL", "postgresql://localhost:5432/bd_air"
    )
