{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {# Isso força o dbt a ignorar o prefixo e usar o nome exato do dbt_project.yml #}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}