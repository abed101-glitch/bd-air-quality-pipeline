select
    d.city_id,
    c.city_name,
    date_trunc('month', d.date_day)::date                         as month_start,
    count(*) filter (where d.is_complete_day)                     as complete_days,
    round(avg(d.pm25_mean), 2)                                    as pm25_mean,
    round(avg(d.pm25_mean) / 5.0, 1)                              as times_who_annual_guideline,  -- WHO annual: 5 µg/m³
    count(*) filter (where d.exceeds_who_24h_guideline)           as days_over_who_24h,
    count(*) filter (where d.aqi_category_rank >= 4)              as unhealthy_or_worse_days,
    max(d.aqi_pm25)                                               as worst_aqi
from {{ ref('fct_daily_city') }} d
join {{ ref('dim_city') }} c using (city_id)
group by 1, 2, 3
