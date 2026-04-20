{{ config(
    materialized='table'
) }}

with risk_data as (
    select * from {{ ref('fct_gwas_risk_score') }}
),

gene_info as (
    select * from {{ source('secondary_data', 'GENES_METADATA') }}
)

select
    r.variant_id
    , r.disease_trait
    , r.beta_weight
    , r.mapped_gene
    , g.gene_function
    , g.pathway
    , coalesce(g.is_immune_related, false) as is_immune_related
from risk_data r
left join gene_info g 
    on trim(upper(r.mapped_gene)) = trim(upper(g.gene_name))