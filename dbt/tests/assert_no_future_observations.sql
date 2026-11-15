select * from {{ ref('fct_air_quality_hourly') }}
where observed_at > (now() at time zone 'Asia/Dhaka') + interval '1 hour'
