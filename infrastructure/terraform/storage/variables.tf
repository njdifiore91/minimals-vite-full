# -----------------------------------------------------------------------------
# S3 Storage Variables for MCA Application Processing System
# -----------------------------------------------------------------------------

# Environment Configuration
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

# Bucket Configuration
# -----------------------------------------------------------------------------

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
  description = "Allow buckets to be destroyed even if they contain objects"
  type        = bool
  default     = false
}

# Encryption Configuration
# -----------------------------------------------------------------------------

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
  description = "KMS key ID to use for encryption if encryption_algorithm is aws:kms"
  type        = string
  default     = null
}

# Versioning Configuration
# -----------------------------------------------------------------------------

variable "enable_versioning" {
  description = "Enable versioning for S3 buckets"
  type        = bool
  default     = true
}

# Lifecycle Policy Configuration
# -----------------------------------------------------------------------------

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules for S3 buckets"
  type        = bool
  default     = true
}

variable "standard_ia_transition_days" {
  description = "Number of days after which objects transition to STANDARD_IA storage class"
  type        = number
  default     = 30
}

variable "glacier_transition_days" {
  description = "Number of days after which objects transition to GLACIER storage class"
  type        = number
  default     = 90
}

variable "expiration_days" {
  description = "Number of days after which objects expire (0 means no expiration)"
  type        = number
  default     = 0 # Default to no expiration
}

variable "noncurrent_version_expiration_days" {
  description = "Number of days after which noncurrent object versions expire"
  type        = number
  default     = 90
}

# Replication and Disaster Recovery Configuration
# -----------------------------------------------------------------------------

variable "enable_replication" {
  description = "Enable cross-region replication for S3 buckets"
  type        = bool
  default     = false
}

variable "replication_region" {
  description = "AWS region for replication destination"
  type        = string
  default     = "us-west-2" # Default secondary region
}

variable "replication_role_arn" {
  description = "ARN of IAM role for S3 replication"
  type        = string
  default     = null
}

# Access Control Configuration
# -----------------------------------------------------------------------------

variable "block_public_access" {
  description = "Enable S3 block public access settings"
  type        = bool
  default     = true
}

variable "enable_signed_urls" {
  description = "Enable signed URLs for secure object access"
  type        = bool
  default     = true
}

variable "signed_url_expiration" {
  description = "Expiration time in seconds for signed URLs"
  type        = number
  default     = 900 # 15 minutes as specified in the requirements
}

# Performance Configuration
# -----------------------------------------------------------------------------

variable "enable_multipart_upload" {
  description = "Enable multipart upload for large files"
  type        = bool
  default     = true
}

variable "multipart_threshold" {
  description = "Size threshold in bytes for multipart uploads"
  type        = number
  default     = 104857600 # 100MB as specified in the requirements
}

# Monitoring and Logging Configuration
# -----------------------------------------------------------------------------

variable "enable_access_logging" {
  description = "Enable access logging for S3 buckets"
  type        = bool
  default     = true
}

variable "access_log_bucket" {
  description = "Name of S3 bucket for access logs"
  type        = string
  default     = null
}

variable "access_log_prefix" {
  description = "Prefix for access log objects"
  type        = string
  default     = "s3-access-logs/"
}

variable "enable_metrics" {
  description = "Enable request metrics for S3 buckets"
  type        = bool
  default     = true
}

variable "metrics_filter_prefix" {
  description = "Prefix filter for metrics"
  type        = string
  default     = ""
}

# Tags Configuration
# -----------------------------------------------------------------------------

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "production_bucket_tags" {
  description = "Additional tags for production bucket"
  type        = map(string)
  default     = {}
}

variable "staging_bucket_tags" {
  description = "Additional tags for staging bucket"
  type        = map(string)
  default     = {}
}