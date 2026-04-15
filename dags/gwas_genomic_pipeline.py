import os
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

@dag(
    dag_id='gwas_genomic_pipeline_v1',
    start_date=datetime(2026, 4, 1),
    schedule=None,
    catchup=False,
    tags=['genomics', 'snowflake', 'dbt'],
    default_args={
        'owner': 'Ingrid Silva',
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
    }
)
def gwas_pipeline():
    """
    Genomic Disease Risk Discovery Pipeline.
    
    End-to-end data engineering pipeline for processing GWAS (Genome-Wide Association Studies)
    variants to discover genetic risk factors for Immune-Mediated Inflammatory Diseases (IBD,
    Crohn's Disease, Ulcerative Colitis).
    
    Pipeline Flow:
        1. ingest_task: Download 1.1M+ variants from EBI GWAS Catalog FTP server
                       and bulk load into Snowflake PRIMARY_DATA schema
        2. dbt_transformations: Execute dbt transformations to:
                               - Stage and filter raw GWAS data (p-value ≤ 5e-8)
                               - Create disease-specific risk scores
                               - Enrich variants with gene annotations
                               - Prepare analysis-ready data in TERTIARY_DATA (gold layer)
    
    Task Dependencies: ingest_task >> dbt_transformations
    
    Expected Runtime: 2-5 minutes (1-2 min ingestion + 1-3 min transformation)
    """

    @task()
    def ingest_task():
        try:
            from plugins.helpers.gwas_factory import run_gwas_ingestion_task
            return run_gwas_ingestion_task()
        except ImportError as e:
            print(f"Import error: {e}")
            return None

    dbt_run = BashOperator(
        task_id='dbt_transformations',
        bash_command= (
        'cd /opt/airflow/dbt_gwas_etl && '
        'dbt deps && '
        'dbt seed --profiles-dir . && '
        'dbt run --profiles-dir . --no-partial-parse'
        ),
        cwd='/opt/airflow/dbt_gwas_etl',
        env={
            **os.environ,
            'DBT_PROFILES_DIR': '/opt/airflow/dbt_gwas_etl'
        }
    )

    ingest_task() >> dbt_run


gwas_pipeline()