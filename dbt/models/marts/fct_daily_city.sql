-- One row per city per day. AQI uses the 24-hour mean, per US EPA method,
-- and is only reported for days with at least 18 of 24 hours (75% completeness).
with daily as (
    select
        city_id,
        observed_date                          as date_day,
        count(*)                               as hours_observed,
        count(pm2_5)                           as pm25_hours,
        avg(pm2_5)                             as pm25_mean,
        max(pm2_5)                             as pm25_max,
        avg(pm10)                              as pm10_mean,
        avg(no2)                               as no2_mean,
        avg(o3)                                as o3_mean,
        avg(temperature_c)                     as temperature_mean_c,
        avg(wind_speed_kmh)                    as wind_speed_mean_kmh,
        sum(precipitation_mm)                  as precipitation_total_mm
    from {{ ref('fct_air_quality_hourly') }}
    group by 1, 2
),

scored as (
    select
        d.*,
        d.pm25_hours >= 18                     as is_complete_day,
        trunc(d.pm25_mean::numeric, 1)         as pm25_trunc,
        trunc(d.pm10_mean::numeric, 0)         as pm10_trunc
    from daily d
)

select
    s.city_id,
    s.date_day,
    s.hours_observed,
    s.is_complete_day,
    round(s.pm25_mean::numeric, 2)             as pm25_mean,
    s.pm25_trunc                               as pm25_aqi_input,  -- 24h mean truncated to 0.1, per EPA
    round(s.pm25_max::numeric, 2)              as pm25_max,
    round(s.pm10_mean::numeric, 2)             as pm10_mean,
    round(s.no2_mean::numeric, 2)              as no2_mean,
    round(s.o3_mean::numeric, 2)               as o3_mean,
    round(s.temperature_mean_c::numeric, 1)    as temperature_mean_c,
    round(s.wind_speed_mean_kmh::numeric, 1)   as wind_speed_mean_kmh,
    round(s.precipitation_total_mm::numeric, 1) as precipitation_total_mm,
    case when s.is_complete_day then
        coalesce(
            round((b.i_high - b.i_low)::numeric / (b.c_high - b.c_low)::numeric * (s.pm25_trunc - b.c_low::numeric) + b.i_low),
            case when s.pm25_trunc > 325.4 then 500 end
        )
    end::int                                   as aqi_pm25,
    case when s.is_complete_day then
        coalesce(b.category, case when s.pm25_trunc > 325.4 then 'Hazardous' end)
    end                                        as aqi_category,
    case when s.is_complete_day then coalesce(b.category_rank, case when s.pm25_trunc > 325.4 then 6 end) end
                                               as aqi_category_rank,
    s.pm25_mean > 15                           as exceeds_who_24h_guideline,  -- WHO 2021: 15 µg/m³
    round((s.pm25_mean / 15.0)::numeric, 2)    as times_who_24h_guideline
from scored s
left join {{ ref('aqi_breakpoints') }} b
    on b.pollutant = 'pm2_5'
   and s.pm25_trunc between b.c_low::numeric and b.c_high::numeric
