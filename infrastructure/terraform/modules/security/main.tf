# Security Module - Main Configuration
#
# This module implements security infrastructure for the MCA Application Processing System
# including IAM roles, security groups, KMS keys, and other security-related resources.
# It supports multiple environments (development, staging, production) with consistent
# naming conventions and tagging strategies.
#
# The module provides:
# - Environment-specific security configurations
# - Consistent resource naming with environment prefixes
# - Standardized tagging for all security resources
# - Security group rules for microservices
# - Network security configurations
# - S3 bucket encryption settings
# - JWT authentication parameters

# Define required Terraform version and providers
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 3.1.0"
    }
  }
}

# Input variables for the security module
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "project" {
  description = "Project name for resource naming and tagging"
  type        = string
  default     = "MCA-Application-Processing"
}

variable "aws_region" {
  description = "AWS region for deploying security resources"
  type        = string
  default     = "us-east-1"
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP CIDR ranges for administrative access"
  type        = list(string)
  default     = []
}

variable "key_rotation_period" {
  description = "Number of days for KMS key rotation period"
  type        = number
  default     = 90
}

variable "enable_field_level_encryption" {
  description = "Enable field-level encryption for PII data"
  type        = bool
  default     = true
}

variable "enable_s3_encryption" {
  description = "Enable S3 server-side encryption for document storage"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Enable AWS CloudTrail for security audit logging"
  type        = bool
  default     = true
}

# Local variables for consistent resource naming and tagging
locals {
  # Environment-specific prefixes for resource naming
  env_prefix = {
    development = "dev"
    staging     = "stg"
    production  = "prod"
  }

  # Common tags to be applied to all resources
  common_tags = {
    Project     = var.project
    ManagedBy   = "Terraform"
    Environment = var.environment
    CreatedAt   = timestamp()
  }

  # Resource-specific tags
  security_tags = merge(local.common_tags, {
    Component = "Security"
  })

  # Service-specific tags for IAM roles and policies
  service_tags = {
    email_service        = merge(local.common_tags, { Service = "EmailService" })
    document_service     = merge(local.common_tags, { Service = "DocumentService" })
    ocr_service          = merge(local.common_tags, { Service = "OCRService" })
    data_service         = merge(local.common_tags, { Service = "DataService" })
    notification_service = merge(local.common_tags, { Service = "NotificationService" })
    api_gateway          = merge(local.common_tags, { Service = "APIGateway" })
  }

  # Naming convention for security resources with environment prefix
  name_prefix = "${local.env_prefix[var.environment]}-mca-security"
  
  # Service-specific resource naming
  service_name_prefix = {
    email_service        = "${local.env_prefix[var.environment]}-mca-email"
    document_service     = "${local.env_prefix[var.environment]}-mca-document"
    ocr_service          = "${local.env_prefix[var.environment]}-mca-ocr"
    data_service         = "${local.env_prefix[var.environment]}-mca-data"
    notification_service = "${local.env_prefix[var.environment]}-mca-notification"
    api_gateway          = "${local.env_prefix[var.environment]}-mca-api"
  }
  
  # Security configuration based on environment
  security_config = {
    development = {
      token_expiry_minutes = 60
      refresh_token_days  = 7
      tls_version         = "TLSv1.2"
      cipher_suites       = ["TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"]
      s3_encryption       = "AES256"
      kms_key_rotation    = true
      jwt_algorithm       = "RS256"
      rate_limits = {
        authenticated   = 60
        unauthenticated = 10
      }
    }
    staging = {
      token_expiry_minutes = 60
      refresh_token_days  = 7
      tls_version         = "TLSv1.3"
      cipher_suites       = ["TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384"]
      s3_encryption       = "AES256"
      kms_key_rotation    = true
      jwt_algorithm       = "RS256"
      rate_limits = {
        authenticated   = 60
        unauthenticated = 10
      }
    }
    production = {
      token_expiry_minutes = 60
      refresh_token_days  = 7
      tls_version         = "TLSv1.3"
      cipher_suites       = ["TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384"]
      s3_encryption       = "AES256"
      kms_key_rotation    = true
      jwt_algorithm       = "RS256"
      rate_limits = {
        authenticated   = 60
        unauthenticated = 10
      }
    }
  }
  
  # S3 bucket naming for document storage
  s3_bucket_names = {
    development = "mca-documents-development"
    staging     = "mca-documents-staging"
    production  = "mca-documents-production"
  }
  
  # Network security configuration
  network_security = {
    development = {
      vpc_cidr_block = "10.0.0.0/16"
      allowed_ips    = ["0.0.0.0/0"] # Open in development, restrict in other environments
    }
    staging = {
      vpc_cidr_block = "10.1.0.0/16"
      allowed_ips    = var.allowed_ip_ranges # Restricted IP ranges for staging
    }
    production = {
      vpc_cidr_block = "10.2.0.0/16"
      allowed_ips    = var.allowed_ip_ranges # Restricted IP ranges for production
    }
  }
  
  # Security group rules for microservices
  security_group_rules = {
    # Email Service security rules
    email_service = {
      ingress = [
        {
          description = "IMAPS from VPC"
          from_port   = 993
          to_port     = 993
          protocol    = "tcp"
          cidr_blocks = [local.network_security[var.environment].vpc_cidr_block]
        }
      ]
      egress = [
        {
          description = "Allow all outbound traffic"
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    
    # API Gateway security rules
    api_gateway = {
      ingress = [
        {
          description = "HTTPS from anywhere"
          from_port   = 443
          to_port     = 443
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
      egress = [
        {
          description = "Allow all outbound traffic"
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    
    # Internal services common rules (document, ocr, data, notification)
    internal_services = {
      ingress = [
        {
          description = "Internal service communication"
          from_port   = 8080
          to_port     = 8080
          protocol    = "tcp"
          cidr_blocks = [local.network_security[var.environment].vpc_cidr_block]
        }
      ]
      egress = [
        {
          description = "Allow all outbound traffic"
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
  }
}

# Output variables from the security module
output "name_prefix" {
  description = "Environment-specific name prefix for security resources"
  value       = local.name_prefix
}

output "common_tags" {
  description = "Common tags to be applied to all resources"
  value       = local.common_tags
}

output "security_tags" {
  description = "Security-specific resource tags"
  value       = local.security_tags
}

output "service_name_prefix" {
  description = "Service-specific resource naming prefixes"
  value       = local.service_name_prefix
}

output "security_config" {
  description = "Environment-specific security configuration"
  value       = local.security_config[var.environment]
}

output "s3_bucket_name" {
  description = "Environment-specific S3 bucket name for document storage"
  value       = local.s3_bucket_names[var.environment]
}

output "network_security" {
  description = "Network security configuration for the current environment"
  value       = local.network_security[var.environment]
}

output "security_group_rules" {
  description = "Security group rules for microservices"
  value       = local.security_group_rules
}