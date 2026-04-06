{{ config(
    materialized='incremental',
    unique_key='variant_id',
    incremental_strategy='merge',
    cluster_by=['disease_trait']
) }}

{% set target_diseases = ['crohn', 'colitis', 'inflammatory bowel disease'] %}

{% set disease_filter = filter_by_disease('disease_trait', target_diseases) %}

{% if is_incremental() %}
    {% set max_ingestion_query %}
        select max(ingestion_date) from {{ this }}
    {% endset %}
    {% set max_ingestion_date = run_query(max_ingestion_query).columns[0][0] %}
{% endif %}

with associations as (
    select * from {{ ref('stg_gwas_associations') }}
    {% if is_incremental() %}
        where ingestion_date > (select max(ingestion_date) from {{ this }})
    {% endif %}
),

risk_score as (
    select
        variant_id
        , chromosome
        , base_pair_locus
        , disease_trait
        , mapped_gene
        , risk_allele
        , odds_ratio
        , ln(odds_ratio) as beta_weight
        , p_value
        , ingestion_date
    from associations
    where odds_ratio > 0 
      and ({{ disease_filter }})
)

select * from risk_score