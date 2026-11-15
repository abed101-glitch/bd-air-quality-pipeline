"""Integration test: the SQL AQI in the dbt mart must agree with the Python reference.

Skipped automatically when the warehouse has not been built.
"""
import pytest

from bdair.aqi import aqi
from bdair.config import database_url

psycopg = pytest.importorskip("psycopg")


@pytest.fixture(scope="module")
def daily_rows():
    try:
        with psycopg.connect(database_url(), connect_timeout=3) as conn:
            return conn.execute(
                "select pm25_aqi_input, aqi_pm25, aqi_category from marts.fct_daily_city "
                "where aqi_pm25 is not null"
            ).fetchall()
    except psycopg.Error as exc:  # no database / not built yet
        pytest.skip(f"warehouse not available: {exc}")


def test_sql_aqi_matches_python_reference(daily_rows):
    assert daily_rows, "fct_daily_city has no scored days"
    mismatches = []
    for mean, sql_aqi, sql_cat in daily_rows:
        ref = aqi("pm2_5", float(mean))
        if ref != (sql_aqi, sql_cat):
            mismatches.append((float(mean), sql_aqi, sql_cat, ref))
    assert not mismatches, mismatches[:10]
