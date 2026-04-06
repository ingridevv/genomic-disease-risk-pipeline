import logging
from ingestion.gwas_ingestion import GWASDataPipeline

def run_gwas_ingestion_task():
    """
    Wrapper function to execute the GWAS ETL process.
    This encapsulates the logic, allowing the DAG to remain 
    strictly for orchestration.
    """
    logging.info("Starting GWAS Ingestion Factory...")
    
    # Initialize your core logic class
    pipeline = GWASDataPipeline()
    
    # Execute the run method (Download -> Extract -> Load)
    pipeline.run()
    
    logging.info("GWAS Ingestion Factory completed successfully.")