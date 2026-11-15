with bounds as (
    select min(observed_date) as d0, max(observed_date) as d1
    from {{ ref('stg_air_quality') }}
)
select
    d::date                                   as date_day,
    extract(year from d)::int                 as year,
    extract(month from d)::int                as month,
    to_char(d, 'Mon')                         as month_name,
    extract(isodow from d)::int               as iso_day_of_week,
    to_char(d, 'Dy')                          as day_name,
    extract(isodow from d) in (5, 6)          as is_weekend,  -- Friday/Saturday in Bangladesh
    case
        when extract(month from d) in (12, 1, 2) then 'Winter'
        when extract(month from d) in (3, 4, 5)  then 'Pre-monsoon'
        when extract(month from d) in (6, 7, 8, 9) then 'Monsoon'
        else 'Post-monsoon'
    end                                       as season
from bounds, generate_series(bounds.d0, bounds.d1, interval '1 day') as d
