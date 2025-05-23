# Variables for Redis Cache Infrastructure

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "AWS region for the Redis cache infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket" {
  description = "S3 bucket name for Terraform state"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access Redis"
  type        = list(string)
  default     = []
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional)"
  type        = string
  default     = ""
}

variable "notification_topic_arn" {
  description = "SNS topic ARN for Redis alarms (optional)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags for Redis resources"
  type        = map(string)
  default     = {}
}