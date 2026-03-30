variable "snowflake_account" {
  type        = string
  description = "Snowflake account identifier. (Ex.: XY12345.us-east-1)"
}

variable "snowflake_user" {
  type = string
}

variable "snowflake_password" {
  type      = string
  sensitive = true
}