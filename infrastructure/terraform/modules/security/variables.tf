# Security Module Variables
# This file defines all input variables for the security module including environment settings,
# service names, JWT configuration, S3 bucket names, and API security parameters.

# Environment Configuration
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "mca"
}

# JWT Authentication Configuration
variable "jwt_algorithm" {
  description = "Algorithm used for JWT signing"
  type        = string
  default     = "RS256"
  validation {
    condition     = var.jwt_algorithm == "RS256"
    error_message = "Only RS256 algorithm is supported for JWT signing."
  }
}

variable "jwt_token_expiry" {
  description = "JWT token expiry time in minutes"
  type        = number
  default     = 60
}

variable "jwt_refresh_token_expiry" {
  description = "JWT refresh token expiry time in days"
  type        = number
  default     = 7
}

variable "jwt_issuer" {
  description = "JWT issuer claim value"
  type        = string
  default     = "dollarfunding-mca"
}

variable "jwt_audience" {
  description = "JWT audience claim value"
  type        = string
  default     = "mca-api"
}

variable "jwt_key_rotation_days" {
  description = "Number of days between JWT public key rotations"
  type        = number
  default     = 90
}

# S3 Storage Configuration
variable "s3_bucket_names" {
  description = "Map of S3 bucket names for document storage"
  type        = map(string)
  default     = {
    development = "mca-documents-development"
    staging     = "mca-documents-staging"
    production  = "mca-documents-production"
  }
}

variable "s3_encryption_type" {
  description = "Type of server-side encryption for S3 buckets"
  type        = string
  default     = "AES256" # SSE-S3 with AES-256 encryption
  validation {
    condition     = contains(["AES256", "aws:kms"], var.s3_encryption_type)
    error_message = "Encryption type must be either AES256 (SSE-S3) or aws:kms (SSE-KMS)."
  }
}

variable "use_kms_for_sensitive_documents" {
  description = "Whether to use KMS-managed keys for sensitive document categories"
  type        = bool
  default     = false
}

# API Gateway Security Configuration
variable "api_rate_limit_authenticated" {
  description = "Rate limit for authenticated API requests (requests per minute)"
  type        = number
  default     = 60
}

variable "api_rate_limit_unauthenticated" {
  description = "Rate limit for unauthenticated API requests (requests per minute)"
  type        = number
  default     = 10
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = []
}

variable "admin_ip_allowlist" {
  description = "List of IP addresses allowed to access administrative endpoints"
  type        = list(string)
  default     = []
  sensitive   = true
}

# TLS Configuration
variable "tls_minimum_version" {
  description = "Minimum TLS version required for service communications"
  type        = string
  default     = "TLSv1.3"
  validation {
    condition     = var.tls_minimum_version == "TLSv1.3"
    error_message = "TLS version 1.3 is required for all service communications."
  }
}

variable "tls_cipher_suites" {
  description = "List of allowed TLS cipher suites"
  type        = list(string)
  default     = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256"
  ]
}

# Field-Level Encryption Configuration
variable "field_encryption_enabled" {
  description = "Whether to enable field-level encryption for PII"
  type        = bool
  default     = true
}

variable "pii_field_patterns" {
  description = "List of field name patterns that should be encrypted as PII"
  type        = list(string)
  default     = [
    ".*name",
    ".*email",
    ".*phone",
    ".*address",
    ".*ssn",
    ".*ein",
    ".*tax_id",
    ".*account_number",
    ".*routing_number"
  ]
}

# Message Broker Security Configuration
variable "rabbitmq_tls_enabled" {
  description = "Whether to enable TLS for RabbitMQ connections"
  type        = bool
  default     = true
}

variable "redis_tls_enabled" {
  description = "Whether to enable TLS for Redis connections"
  type        = bool
  default     = true
}

# Content Security Configuration
variable "allowed_file_types" {
  description = "List of allowed file types for document uploads"
  type        = list(string)
  default     = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv"
  ]
}

variable "max_file_size_mb" {
  description = "Maximum allowed file size in MB"
  type        = number
  default     = 10
}

variable "enable_malware_scanning" {
  description = "Whether to enable malware scanning for uploaded documents"
  type        = bool
  default     = true
}

# Webhook Security Configuration
variable "webhook_hmac_enabled" {
  description = "Whether to enable HMAC signatures for webhook payloads"
  type        = bool
  default     = true
}

variable "webhook_retry_count" {
  description = "Maximum number of retry attempts for failed webhook deliveries"
  type        = number
  default     = 5
}

variable "webhook_retry_interval_seconds" {
  description = "Initial retry interval in seconds (will increase with exponential backoff)"
  type        = number
  default     = 60
}

# Network Security Configuration
variable "network_segmentation_enabled" {
  description = "Whether to enable network segmentation between service groups"
  type        = bool
  default     = true
}

# AWS Credentials Management
variable "aws_credential_rotation_days" {
  description = "Number of days between AWS credential rotations"
  type        = number
  default     = 90
}