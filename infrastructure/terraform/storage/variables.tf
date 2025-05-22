# Variables for S3-compatible storage infrastructure

variable "environment" {
  description = "Deployment environment (production, staging)"
  type        = string
  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "Environment must be either 'production' or 'staging'."
  }
}

variable "region" {
  description = "AWS region for primary storage resources"
  type        = string
  default     = "us-east-1"
}

variable "replica_region" {
  description = "AWS region for replica storage resources (for cross-region replication)"
  type        = string
  default     = "us-west-2"
}

variable "transition_days" {
  description = "Number of days before transitioning objects to Infrequent Access storage class"
  type        = number
  default     = 30
  validation {
    condition     = var.transition_days >= 30
    error_message = "Transition days must be at least 30 days for compliance requirements."
  }
}

variable "expiration_days" {
  description = "Number of days before expiring objects (set to 0 to disable expiration)"
  type        = number
  default     = 0  # Default to no expiration for compliance
}

variable "enable_replication" {
  description = "Enable cross-region replication for disaster recovery"
  type        = bool
  default     = true
}

variable "additional_tags" {
  description = "Additional tags to apply to storage resources"
  type        = map(string)
  default     = {}
}