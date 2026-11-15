"""Query the marts and write charts + headline findings to docs/."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg

from bdair.config import database_url

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

CAT_ORDER = ["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy",
             "Very Unhealthy", "Hazardous"]
CAT_COLORS = ["#2e7d32", "#c0a000", "#ef6c00", "#c62828", "#6a1b9a", "#4e0d1a"]


def q(conn, sql: str) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        monthly = q(conn, "select * from marts.agg_city_monthly order by month_start, city_name")
        daily = q(conn, """
            select d.*, c.city_name, dt.season
            from marts.fct_daily_city d
            join marts.dim_city c using (city_id)
            join marts.dim_date dt on dt.date_day = d.date_day
            where d.is_complete_day""")
        hourly = q(conn, """
            select observed_hour, extract(month from observed_date)::int as month, avg(pm2_5) as pm25
            from marts.fct_air_quality_hourly where city_id = 'DHK' group by 1, 2""")
        dq = q(conn, """
            select (select count(*) from raw.air_quality_hourly) as aq_rows,
                   (select count(*) from raw.weather_hourly) as weather_rows,
                   (select count(*) from raw.quarantine) as quarantined""")

    for df in (monthly, daily, hourly):
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass

    # 1. Monthly PM2.5 by city vs WHO guideline
    fig, ax = plt.subplots(figsize=(11, 5))
    for city, g in monthly.groupby("city_name"):
        ax.plot(pd.to_datetime(g["month_start"]), g["pm25_mean"], label=city,
                linewidth=2.6 if city == "Dhaka" else 1.2, alpha=1 if city == "Dhaka" else 0.7)
    ax.axhline(15, color="black", linestyle="--", linewidth=1)
    ax.text(ax.get_xlim()[0], 17, " WHO 24-hour guideline (15 µg/m³)", fontsize=9)
    ax.set_ylabel("Monthly mean PM2.5 (µg/m³)")
    ax.set_title("PM2.5 across Bangladesh's divisional cities")
    ax.legend(ncol=4, fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMG / "monthly_pm25.png", dpi=150)
    plt.close(fig)

    # 2. AQI category share by city (stacked bar)
    share = (daily.groupby(["city_name", "aqi_category"]).size()
             .unstack(fill_value=0).reindex(columns=CAT_ORDER, fill_value=0))
    share = share.div(share.sum(axis=1), axis=0) * 100
    share = share.sort_values(["Very Unhealthy", "Unhealthy"], ascending=True)
    fig, ax = plt.subplots(figsize=(11, 5))
    share.plot(kind="barh", stacked=True, color=CAT_COLORS, ax=ax, width=0.75)
    ax.set_xlabel("% of days (US EPA AQI category, PM2.5)")
    ax.set_ylabel("")
    ax.set_title("How many days were unhealthy? Share of days by AQI category")
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMG / "aqi_category_share.png", dpi=150)
    plt.close(fig)

    # 3. Dhaka hour-of-day x month heatmap
    pivot = hourly.pivot(index="observed_hour", columns="month", values="pm25").sort_index()
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(pivot.values, aspect="auto", cmap="magma_r", origin="lower")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([pd.Timestamp(2024, m, 1).strftime("%b") for m in pivot.columns])
    ax.set_yticks(range(0, 24, 3))
    ax.set_ylabel("Hour of day (Asia/Dhaka)")
    ax.set_title("Dhaka: mean PM2.5 by month and hour of day")
    fig.colorbar(im, ax=ax, label="PM2.5 (µg/m³)")
    fig.tight_layout()
    fig.savefig(IMG / "dhaka_hour_month_heatmap.png", dpi=150)
    plt.close(fig)

    # Headline numbers
    dhaka = daily[daily["city_name"] == "Dhaka"]
    by_city = daily.groupby("city_name")["pm25_mean"].mean().sort_values(ascending=False)
    season = dhaka.groupby("season")["pm25_mean"].mean()
    peak_hour = int(hourly.groupby("observed_hour")["pm25"].mean().idxmax())
    findings = {
        "period": f"{daily['date_day'].min()} to {daily['date_day'].max()}",
        "complete_city_days": len(daily),
        "raw_rows_air_quality": int(dq.loc[0, "aq_rows"]),
        "raw_rows_weather": int(dq.loc[0, "weather_rows"]),
        "rows_quarantined": int(dq.loc[0, "quarantined"]),
        "dhaka_mean_pm25": round(float(dhaka["pm25_mean"].mean()), 1),
        "dhaka_times_who_annual": round(float(dhaka["pm25_mean"].mean()) / 5, 1),
        "dhaka_pct_days_over_who_24h": round(100 * float(dhaka["exceeds_who_24h_guideline"].mean()), 1),
        "dhaka_pct_days_unhealthy_or_worse": round(100 * float((dhaka["aqi_category_rank"] >= 4).mean()), 1),
        "dhaka_winter_vs_monsoon_ratio": round(float(season["Winter"] / season["Monsoon"]), 1),
        "dhaka_peak_hour": peak_hour,
        "most_polluted_city": by_city.index[0],
        "least_polluted_city": by_city.index[-1],
        "city_ranking_pm25": {k: round(float(v), 1) for k, v in by_city.items()},
    }
    (ROOT / "docs" / "findings.json").write_text(json.dumps(findings, indent=2, default=str))
    print(json.dumps(findings, indent=2, default=str))


if __name__ == "__main__":
    main()
