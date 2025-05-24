# Security Module - Variables

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "ID of the VPC where security groups will be created"
  type        = string
}

variable "resource_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "kms_key_administrators" {
  description = "List of IAM ARNs that can administer the KMS keys"
  type        = list(string)
  default     = []
}

variable "jwt_issuer" {
  description = "Issuer claim for JWT tokens"
  type        = string
  default     = "dollarfunding-mca"
}

variable "jwt_audience" {
  description = "Audience claim for JWT tokens"
  type        = string
  default     = "mca-application-api"
}

variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway protection"
  type        = bool
  default     = true
}

variable "ip_whitelist" {
  description = "List of IP addresses/ranges allowed to access admin endpoints"
  type        = list(string)
  default     = []
  sensitive   = true
}

variable "enable_field_encryption" {
  description = "Enable field-level encryption for PII data"
  type        = bool
  default     = true
}

variable "enable_malware_scanning" {
  description = "Enable malware scanning for document uploads"
  type        = bool
  default     = true
}