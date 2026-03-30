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

# schema
resource "snowflake_schema" "schema" {
  database = snowflake_database.db.name
  name     = "ANALYSIS"
}