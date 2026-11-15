select
    city_id,
    observed_at,
    observed_at::date                as observed_date,
    extract(hour from observed_at)::int as observed_hour,
    pm2_5,
    pm10,
    nitrogen_dioxide                 as no2,
    sulphur_dioxide                  as so2,
    ozone                            as o3,
    carbon_monoxide                  as co,
    loaded_at
from {{ source('raw', 'air_quality_hourly') }}
