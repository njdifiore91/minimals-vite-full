# =============================================================================
# MCA Application Processing System - Messaging Variables
# =============================================================================
# This file defines all input variables for the RabbitMQ messaging module,
# including environment type, instance sizes, security settings, and
# monitoring configurations.
# =============================================================================

variable "environment" {
  description = "The deployment environment (development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "vpc_id" {
  description = "The ID of the VPC where the RabbitMQ cluster will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "The subnet IDs where the RabbitMQ cluster will be deployed"
  type        = list(string)
}

variable "security_group_id" {
  description = "The security group ID for the RabbitMQ cluster"
  type        = string
}

variable "username" {
  description = "The username for RabbitMQ authentication"
  type        = string
  sensitive   = true
}

variable "password" {
  description = "The password for RabbitMQ authentication"
  type        = string
  sensitive   = true
}

variable "kms_key_id" {
  description = "The KMS key ID for encryption"
  type        = string
  default     = ""
}

variable "ca_cert_file" {
  description = "The path to the CA certificate file for TLS verification"
  type        = string
  default     = ""
}

variable "sns_topic_arn" {
  description = "The ARN of the SNS topic for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "tags" {
  description = "A map of tags to apply to all resources"
  type        = map(string)
  default     = {}
}