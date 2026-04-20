# Database
resource "snowflake_database" "db" {
  name = "GENOMIC_PROJECT"
}

# Warehouse
resource "snowflake_warehouse" "warehouse" {
  name           = "GENOMIC_WH"
  warehouse_size = "X-SMALL"
  auto_suspend   = 60
  auto_resume    = true
}

# Schemas (Medallion)

# PRIMARY (Bronze / Raw)
resource "snowflake_schema" "primary" {
  database = snowflake_database.db.name
  name     = "PRIMARY_DATA"
}

# SECONDARY (Silver / Clean)
resource "snowflake_schema" "secondary" {
  database = snowflake_database.db.name
  name     = "SECONDARY_DATA"
}

# TERTIARY (Gold / Analytics)
resource "snowflake_schema" "tertiary" {
  database = snowflake_database.db.name
  name     = "TERTIARY_DATA"
}

# Internal Stage
resource "snowflake_stage" "gwas_stage" {
  name     = "GWAS_CATALOG_STAGE"
  database = snowflake_database.db.name
  schema   = snowflake_schema.primary.name

  comment = "Internal stage for GWAS Catalog Parquet ingestion"
}

# Parquet File format_type
resource "snowflake_file_format" "parquet_format" {
  name        = "PARQUET_FORMAT"
  database    = snowflake_database.db.name
  schema      = snowflake_schema.primary.name
  format_type = "PARQUET"
}