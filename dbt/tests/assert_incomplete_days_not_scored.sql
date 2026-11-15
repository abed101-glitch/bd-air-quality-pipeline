-- Days below 75% hourly completeness must not get an AQI.
select * from {{ ref('fct_daily_city') }}
where not is_complete_day and aqi_pm25 is not null
