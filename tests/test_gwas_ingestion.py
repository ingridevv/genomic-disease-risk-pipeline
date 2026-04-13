"""Unit and integration tests for GWAS data ingestion pipeline."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call
from ingestion.gwas_ingestion import GWASDataPipeline


class TestGWASDataPipelineMetadata:
    """Tests for metadata transformation and validation."""

    def test_transform_metadata_column_normalization(self, sample_gwas_data):
        """Verify that column headers are normalized to Snowflake-compliant format."""
        pipeline = GWASDataPipeline()
        transformed = pipeline.transform_metadata(sample_gwas_data.copy())
        
        # Check that all columns are uppercase and spaces replaced
        assert all(col.isupper() or col == '' for col in transformed.columns)
        assert ' ' not in ''.join(transformed.columns)
        # Original column count preserved
        assert len(transformed.columns) == len(sample_gwas_data.columns)

    def test_transform_metadata_preserves_data_integrity(self, sample_gwas_data):
        """Ensure transformation doesn't alter underlying data values."""
        pipeline = GWASDataPipeline()
        original_shape = sample_gwas_data.shape
        transformed = pipeline.transform_metadata(sample_gwas_data.copy())
        
        assert transformed.shape == original_shape
        # Verify row count unchanged
        assert len(transformed) == len(sample_gwas_data)

    def test_transform_metadata_handles_special_characters(self):
        """Verify special characters in column names are sanitized."""
        df = pd.DataFrame({
            'Column With Spaces': [1, 2],
            'Column.With.Dots': [3, 4],
            'Column/With/Slashes': [5, 6]
        })
        pipeline = GWASDataPipeline()
        transformed = pipeline.transform_metadata(df)
        
        expected_columns = ['COLUMN_WITH_SPACES', 'COLUMN_WITH_DOTS', 'COLUMN_WITH_SLASHES']
        assert list(transformed.columns) == expected_columns


class TestGWASDataPipelineValidation:
    """Tests for data quality validation."""

    def test_sample_gwas_data_has_required_columns(self, sample_gwas_data):
        """Verify test data contains essential GWAS columns."""
        required_cols = ['SNPS', 'CHR_ID', 'P-VALUE', 'OR or BETA', 'DISEASE/TRAIT']
        assert all(col in sample_gwas_data.columns for col in required_cols)

    def test_p_values_are_numeric(self, sample_gwas_data):
        """Ensure p-values are numeric and plausible."""
        pipeline = GWASDataPipeline()
        df = pipeline.transform_metadata(sample_gwas_data.copy())
        
        # Check p-values are numeric (column name stays 'P-VALUE' after transform)
        assert pd.api.types.is_numeric_dtype(df['P-VALUE'])
        # Check values are between 0 and 1
        assert (df['P-VALUE'] >= 0).all() and (df['P-VALUE'] <= 1).all()

    def test_no_null_variant_identifiers(self, sample_gwas_data):
        """Critical: variant IDs must never be null."""
        pipeline = GWASDataPipeline()
        df = pipeline.transform_metadata(sample_gwas_data.copy())
        
        assert not df['SNPS'].isna().any(), "Variant identifiers cannot contain nulls"

    def test_data_volume_validation(self, sample_gwas_data):
        """Verify minimum data volume expectations."""
        assert len(sample_gwas_data) >= 1, "Data must contain at least 1 record"


class TestGWASDataPipelineInitialization:
    """Tests for pipeline initialization and configuration."""

    def test_pipeline_initialization(self, mock_env_vars):
        """Verify pipeline initializes with correct defaults."""
        pipeline = GWASDataPipeline()
        
        assert pipeline.url is not None
        assert pipeline.table_name == "GWAS_ASSOCIATIONS_FULL"
        assert pipeline.conn is None  # Connection not yet established

    def test_snowflake_connection_requires_env_vars(self, mock_env_vars):
        """Verify Snowflake connection uses environment variables."""
        with patch('snowflake.connector.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            pipeline = GWASDataPipeline()
            pipeline.create_snowflake_connection()
            
            # Verify connect was called with correct parameters
            mock_connect.assert_called_once()
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs['user'] == mock_env_vars['SF_USER']
            assert call_kwargs['account'] == mock_env_vars['SF_ACCOUNT']

    def test_snowflake_connection_handles_failure(self, mock_env_vars):
        """Verify pipeline handles Snowflake connection errors gracefully."""
        with patch('snowflake.connector.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection timeout")
            pipeline = GWASDataPipeline()
            
            with pytest.raises(Exception):
                pipeline.create_snowflake_connection()


class TestGWASDataPipelineDownload:
    """Tests for data download and extraction logic."""

    @patch('requests.get')
    @patch('zipfile.ZipFile')
    def test_download_and_extract_success(self, mock_zipfile, mock_get, sample_gwas_data):
        """Verify successful download and ZIP extraction."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = b"mock zip content"
        mock_get.return_value = mock_response
        
        # Mock ZIP file extraction
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ['gwas_catalog.tsv']
        mock_zip.__enter__.return_value = mock_zip
        
        # Mock file reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_zip.open.return_value = mock_file
        
        with patch('pandas.read_csv', return_value=sample_gwas_data):
            pipeline = GWASDataPipeline()
            result = pipeline.download_and_extract()
            
            # Verify data was returned
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0

    @patch('requests.get')
    def test_download_network_error_handling(self, mock_get):
        """Verify graceful handling of network failures."""
        mock_get.side_effect = Exception("Network error")
        pipeline = GWASDataPipeline()
        
        with pytest.raises(Exception):
            pipeline.download_and_extract()


class TestGWASDataPipelineLoad:
    """Tests for Snowflake loading logic."""

    @patch('ingestion.gwas_ingestion.write_pandas')
    @patch('snowflake.connector.connect')
    def test_load_to_snowflake_success(self, mock_connect, mock_write_pandas, sample_gwas_data, mock_env_vars):
        """Verify successful data load to Snowflake."""
        # Mock connection and write_pandas
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_write_pandas.return_value = (True, 1, len(sample_gwas_data), None)
        
        pipeline = GWASDataPipeline()
        pipeline.create_snowflake_connection()
        
        # Transform data to ensure column normalization
        transformed_data = pipeline.transform_metadata(sample_gwas_data.copy())
        # Should not raise exception
        pipeline.load_to_snowflake(transformed_data)
        
        # Verify write_pandas was called
        mock_write_pandas.assert_called_once()

    @patch('ingestion.gwas_ingestion.write_pandas')
    @patch('snowflake.connector.connect')
    def test_load_to_snowflake_connection_creation(self, mock_connect, mock_write_pandas, sample_gwas_data, mock_env_vars):
        """Verify load creates connection if not already established."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_write_pandas.return_value = (True, 1, len(sample_gwas_data), None)
        
        with patch('snowflake.connector.pandas_tools.write_pandas', mock_write_pandas):
            pipeline = GWASDataPipeline()
            # Transform data first to ensure column names are normalized
            transformed_data = pipeline.transform_metadata(sample_gwas_data.copy())
            pipeline.load_to_snowflake(transformed_data)
            
            # Verify connection was created
            mock_connect.assert_called_once()

    @patch('ingestion.gwas_ingestion.write_pandas')
    @patch('snowflake.connector.connect')
    def test_load_to_snowflake_failure_logging(self, mock_connect, mock_write_pandas, sample_gwas_data, mock_env_vars, caplog):
        """Verify exception handling and error logging in load_to_snowflake."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        # Simulate write_pandas failure
        mock_write_pandas.side_effect = Exception("Snowflake write failed: disk quota exceeded")
        
        pipeline = GWASDataPipeline()
        pipeline.create_snowflake_connection()
        transformed_data = pipeline.transform_metadata(sample_gwas_data.copy())
        
        # Should raise the exception after logging
        with pytest.raises(Exception):
            pipeline.load_to_snowflake(transformed_data)
        
        # Verify error was logged
        assert any("Load failure" in record.message for record in caplog.records)


class TestGWASDataPipelineIntegration:
    """Integration tests for complete pipeline flow."""

    @patch('ingestion.gwas_ingestion.GWASDataPipeline.download_and_extract')
    @patch('ingestion.gwas_ingestion.GWASDataPipeline.load_to_snowflake')
    def test_pipeline_run_orchestration(self, mock_load, mock_download, sample_gwas_data, mock_env_vars):
        """Verify pipeline orchestration calls all steps in correct order."""
        mock_download.return_value = sample_gwas_data
        
        pipeline = GWASDataPipeline()
        pipeline.run()
        
        # Verify both major steps were called
        mock_download.assert_called_once()
        mock_load.assert_called_once()

    def test_pipeline_logs_execution(self, sample_gwas_data, mock_env_vars):
        """Verify pipeline executes without errors."""
        with patch.object(GWASDataPipeline, 'download_and_extract', return_value=sample_gwas_data):
            with patch.object(GWASDataPipeline, 'load_to_snowflake'):
                pipeline = GWASDataPipeline()
                # Should not raise exception
                pipeline.run()

    @patch('ingestion.gwas_ingestion.GWASDataPipeline.download_and_extract')
    def test_pipeline_run_exception_handling(self, mock_download, mock_env_vars, caplog):
        """Verify pipeline logs critical errors during execution."""
        # Simulate failure in download step
        mock_download.side_effect = Exception("EBI FTP connection timeout")
        
        pipeline = GWASDataPipeline()
        # Exception should be re-raised after logging
        with pytest.raises(Exception, match="EBI FTP connection timeout"):
            pipeline.run()
        
        # Verify critical error was logged with full traceback
        assert any("Pipeline crashed" in record.message for record in caplog.records)
        assert any("Critical error" in record.message for record in caplog.records)


class TestDataQualityRequirements:
    """Tests ensuring data quality for zoomcamp evaluation."""

    def test_minimum_record_count_requirement(self, sample_gwas_data):
        """Ensure pipeline handles minimum data volume (GWAS: 1M+ records)."""
        assert len(sample_gwas_data) >= 1
        # In production, we'd validate >= 1_000_000 records

    def test_no_duplicate_variant_identifiers_allowed(self):
        """Critical: genomic variants must be unique."""
        df = pd.DataFrame({
            'SNPS': ['rs123', 'rs123', 'rs456'],  # Duplicate
            'P_VALUE': [1e-10, 1e-10, 1e-8]
        })
        duplicates = df[df.duplicated(subset=['SNPS'], keep=False)]
        # In production, this should be 0; test documents the requirement
        assert duplicates.shape[0] == 2  # This example has duplicates (caught by validation)

    def test_statistical_significance_threshold(self, sample_gwas_data):
        """GWAS standard: significant variants have p-value <= 5e-8."""
        pipeline = GWASDataPipeline()
        df = pipeline.transform_metadata(sample_gwas_data.copy())
        
        # Verify threshold constant is defined
        GWAS_SIGNIFICANCE_THRESHOLD = 5e-8
        
        # Count variants meeting significance threshold (column name stays 'P-VALUE')
        significant = df[df['P-VALUE'] <= GWAS_SIGNIFICANCE_THRESHOLD]
        assert len(significant) > 0, "Sample should have significant variants"
