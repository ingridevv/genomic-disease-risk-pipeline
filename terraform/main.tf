# database
resource "snowflake_database" "db" {
  name = "GENOMIC_PROJECT"
}

# warehouse
resource "snowflake_warehouse" "warehouse" {
  name           = "GENOMIC_WH"
  warehouse_size = "X-SMALL"
  auto_suspend   = 60
  auto_resume    = true
}

# primary layer: raw genomic data as ingested from source
resource "snowflake_schema" "primary" {
  database = snowflake_database.db.name
  name     = "PRIMARY_DATA"
}

# secondary layer: cleaned, filtered and normalized genomic variants 
resource "snowflake_schema" "secondary" {
  database = snowflake_database.db.name
  name     = "SECONDARY_DATA"
}

# gold layer: final analytics, high-value business/clinical insights (the PRS) are stored
resource "snowflake_schema" "tertiary" {
  database = snowflake_database.db.name
  name     = "TERTIARY_DATA"
}