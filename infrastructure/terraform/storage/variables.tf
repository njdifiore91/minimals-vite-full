# =========================================
# S3 Storage Variables for MCA Application
# =========================================

# Environment Configuration
# -----------------------

variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

variable "aws_region" {
  description = "AWS region for primary bucket deployment"
  type        = string
  default     = "us-east-1"
}

# Bucket Configuration
# -------------------

variable "bucket_name_prefix" {
  description = "Prefix for S3 bucket names"
  type        = string
  default     = "mca-documents"
}

variable "create_production_bucket" {
  description = "Whether to create the production bucket"
  type        = bool
  default     = true
}

variable "create_staging_bucket" {
  description = "Whether to create the staging bucket"
  type        = bool
  default     = true
}

variable "force_destroy" {
  description = "Allow terraform to destroy buckets even if they contain objects"
  type        = bool
  default     = false
}

# Encryption Configuration
# -----------------------

variable "enable_encryption" {
  description = "Enable server-side encryption for S3 buckets"
  type        = bool
  default     = true
}

variable "encryption_algorithm" {
  description = "Server-side encryption algorithm to use"
  type        = string
  default     = "AES256" # AES-256 encryption as specified in the requirements
  
  validation {
    condition     = contains(["AES256", "aws:kms"], var.encryption_algorithm)
    error_message = "Encryption algorithm must be either AES256 or aws:kms."
  }
}

variable "kms_key_id" {
  description = "KMS key ID to use for encryption (if encryption_algorithm is aws:kms)"
  type        = string
  default     = null
}

# Versioning Configuration
# -----------------------

variable "enable_versioning" {
  description = "Enable versioning for document history tracking"
  type        = bool
  default     = true
}

variable "versioning_mfa_delete" {
  description = "Enable MFA delete for versioning"
  type        = bool
  default     = false
}

# Lifecycle Policies
# -----------------

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules for S3 buckets"
  type        = bool
  default     = true
}

variable "minimum_retention_days" {
  description = "Minimum retention period for objects in days"
  type        = number
  default     = 30 # 30-day minimum retention as specified in the requirements
  
  validation {
    condition     = var.minimum_retention_days >= 30
    error_message = "Minimum retention period must be at least 30 days for compliance."
  }
}

variable "transition_to_ia_days" {
  description = "Days after which objects transition to Infrequent Access storage class"
  type        = number
  default     = 90
}

variable "transition_to_glacier_days" {
  description = "Days after which objects transition to Glacier storage class"
  type        = number
  default     = 180
}

variable "expiration_days" {
  description = "Days after which objects expire (if configured)"
  type        = number
  default     = 2555 # ~7 years for long-term retention
}

# Replication Configuration
# ------------------------

variable "enable_replication" {
  description = "Enable cross-region replication for disaster recovery"
  type        = bool
  default     = false
}

variable "replication_region" {
  description = "AWS region for replica bucket (if replication is enabled)"
  type        = string
  default     = "us-west-2"
}

variable "replication_role_arn" {
  description = "IAM role ARN for replication (if replication is enabled)"
  type        = string
  default     = null
}

# Access Control
# -------------

variable "block_public_access" {
  description = "Enable S3 block public access settings"
  type        = bool
  default     = true
}

variable "signed_url_expiration" {
  description = "Expiration time for signed URLs in minutes"
  type        = number
  default     = 15 # 15-minute expiration as specified in the requirements
}

# Upload Configuration
# -------------------

variable "multipart_threshold" {
  description = "Size threshold in MB for multipart uploads"
  type        = number
  default     = 100 # Multi-part uploads for files >100MB as specified
}

# Monitoring and Logging
# ---------------------

variable "enable_request_metrics" {
  description = "Enable request metrics for S3 buckets"
  type        = bool
  default     = true
}

variable "enable_object_level_logging" {
  description = "Enable object-level logging for S3 buckets"
  type        = bool
  default     = true
}

variable "access_logs_bucket" {
  description = "Bucket name for S3 access logs"
  type        = string
  default     = null
}

variable "access_logs_prefix" {
  description = "Prefix for S3 access logs"
  type        = string
  default     = "s3-access-logs/"
}

# Tags
# ----

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "production_tags" {
  description = "Additional tags to apply to production resources"
  type        = map(string)
  default     = {}
}

variable "staging_tags" {
  description = "Additional tags to apply to staging resources"
  type        = map(string)
  default     = {}
}