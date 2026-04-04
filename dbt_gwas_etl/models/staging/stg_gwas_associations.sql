{{ config(
    materialized='incremental',
    unique_key='variant_id',
    cluster_by=['disease_trait', 'ingestion_date'],
    incremental_strategy='merge',
    on_schema_change='sync_all_columns'
) }}

with raw_source as (
    select * from {{ source('gwas_catalog', 'GWAS_ASSOCIATIONS_FULL') }}

    {% if is_incremental() %}
        where DATE_ADDED_TO_CATALOG > (select max(ingestion_date) from {{ this }})
    {% endif %}
),

gwas_associations as (
    select
        -- Genetic variant identifiers and genomic mapping
        upper(SNPS) as variant_id
        , upper(CHR_ID) as chromosome
        , cast(regexp_substr(CHR_POS, '^[0-9]+') as integer) as base_pair_locus
        , REGION as region

        -- Phenotypic information and trait mapping
        , DISEASE_TRAIT as disease_trait
        , MAPPED_GENE as mapped_gene
        , "REPORTED_GENE(S)" as reported_genes
        , "STRONGEST_SNP-RISK_ALLELE" as risk_allele

        -- Statistical metrics 
        , cast("P-VALUE" as float) as p_value
        , cast(OR_OR_BETA as float) as odds_ratio
        , cast(regexp_substr(nullif(RISK_ALLELE_FREQUENCY, 'NR'), '[0-9]+\\.?[0-9]*') as float) as risk_allele_freq
       

        -- Ingestion metadata
        , DATE_ADDED_TO_CATALOG as ingestion_date
    
        from raw_source

        /* Genome-Wide significant threshold, standard bioinformatics practice 
        filters for p-values <= 5e-8 to minimize false positives in genomic associations.*/
        where cast(p_value as float) <= 5e-8
)

select * from gwas_associations