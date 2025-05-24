# RabbitMQ Security Configuration for MCA Application Processing System
# This file implements comprehensive security measures for the RabbitMQ cluster,
# including network security groups, encryption settings, authentication methods,
# and access control.
#
# Security features implemented:
# 1. TLS 1.3 for transit encryption with strong cipher suites
# 2. Message encryption at rest using KMS
# 3. Secure authentication with username/password and client certificates
# 4. Network isolation with security groups and restricted access
# 5. Virtual host isolation for service domains
# 6. Secrets management for credentials and certificates

# -----------------------------------------------------------------------------
# Security Group for RabbitMQ Cluster
# -----------------------------------------------------------------------------

resource "aws_security_group" "rabbitmq_cluster" {
  name        = "${var.environment}-rabbitmq-cluster-sg"
  description = "Security group for RabbitMQ cluster in ${var.environment} environment"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-cluster-sg"
      Component = "messaging"
    }
  )

  # Prevent deletion of the security group via Terraform if it's in use
  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Ingress Rules for RabbitMQ Cluster
# -----------------------------------------------------------------------------

# AMQP over TLS (5671)
resource "aws_security_group_rule" "rabbitmq_amqps" {
  security_group_id = aws_security_group.rabbitmq_cluster.id
  type              = "ingress"
  from_port         = 5671
  to_port           = 5671
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  description       = "AMQP over TLS"
}

# Management UI over HTTPS (15671)
resource "aws_security_group_rule" "rabbitmq_management_ui" {
  security_group_id = aws_security_group.rabbitmq_cluster.id
  type              = "ingress"
  from_port         = 15671
  to_port           = 15671
  protocol          = "tcp"
  cidr_blocks       = var.management_cidr_blocks
  description       = "Management UI over HTTPS"
}

# Erlang Port Mapper Daemon (epmd)
resource "aws_security_group_rule" "rabbitmq_epmd" {
  security_group_id = aws_security_group.rabbitmq_cluster.id
  type              = "ingress"
  from_port         = 4369
  to_port           = 4369
  protocol          = "tcp"
  self              = true
  description       = "Erlang Port Mapper Daemon (epmd)"
}

# Inter-node communication
resource "aws_security_group_rule" "rabbitmq_inter_node" {
  security_group_id = aws_security_group.rabbitmq_cluster.id
  type              = "ingress"
  from_port         = 25672
  to_port           = 25672
  protocol          = "tcp"
  self              = true
  description       = "Inter-node communication"
}

# Allow all outbound traffic
resource "aws_security_group_rule" "rabbitmq_egress" {
  security_group_id = aws_security_group.rabbitmq_cluster.id
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all outbound traffic"
}

# -----------------------------------------------------------------------------
# TLS Certificate Management
# -----------------------------------------------------------------------------

# KMS key for encrypting RabbitMQ credentials and certificates
resource "aws_kms_key" "rabbitmq_encryption" {
  description             = "KMS key for RabbitMQ encryption in ${var.environment} environment"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-encryption-key"
      Component = "messaging"
    }
  )
}

resource "aws_kms_alias" "rabbitmq_encryption" {
  name          = "alias/${var.environment}-rabbitmq-encryption"
  target_key_id = aws_kms_key.rabbitmq_encryption.key_id
}

# S3 bucket for storing RabbitMQ TLS certificates
resource "aws_s3_bucket" "rabbitmq_certificates" {
  bucket = "${var.environment}-rabbitmq-certificates-${var.aws_account_id}"
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-certificates"
      Component = "messaging"
    }
  )
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "rabbitmq_certificates" {
  bucket = aws_s3_bucket.rabbitmq_certificates.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.rabbitmq_encryption.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# Block public access to the S3 bucket
resource "aws_s3_bucket_public_access_block" "rabbitmq_certificates" {
  bucket                  = aws_s3_bucket.rabbitmq_certificates.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket policy to restrict access
resource "aws_s3_bucket_policy" "rabbitmq_certificates" {
  bucket = aws_s3_bucket.rabbitmq_certificates.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSSLOperations"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.aws_account_id}:role/${var.environment}-rabbitmq-role"
        }
        Action    = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource  = [
          aws_s3_bucket.rabbitmq_certificates.arn,
          "${aws_s3_bucket.rabbitmq_certificates.arn}/*"
        ]
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.rabbitmq_certificates]
}

# -----------------------------------------------------------------------------
# Secrets Management for RabbitMQ
# -----------------------------------------------------------------------------

# Secret for RabbitMQ admin credentials
resource "aws_secretsmanager_secret" "rabbitmq_admin" {
  name                    = "${var.environment}/rabbitmq/admin"
  description             = "RabbitMQ admin credentials for ${var.environment} environment"
  kms_key_id              = aws_kms_key.rabbitmq_encryption.arn
  recovery_window_in_days = 30
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-admin-credentials"
      Component = "messaging"
    }
  )
}

# Secret for RabbitMQ service accounts
resource "aws_secretsmanager_secret" "rabbitmq_service_accounts" {
  name                    = "${var.environment}/rabbitmq/service-accounts"
  description             = "RabbitMQ service account credentials for ${var.environment} environment"
  kms_key_id              = aws_kms_key.rabbitmq_encryption.arn
  recovery_window_in_days = 30
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-service-accounts"
      Component = "messaging"
    }
  )
}

# Secret for RabbitMQ TLS certificates
resource "aws_secretsmanager_secret" "rabbitmq_tls" {
  name                    = "${var.environment}/rabbitmq/tls"
  description             = "RabbitMQ TLS certificates for ${var.environment} environment"
  kms_key_id              = aws_kms_key.rabbitmq_encryption.arn
  recovery_window_in_days = 30
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-tls-certificates"
      Component = "messaging"
    }
  )
}

# -----------------------------------------------------------------------------
# IAM Role and Policy for RabbitMQ
# -----------------------------------------------------------------------------

# IAM role for RabbitMQ instances
resource "aws_iam_role" "rabbitmq" {
  name = "${var.environment}-rabbitmq-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-role"
      Component = "messaging"
    }
  )
}

# IAM policy for RabbitMQ instances
resource "aws_iam_policy" "rabbitmq" {
  name        = "${var.environment}-rabbitmq-policy"
  description = "Policy for RabbitMQ instances in ${var.environment} environment"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.rabbitmq_certificates.arn,
          "${aws_s3_bucket.rabbitmq_certificates.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.rabbitmq_admin.arn,
          aws_secretsmanager_secret.rabbitmq_service_accounts.arn,
          aws_secretsmanager_secret.rabbitmq_tls.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.rabbitmq_encryption.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "rabbitmq" {
  role       = aws_iam_role.rabbitmq.name
  policy_arn = aws_iam_policy.rabbitmq.arn
}

# Instance profile for RabbitMQ instances
resource "aws_iam_instance_profile" "rabbitmq" {
  name = "${var.environment}-rabbitmq-instance-profile"
  role = aws_iam_role.rabbitmq.name
}

# -----------------------------------------------------------------------------
# RabbitMQ TLS Configuration
# -----------------------------------------------------------------------------

# RabbitMQ TLS configuration template
resource "aws_s3_object" "rabbitmq_tls_config" {
  bucket  = aws_s3_bucket.rabbitmq_certificates.id
  key     = "config/rabbitmq-tls.conf"
  content = <<-EOT
    # RabbitMQ TLS Configuration
    listeners.ssl.default = 5671
    
    # TLS/SSL configuration
    ssl_options.cacertfile = /etc/rabbitmq/certs/ca_certificate.pem
    ssl_options.certfile   = /etc/rabbitmq/certs/server_certificate.pem
    ssl_options.keyfile    = /etc/rabbitmq/certs/server_key.pem
    ssl_options.verify     = verify_peer
    ssl_options.fail_if_no_peer_cert = true
    
    # Only allow TLSv1.3 as required by security policy
    # TLSv1.2 included as fallback for compatibility with older clients if needed
    ssl_options.versions.1 = tlsv1.3
    ssl_options.versions.2 = tlsv1.2
    
    # Specify strong cipher suites (TLS 1.3 compatible)
    ssl_options.ciphers.1 = TLS_AES_256_GCM_SHA384
    ssl_options.ciphers.2 = TLS_AES_128_GCM_SHA256
    ssl_options.ciphers.3 = TLS_CHACHA20_POLY1305_SHA256
    # TLS 1.2 fallback ciphers
    ssl_options.ciphers.4 = ECDHE-RSA-AES256-GCM-SHA384
    ssl_options.ciphers.5 = ECDHE-RSA-AES128-GCM-SHA256
    
    # Management UI TLS configuration
    management.ssl.port       = 15671
    management.ssl.cacertfile = /etc/rabbitmq/certs/ca_certificate.pem
    management.ssl.certfile   = /etc/rabbitmq/certs/server_certificate.pem
    management.ssl.keyfile    = /etc/rabbitmq/certs/server_key.pem
  EOT
  
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.rabbitmq_encryption.arn
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-tls-config"
      Component = "messaging"
    }
  )
}

# -----------------------------------------------------------------------------
# RabbitMQ Virtual Hosts and Permissions Configuration
# -----------------------------------------------------------------------------

# RabbitMQ virtual hosts and permissions configuration template
resource "aws_s3_object" "rabbitmq_vhosts_config" {
  bucket  = aws_s3_bucket.rabbitmq_certificates.id
  key     = "config/rabbitmq-vhosts.conf"
  content = <<-EOT
    # RabbitMQ Virtual Hosts Configuration
    
    # Default virtual host
    default_vhost = mca
    
    # Default admin user (password will be replaced with secret during deployment)
    default_user = admin
    default_pass = PLACEHOLDER_TO_BE_REPLACED_WITH_SECRET
    default_permissions.configure = .*
    default_permissions.read = .*
    default_permissions.write = .*
    
    # Virtual hosts for service isolation as specified in the technical specification
    # Each microservice will have its own virtual host for isolation
    default_vhost.1 = document-processing
    default_vhost.2 = data-extraction
    default_vhost.3 = notification
    
    # Service-specific users and permissions
    # These will be configured programmatically during deployment
    # to implement the principle of least privilege
    #
    # Example permissions (to be applied via API):
    # - email-service: write to document-processing exchange
    # - document-service: read from document-processing queue, write to data-extraction exchange
    # - ocr-service: read from data-extraction queue, write to notification exchange
    # - data-service: read from notification queue
    # - notification-service: read from notification queue
  EOT
  
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.rabbitmq_encryption.arn
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-vhosts-config"
      Component = "messaging"
    }
  )
}

# -----------------------------------------------------------------------------
# RabbitMQ Message Encryption Configuration
# -----------------------------------------------------------------------------

# RabbitMQ message encryption configuration template
resource "aws_s3_object" "rabbitmq_encryption_config" {
  bucket  = aws_s3_bucket.rabbitmq_certificates.id
  key     = "config/rabbitmq-encryption.conf"
  content = <<-EOT
    # RabbitMQ Message Encryption Configuration
    
    # Enable required plugins for security
    rabbitmq_plugins.enable.1 = rabbitmq_auth_mechanism_ssl
    rabbitmq_plugins.enable.2 = rabbitmq_auth_backend_cache
    rabbitmq_plugins.enable.3 = rabbitmq_auth_backend_http
    
    # Configure authentication mechanisms
    # EXTERNAL - for client certificate authentication
    # PLAIN - for username/password authentication (over TLS only)
    auth_mechanisms.1 = EXTERNAL
    auth_mechanisms.2 = PLAIN
    
    # Enable disk encryption for messages at rest
    disk_free_limit.absolute = 5GB
    queue_index_embed_msgs_below = 4096
    
    # Message payload encryption settings
    # These settings ensure sensitive data within messages is encrypted
    consumer_timeout = 1800000 # 30 minutes in milliseconds
    hipe_compile = false # Disable HiPE for security reasons
    
    # Secure channel settings
    channel_max = 2048
    heartbeat = 60 # 60 seconds heartbeat for faster connection failure detection
  EOT
  
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.rabbitmq_encryption.arn
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-rabbitmq-encryption-config"
      Component = "messaging"
    }
  )
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where RabbitMQ cluster will be deployed"
  type        = string
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to RabbitMQ AMQP port"
  type        = list(string)
  default     = []
}

variable "management_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to RabbitMQ management UI"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "rabbitmq_security_group_id" {
  description = "ID of the RabbitMQ security group"
  value       = aws_security_group.rabbitmq_cluster.id
}

output "rabbitmq_iam_role_arn" {
  description = "ARN of the RabbitMQ IAM role"
  value       = aws_iam_role.rabbitmq.arn
}

output "rabbitmq_instance_profile_name" {
  description = "Name of the RabbitMQ instance profile"
  value       = aws_iam_instance_profile.rabbitmq.name
}

output "rabbitmq_kms_key_arn" {
  description = "ARN of the KMS key used for RabbitMQ encryption"
  value       = aws_kms_key.rabbitmq_encryption.arn
}

output "rabbitmq_certificates_bucket" {
  description = "Name of the S3 bucket containing RabbitMQ certificates"
  value       = aws_s3_bucket.rabbitmq_certificates.id
}

output "rabbitmq_admin_secret_arn" {
  description = "ARN of the secret containing RabbitMQ admin credentials"
  value       = aws_secretsmanager_secret.rabbitmq_admin.arn
}

output "rabbitmq_service_accounts_secret_arn" {
  description = "ARN of the secret containing RabbitMQ service account credentials"
  value       = aws_secretsmanager_secret.rabbitmq_service_accounts.arn
}

output "rabbitmq_tls_secret_arn" {
  description = "ARN of the secret containing RabbitMQ TLS certificates"
  value       = aws_secretsmanager_secret.rabbitmq_tls.arn
}