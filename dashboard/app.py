"""Streamlit dashboard over the dbt marts.  Run: streamlit run dashboard/app.py"""
from __future__ import annotations

import pandas as pd
import psycopg
import streamlit as st

from bdair.config import database_url

st.set_page_config(page_title="Bangladesh Air Quality", layout="wide")


@st.cache_data(ttl=3600)
def load(sql: str, params: tuple = ()) -> pd.DataFrame:
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        df = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
    for col in df.columns[df.dtypes == object]:
        try:
            df[col] = pd.to_numeric(df[col])  # Decimal -> float
        except (ValueError, TypeError):
            pass  # genuinely text
    return df


cities = load("select city_id, city_name from marts.dim_city order by city_name")
bounds = load("select min(date_day) as lo, max(date_day) as hi from marts.fct_daily_city")
lo, hi = pd.to_datetime(bounds.loc[0, "lo"]).date(), pd.to_datetime(bounds.loc[0, "hi"]).date()

st.title("Bangladesh Air Quality")
st.caption("Open-Meteo (CAMS) hourly data → PostgreSQL → dbt marts. AQI: US EPA (2024), PM2.5 24-hour mean.")

with st.sidebar:
    picked = st.multiselect("Cities", cities["city_name"].tolist(), default=["Dhaka", "Sylhet"])
    start, end = st.date_input("Date range", (lo, hi), min_value=lo, max_value=hi)

daily = load(
    """select d.*, c.city_name from marts.fct_daily_city d join marts.dim_city c using (city_id)
       where d.date_day between %s and %s and d.is_complete_day""",
    (start, end),
)
daily = daily[daily["city_name"].isin(picked)]
if daily.empty:
    st.warning("No complete days for this selection.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Mean PM2.5 (µg/m³)", f"{daily['pm25_mean'].mean():.1f}")
k2.metric("× WHO annual guideline", f"{daily['pm25_mean'].mean() / 5:.1f}×")
k3.metric("Days over WHO 24h limit", f"{100 * daily['exceeds_who_24h_guideline'].mean():.0f}%")
k4.metric("Worst daily AQI", int(daily["aqi_pm25"].max()))

st.subheader("Daily PM2.5")
st.line_chart(daily.pivot_table(index="date_day", columns="city_name", values="pm25_mean"))

st.subheader("Days by AQI category")
cat = daily.groupby(["city_name", "aqi_category"]).size().unstack(fill_value=0)
st.bar_chart(cat.T)

st.subheader("Monthly summary")
monthly = load("select * from marts.agg_city_monthly order by month_start desc")
st.dataframe(monthly[monthly["city_name"].isin(picked)], use_container_width=True, hide_index=True)
