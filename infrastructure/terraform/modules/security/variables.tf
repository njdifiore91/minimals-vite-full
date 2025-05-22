# Variables for the security module

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "mca"
}

variable "organization" {
  description = "Organization name"
  type        = string
  default     = "dollarfunding"
}

# JWT Authentication Variables
variable "jwt_token_expiry_minutes" {
  description = "JWT token expiry time in minutes"
  type        = number
  default     = 60  # 60 minutes as specified in requirements
}

variable "jwt_refresh_token_expiry_days" {
  description = "JWT refresh token expiry time in days"
  type        = number
  default     = 7   # 7 days as specified in requirements
}

variable "jwt_key_rotation_timestamp" {
  description = "Timestamp for JWT key rotation (change to trigger rotation)"
  type        = string
  default     = "2023-01-01T00:00:00Z"
}

# API Security Variables
variable "api_rate_limit_authenticated" {
  description = "Rate limit for authenticated users (requests per minute)"
  type        = number
  default     = 60  # 60 requests per minute as specified in requirements
}

variable "api_rate_limit_unauthenticated" {
  description = "Rate limit for unauthenticated users (requests per minute)"
  type        = number
  default     = 10  # 10 requests per minute as specified in requirements
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = [
    "https://app.dollarfunding.com",
    "https://staging.dollarfunding.com",
    "http://localhost:3000"
  ]
}

variable "admin_ip_allowlist" {
  description = "List of allowed IP addresses for admin endpoints"
  type        = list(string)
  default     = [
    "10.0.0.0/8",     # Internal network
    "172.16.0.0/12",  # Docker network
    "192.168.0.0/16"  # Private network
  ]
}

# S3 Bucket Variables
variable "s3_bucket_names" {
  description = "Names of S3 buckets for document storage"
  type        = map(string)
  default     = {
    documents = "mca-documents"
  }
}

variable "s3_encryption_type" {
  description = "Type of encryption for S3 buckets (AES256 or aws:kms)"
  type        = string
  default     = "AES256"  # AES-256 encryption as specified in requirements
  validation {
    condition     = contains(["AES256", "aws:kms"], var.s3_encryption_type)
    error_message = "S3 encryption type must be one of: AES256, aws:kms."
  }
}

# Service Names
variable "service_names" {
  description = "Names of microservices"
  type        = list(string)
  default     = [
    "email-service",
    "document-service",
    "ocr-service",
    "data-service",
    "notification-service",
    "api-gateway"
  ]
}

# EKS OIDC Provider
variable "eks_oidc_provider" {
  description = "The OpenID Connect provider URL for the EKS cluster (without the https:// prefix)"
  type        = string
  default     = ""
}