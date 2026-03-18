variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "log-analytics-engine"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "db_password" {
  description = "Postgres password"
  type        = string
  sensitive   = true
  default     = "logpass-prod-2026"
}