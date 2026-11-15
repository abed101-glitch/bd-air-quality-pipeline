{# Lightweight generic tests so the project has no package dependencies. #}

{% test dbt_utils_unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}

{% test non_negative(model, column_name) %}
select * from {{ model }} where {{ column_name }} < 0
{% endtest %}

{% test between(model, column_name, min_value, max_value) %}
select * from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
