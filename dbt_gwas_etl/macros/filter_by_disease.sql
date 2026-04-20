{% macro filter_by_disease(column_name, disease_list) -%}
    (
    {%- for disease in disease_list -%}
        lower({{ column_name }}) like '%{{ disease | lower }}%'
        {%- if not loop.last %} or {% endif -%}
    {%- endfor -%}
    )
{%- endmacro %}