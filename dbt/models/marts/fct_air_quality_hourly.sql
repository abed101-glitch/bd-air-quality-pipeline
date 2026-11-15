{{ config(
    materialized='incremental',
    unique_key=['city_id', 'observed_at'],
    incremental_strategy='delete+insert',
    indexes=[{'columns': ['city_id', 'observed_at'], 'unique': true}, {'columns': ['observed_date']}]
) }}

select
    aq.city_id,
    aq.observed_at,
    aq.observed_date,
    aq.observed_hour,
    aq.pm2_5,
    aq.pm10,
    aq.no2,
    aq.so2,
    aq.o3,
    aq.co,
    w.temperature_c,
    w.relative_humidity_pct,
    w.wind_speed_kmh,
    w.precipitation_mm,
    aq.loaded_at
from {{ ref('stg_air_quality') }} aq
left join {{ ref('stg_weather') }} w
    on w.city_id = aq.city_id and w.observed_at = aq.observed_at
{% if is_incremental() %}
-- reprocess a 10-day window so revised API values and late weather rows are picked up
where aq.observed_date >= (select max(observed_date) - 10 from {{ this }})
{% endif %}
