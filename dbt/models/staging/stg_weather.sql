select
    city_id,
    observed_at,
    temperature_2m        as temperature_c,
    relative_humidity_2m  as relative_humidity_pct,
    wind_speed_10m        as wind_speed_kmh,
    precipitation         as precipitation_mm
from {{ source('raw', 'weather_hourly') }}
