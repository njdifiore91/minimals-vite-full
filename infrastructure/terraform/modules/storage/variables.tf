# -----------------------------------------------
# Storage Module Variables
# -----------------------------------------------
# This file defines all input variables for the storage module, including
# environment names, region settings, bucket configurations, retention periods,
# and security parameters. It enables parameterized deployment of the storage
# infrastructure with environment-specific values.
# -----------------------------------------------

# -----------------------------------------------
# Environment Configuration
# -----------------------------------------------

variable "environment" {
  description = "Deployment environment name (e.g., production, staging)"
  type        = string
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

variable "project" {
  description = "Project identifier used for resource naming"
  type        = string
  default     = "mca"
}

# -----------------------------------------------
# Region Configuration
# -----------------------------------------------

variable "primary_region" {
  description = "Primary AWS region for storage resources"
  type        = string
  default     = "us-east-1"
}

variable "replica_regions" {
  description = "List of replica regions for multi-region replication"
  type        = list(string)
  default     = []
}

variable "enable_replication" {
  description = "Enable cross-region replication for disaster recovery"
  type        = bool
  default     = false
}

# -----------------------------------------------
# Bucket Configuration
# -----------------------------------------------

variable "bucket_name" {
  description = "Base name for S3 buckets (will be prefixed with environment)"
  type        = string
  default     = "documents"
}

variable "bucket_prefix" {
  description = "Prefix to use for all bucket names"
  type        = string
  default     = "dollarfunding"
}

variable "enable_versioning" {
  description = "Enable versioning for document history tracking"
  type        = bool
  default     = true
}

variable "force_destroy" {
  description = "Allow terraform to destroy buckets with content"
  type        = bool
  default     = false
}

variable "storage_class" {
  description = "Default storage class for objects"
  type        = string
  default     = "STANDARD"
  validation {
    condition     = contains(["STANDARD", "REDUCED_REDUNDANCY", "STANDARD_IA", "ONEZONE_IA", "INTELLIGENT_TIERING", "GLACIER", "DEEP_ARCHIVE"], var.storage_class)
    error_message = "Storage class must be a valid S3 storage class."
  }
}

variable "archive_storage_class" {
  description = "Storage class for archived objects"
  type        = string
  default     = "STANDARD_IA"
  validation {
    condition     = contains(["STANDARD_IA", "ONEZONE_IA", "INTELLIGENT_TIERING", "GLACIER", "DEEP_ARCHIVE"], var.archive_storage_class)
    error_message = "Archive storage class must be a valid S3 storage class for infrequent access."
  }
}

# -----------------------------------------------
# Lifecycle Configuration
# -----------------------------------------------

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules for object management"
  type        = bool
  default     = true
}

variable "standard_transition_days" {
  description = "Days after which objects transition to infrequent access storage"
  type        = number
  default     = 90
}

variable "glacier_transition_days" {
  description = "Days after which objects transition to glacier storage"
  type        = number
  default     = 365
}

variable "expiration_days" {
  description = "Days after which objects may be deleted (0 means never expire)"
  type        = number
  default     = 0
}

variable "noncurrent_version_expiration_days" {
  description = "Days after which non-current object versions may be deleted"
  type        = number
  default     = 90
}

variable "minimum_retention_days" {
  description = "Minimum number of days objects must be retained (compliance)"
  type        = number
  default     = 30
}

# -----------------------------------------------
# Security Configuration
# -----------------------------------------------

variable "enable_encryption" {
  description = "Enable server-side encryption for all objects"
  type        = bool
  default     = true
}

variable "encryption_algorithm" {
  description = "Server-side encryption algorithm"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "aws:kms"], var.encryption_algorithm)
    error_message = "Encryption algorithm must be either AES256 or aws:kms."
  }
}

variable "kms_key_id" {
  description = "KMS key ID for server-side encryption (if aws:kms is used)"
  type        = string
  default     = ""
}

variable "block_public_access" {
  description = "Enable block public access settings for buckets"
  type        = bool
  default     = true
}

variable "enable_ssl_requests" {
  description = "Enforce SSL for all bucket requests"
  type        = bool
  default     = true
}

variable "signed_url_expiration" {
  description = "Expiration time in seconds for signed URLs"
  type        = number
  default     = 900  # 15 minutes
}

# -----------------------------------------------
# Logging and Monitoring Configuration
# -----------------------------------------------

variable "enable_access_logging" {
  description = "Enable access logging for buckets"
  type        = bool
  default     = true
}

variable "access_log_bucket" {
  description = "Bucket name for access logs (if empty, a log bucket will be created)"
  type        = string
  default     = ""
}

variable "access_log_prefix" {
  description = "Prefix for access logs within the log bucket"
  type        = string
  default     = "bucket-logs/"
}

variable "enable_request_metrics" {
  description = "Enable detailed request metrics for monitoring"
  type        = bool
  default     = true
}

variable "enable_cost_allocation_tags" {
  description = "Enable cost allocation tags for billing analysis"
  type        = bool
  default     = true
}

# -----------------------------------------------
# CORS Configuration
# -----------------------------------------------

variable "enable_cors" {
  description = "Enable CORS configuration for buckets"
  type        = bool
  default     = false
}

variable "cors_allowed_origins" {
  description = "List of origins allowed for CORS requests"
  type        = list(string)
  default     = []
}

variable "cors_allowed_methods" {
  description = "List of HTTP methods allowed for CORS requests"
  type        = list(string)
  default     = ["GET", "HEAD"]
}

variable "cors_allowed_headers" {
  description = "List of headers allowed for CORS requests"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "List of headers exposed to CORS requests"
  type        = list(string)
  default     = ["ETag"]
}

variable "cors_max_age_seconds" {
  description = "Time in seconds browsers can cache CORS preflight responses"
  type        = number
  default     = 3600
}

# -----------------------------------------------
# Object Lock Configuration (for compliance)
# -----------------------------------------------

variable "enable_object_lock" {
  description = "Enable object lock for compliance requirements"
  type        = bool
  default     = false
}

variable "object_lock_mode" {
  description = "Object lock mode (GOVERNANCE or COMPLIANCE)"
  type        = string
  default     = "GOVERNANCE"
  validation {
    condition     = contains(["GOVERNANCE", "COMPLIANCE"], var.object_lock_mode)
    error_message = "Object lock mode must be either GOVERNANCE or COMPLIANCE."
  }
}

variable "object_lock_retention_days" {
  description = "Default retention period in days for object lock"
  type        = number
  default     = 30
}

# -----------------------------------------------
# Notification Configuration
# -----------------------------------------------

variable "enable_notifications" {
  description = "Enable event notifications for bucket events"
  type        = bool
  default     = false
}

variable "notification_events" {
  description = "List of events that trigger notifications"
  type        = list(string)
  default     = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
}

variable "notification_target_arn" {
  description = "ARN of the notification target (SNS, SQS, or Lambda)"
  type        = string
  default     = ""
}

# -----------------------------------------------
# Transfer Acceleration Configuration
# -----------------------------------------------

variable "enable_transfer_acceleration" {
  description = "Enable S3 transfer acceleration for faster uploads"
  type        = bool
  default     = false
}

# -----------------------------------------------
# Intelligent Tiering Configuration
# -----------------------------------------------

variable "enable_intelligent_tiering" {
  description = "Enable S3 Intelligent Tiering for automatic storage class optimization"
  type        = bool
  default     = false
}

variable "intelligent_tiering_days_until_archive" {
  description = "Days until objects are moved to archive access tier"
  type        = number
  default     = 90
}

variable "intelligent_tiering_days_until_deep_archive" {
  description = "Days until objects are moved to deep archive access tier"
  type        = number
  default     = 180
}