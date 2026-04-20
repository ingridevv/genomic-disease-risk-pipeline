import os
import io
import zipfile
import logging
import requests
import pandas as pd
import snowflake.connector
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from snowflake.connector.pandas_tools import write_pandas

# --- 1. Logging Configuration ---
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"gwas_ingestion_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(module)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GWASDataPipeline:
    """
    ETL Pipeline for GWAS Catalog Genomic Associations Ingestion into Snowflake.
    Following data engineering standards for scalability and auditability.
    """
    
    def __init__(self):
        load_dotenv()
        self.url = "https://ftp.ebi.ac.uk/pub/databases/gwas/releases/2026/01/20/gwas-catalog-associations_ontology-annotated-full.zip"
        self.table_name = "GWAS_ASSOCIATIONS_FULL"
        self.conn = None

    def create_snowflake_connection(self):
        """Establishes connection to Snowflake using environment variables."""
        try:
            self.conn = snowflake.connector.connect(
                user=os.getenv("SF_USER"),
                password=os.getenv("SF_PASSWORD"),
                account=os.getenv("SF_ACCOUNT"),
                warehouse=os.getenv("SF_WAREHOUSE"),
                database=os.getenv("SF_DATABASE"),
                schema=os.getenv("SF_SCHEMA")
            )
            logger.info("Successfully established Snowflake connection.")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    def download_and_extract(self):
        """Fetches the genomic dataset from EBI FTP and extracts TSV content in-memory."""
        logger.info(f"Initiating download from: {self.url}")
        try:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                target_file = z.namelist()[0]
                logger.info(f"Extracting genomic payload: {target_file}")
                with z.open(target_file) as f:
                    # Using '\t' for TSV and low_memory to handle large genomic matrices
                    return pd.read_csv(f, sep='\t', low_memory=False)
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during download: {e}")
            raise

    def transform_metadata(self, df):
        """Normalizes column headers to compliant Snowflake identifiers."""
        logger.info("Normalizing dataframe schema for Snowflake compliance.")
        df.columns = [
            col.upper().replace(' ', '_').replace('.', '_').replace('/', '_') 
            for col in df.columns
        ]
        return df

    def load_to_snowflake(self, df):
        """Executes bulk loading into Snowflake's Primary Data layer."""
        if self.conn is None:
            self.create_snowflake_connection()
            
        try:
            logger.info(f"Streaming {len(df):,} records to Snowflake...")
            success, nchunks, nrows, _ = write_pandas(
                conn=self.conn,
                df=df,
                table_name=self.table_name,
                auto_create_table=True,
                overwrite=True
            )
            if success:
                logger.info(f"Ingestion complete. {nrows:,} rows committed to {self.table_name}.")
        except Exception as e:
            logger.error(f"Load failure: {e}", exc_info=True)
            raise
        finally:
            if self.conn:
                self.conn.close()
                logger.info("Snowflake connection closed.")

    def run(self):
        """Pipeline Orchestration Logic."""
        start_time = datetime.now()
        logger.info("--- GWAS Ingestion Pipeline Started ---")
        
        try:
            raw_data = self.download_and_extract()
            processed_data = self.transform_metadata(raw_data)
            self.load_to_snowflake(processed_data)
            
            duration = datetime.now() - start_time
            logger.info(f"--- Pipeline Finished Successfully | Execution Time: {duration} ---")
        except Exception as e:
            logger.critical(f"Pipeline crashed. Critical error: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    try:
        pipeline = GWASDataPipeline()
        pipeline.run()
    except Exception as e:
        logger.critical(f"Fatal error: Pipeline execution failed. {e}", exc_info=True)
        exit(1)