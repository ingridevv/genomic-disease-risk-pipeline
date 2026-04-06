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
        bash_command='cd /opt/airflow/dbt_gwas_etl && dbt run --no-partial-parse',
        cwd='/opt/airflow/dbt_gwas_etl',
        env={
            **os.environ,
            'DBT_PROFILES_DIR': '/opt/airflow/dbt_gwas_etl'
        }
    )

    ingest_task() >> dbt_run


gwas_pipeline()