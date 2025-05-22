# Variables for PostgreSQL Database Monitoring Configuration

variable "prefix" {
  description = "Prefix to be used for resource naming"
  type        = string
  default     = "mca"
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "db_cluster_identifier" {
  description = "The identifier of the DB cluster"
  type        = string
}

variable "db_instance_identifier" {
  description = "The identifier of the DB instance (for read replica monitoring)"
  type        = string
  default     = ""
}

variable "is_read_replica" {
  description = "Whether the DB instance is a read replica"
  type        = bool
  default     = false
}

variable "max_connections" {
  description = "Maximum number of database connections allowed"
  type        = number
  default     = 100
}

variable "create_cloudwatch_alarms" {
  description = "Whether to create CloudWatch alarms"
  type        = bool
  default     = true
}

variable "create_cloudwatch_dashboard" {
  description = "Whether to create CloudWatch dashboard"
  type        = bool
  default     = true
}

variable "critical_alarm_actions" {
  description = "List of ARNs to notify when a critical alarm transitions to ALARM state"
  type        = list(string)
  default     = []
}

variable "warning_alarm_actions" {
  description = "List of ARNs to notify when a warning alarm transitions to ALARM state"
  type        = list(string)
  default     = []
}

variable "ok_alarm_actions" {
  description = "List of ARNs to notify when an alarm transitions to OK state"
  type        = list(string)
  default     = []
}

variable "enable_datadog_integration" {
  description = "Whether to enable Datadog integration"
  type        = bool
  default     = false
}

variable "datadog_api_key" {
  description = "Datadog API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "datadog_app_key" {
  description = "Datadog application key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "datadog_api_url" {
  description = "Datadog API URL"
  type        = string
  default     = "https://api.datadoghq.com/"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}