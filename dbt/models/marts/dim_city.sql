select
    city_id,
    city_name,
    division,
    latitude,
    longitude
from {{ ref('cities') }}
