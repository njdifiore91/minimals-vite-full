# infrastructure/terraform/global/storage.tf

# This file provisions global storage resources including S3 buckets for document storage,
# artifacts, and Terraform state. It creates the persistent storage infrastructure needed
# across all environments.

# Provider configuration is assumed to be defined elsewhere

# ---------------------------------------------------------------------------------------------------------------------
# Document Storage Buckets
# ---------------------------------------------------------------------------------------------------------------------

# Production document storage bucket
resource "aws_s3_bucket" "documents_production" {
  bucket = "mca-documents-production"
  
  # Prevent accidental deletion of this bucket
  force_destroy = false
  
  tags = {
    Name        = "MCA Documents Production"
    Environment = "production"
    Service     = "document-storage"
    ManagedBy   = "terraform"
  }
}

# Staging document storage bucket
resource "aws_s3_bucket" "documents_staging" {
  bucket = "mca-documents-staging"
  
  # Prevent accidental deletion of this bucket
  force_destroy = false
  
  tags = {
    Name        = "MCA Documents Staging"
    Environment = "staging"
    Service     = "document-storage"
    ManagedBy   = "terraform"
  }
}

# Development document storage bucket
resource "aws_s3_bucket" "documents_development" {
  bucket = "mca-documents-development"
  
  # Allow deletion in development environment
  force_destroy = true
  
  tags = {
    Name        = "MCA Documents Development"
    Environment = "development"
    Service     = "document-storage"
    ManagedBy   = "terraform"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Versioning Configuration
# ---------------------------------------------------------------------------------------------------------------------

# Enable versioning for production bucket
resource "aws_s3_bucket_versioning" "documents_production_versioning" {
  bucket = aws_s3_bucket.documents_production.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning for staging bucket
resource "aws_s3_bucket_versioning" "documents_staging_versioning" {
  bucket = aws_s3_bucket.documents_staging.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning for development bucket
resource "aws_s3_bucket_versioning" "documents_development_versioning" {
  bucket = aws_s3_bucket.documents_development.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Server-Side Encryption Configuration
# ---------------------------------------------------------------------------------------------------------------------

# Enable AES-256 encryption for production bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "documents_production_encryption" {
  bucket = aws_s3_bucket.documents_production.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable AES-256 encryption for staging bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "documents_staging_encryption" {
  bucket = aws_s3_bucket.documents_staging.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable AES-256 encryption for development bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "documents_development_encryption" {
  bucket = aws_s3_bucket.documents_development.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Lifecycle Configuration
# ---------------------------------------------------------------------------------------------------------------------

# Lifecycle rules for production bucket
resource "aws_s3_bucket_lifecycle_configuration" "documents_production_lifecycle" {
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.documents_production_versioning]
  
  bucket = aws_s3_bucket.documents_production.id

  # Rule for transitioning old document versions to cheaper storage
  rule {
    id = "archive-old-versions"
    status = "Enabled"

    # Move non-current versions to Infrequent Access after 30 days
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    
    # Move non-current versions to Glacier after 90 days
    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }
    
    # Keep non-current versions for 7 years (2555 days) for compliance
    noncurrent_version_expiration {
      noncurrent_days = 2555
    }
  }
  
  # Rule for cleaning up incomplete multipart uploads
  rule {
    id = "abort-incomplete-uploads"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Lifecycle rules for staging bucket
resource "aws_s3_bucket_lifecycle_configuration" "documents_staging_lifecycle" {
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.documents_staging_versioning]
  
  bucket = aws_s3_bucket.documents_staging.id

  # Rule for transitioning old document versions to cheaper storage
  rule {
    id = "archive-old-versions"
    status = "Enabled"

    # Move non-current versions to Infrequent Access after 30 days
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    
    # Expire non-current versions after 90 days (staging doesn't need long retention)
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
  
  # Rule for cleaning up incomplete multipart uploads
  rule {
    id = "abort-incomplete-uploads"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Lifecycle rules for development bucket
resource "aws_s3_bucket_lifecycle_configuration" "documents_development_lifecycle" {
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.documents_development_versioning]
  
  bucket = aws_s3_bucket.documents_development.id

  # Rule for cleaning up old versions quickly in development
  rule {
    id = "cleanup-old-versions"
    status = "Enabled"
    
    # Expire non-current versions after 30 days (development has shorter retention)
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
  
  # Rule for cleaning up incomplete multipart uploads
  rule {
    id = "abort-incomplete-uploads"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Public Access Block Configuration
# ---------------------------------------------------------------------------------------------------------------------

# Block all public access for production bucket
resource "aws_s3_bucket_public_access_block" "documents_production_public_access_block" {
  bucket = aws_s3_bucket.documents_production.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block all public access for staging bucket
resource "aws_s3_bucket_public_access_block" "documents_staging_public_access_block" {
  bucket = aws_s3_bucket.documents_staging.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block all public access for development bucket
resource "aws_s3_bucket_public_access_block" "documents_development_public_access_block" {
  bucket = aws_s3_bucket.documents_development.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------------------------------------------------
# Deployment Artifacts Bucket
# ---------------------------------------------------------------------------------------------------------------------

# Bucket for storing deployment artifacts
resource "aws_s3_bucket" "deployment_artifacts" {
  bucket = "mca-deployment-artifacts"
  
  # Prevent accidental deletion of this bucket
  force_destroy = false
  
  tags = {
    Name        = "MCA Deployment Artifacts"
    Service     = "ci-cd"
    ManagedBy   = "terraform"
  }
}

# Enable versioning for deployment artifacts bucket
resource "aws_s3_bucket_versioning" "deployment_artifacts_versioning" {
  bucket = aws_s3_bucket.deployment_artifacts.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for deployment artifacts bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "deployment_artifacts_encryption" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access for deployment artifacts bucket
resource "aws_s3_bucket_public_access_block" "deployment_artifacts_public_access_block" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules for deployment artifacts bucket
resource "aws_s3_bucket_lifecycle_configuration" "deployment_artifacts_lifecycle" {
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.deployment_artifacts_versioning]
  
  bucket = aws_s3_bucket.deployment_artifacts.id

  # Rule for cleaning up old artifacts
  rule {
    id = "cleanup-old-artifacts"
    status = "Enabled"
    
    # Expire old versions after 90 days
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Terraform State Bucket
# ---------------------------------------------------------------------------------------------------------------------

# Bucket for storing Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "mca-terraform-state"
  
  # Prevent accidental deletion of this bucket
  force_destroy = false
  
  tags = {
    Name        = "MCA Terraform State"
    Service     = "terraform"
    ManagedBy   = "terraform"
  }
}

# Enable versioning for Terraform state bucket
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for Terraform state bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_encryption" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access for Terraform state bucket
resource "aws_s3_bucket_public_access_block" "terraform_state_public_access_block" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "documents_production_bucket_name" {
  description = "The name of the production documents bucket"
  value       = aws_s3_bucket.documents_production.id
}

output "documents_staging_bucket_name" {
  description = "The name of the staging documents bucket"
  value       = aws_s3_bucket.documents_staging.id
}

output "documents_development_bucket_name" {
  description = "The name of the development documents bucket"
  value       = aws_s3_bucket.documents_development.id
}

output "deployment_artifacts_bucket_name" {
  description = "The name of the deployment artifacts bucket"
  value       = aws_s3_bucket.deployment_artifacts.id
}

output "terraform_state_bucket_name" {
  description = "The name of the Terraform state bucket"
  value       = aws_s3_bucket.terraform_state.id
}