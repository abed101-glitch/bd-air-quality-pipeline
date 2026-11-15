-- Every scored day's AQI must fall inside the index band of its category.
select d.*
from {{ ref('fct_daily_city') }} d
join {{ ref('aqi_breakpoints') }} b
  on b.pollutant = 'pm2_5' and b.category = d.aqi_category
where d.aqi_pm25 is not null
  and d.aqi_pm25 not between b.i_low and b.i_high
