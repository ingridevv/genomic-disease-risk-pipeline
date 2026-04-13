"""Pytest configuration and shared fixtures for HELIOX test suite."""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import os


@pytest.fixture
def sample_gwas_data():
    """Sample GWAS data matching EBI Catalog format."""
    return pd.DataFrame({
        'SNPS': ['rs1123456', 'rs2234567', 'rs3345678'],
        'CHR_ID': ['1', '2', '3'],
        'CHR_POS': [123456, 234567, 345678],
        'P-VALUE': [1.5e-10, 3.2e-9, 2.1e-8],
        'OR or BETA': [1.25, 1.15, 1.08],
        'MAPPED_GENE': ['GENE_A', 'GENE_B', 'GENE_C'],
        'DISEASE/TRAIT': ['Crohn\'s disease', 'IBD', 'Ulcerative colitis'],
        'STUDY ACCESSION': ['GCST000001', 'GCST000002', 'GCST000003']
    })


@pytest.fixture
def mock_snowflake_connection():
    """Mock Snowflake connection for testing."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for Snowflake connection."""
    env_vars = {
        'SF_ACCOUNT': 'test_account',
        'SF_USER': 'test_user',
        'SF_PASSWORD': 'test_password',
        'SF_WAREHOUSE': 'TEST_WH',
        'SF_DATABASE': 'TEST_DB',
        'SF_SCHEMA': 'PRIMARY_DATA'
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def temp_log_dir(tmp_path, monkeypatch):
    """Create temporary directory for logs during testing."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    return log_dir
