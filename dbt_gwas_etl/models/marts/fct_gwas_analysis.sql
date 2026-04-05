{{ config(materialized='table') }}

with facts as (
    select * from {{ ref('fct_gwas_risk_score') }}
),

dim_genes as (
    select * from {{ ref('dim_gene_context') }}
)

select
    -- Facts Data (FCT)
    f.chromosome,
    f.base_pair_locus as position,
    f.disease_trait as phenotype,
    f."P_VALUE",
    f.beta_weight,
    f.odds_ratio,
    f.variant_id,
    f.risk_allele,

    -- Dimension Data (DIM)
    d.mapped_gene,
    d.gene_function
from facts f
left join dim_genes d on f.variant_id = d.variant_id