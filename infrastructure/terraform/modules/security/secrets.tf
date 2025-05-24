# AWS Secrets Manager resources for the MCA Application Processing System
# This file manages secure credential storage for RabbitMQ, Redis, email services, and webhook signatures

# ---------------------------------------------------------------------------------------------------------------------
# RANDOM PASSWORD GENERATION
# ---------------------------------------------------------------------------------------------------------------------

# Generate a secure random password for RabbitMQ admin user
resource "random_password" "rabbitmq_admin" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Generate a secure random password for Redis
resource "random_password" "redis" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Generate a secure random password for email service
resource "random_password" "email_service" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Generate a secure HMAC key for webhook signatures
resource "random_password" "webhook_hmac" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS SECRETS MANAGER SECRETS
# ---------------------------------------------------------------------------------------------------------------------

# RabbitMQ credentials secret
resource "aws_secretsmanager_secret" "rabbitmq_credentials" {
  name                    = "mca/rabbitmq/credentials"
  description             = "RabbitMQ admin credentials for MCA Application Processing System"
  recovery_window_in_days = 7
  
  tags = {
    Name        = "mca-rabbitmq-credentials"
    Environment = var.environment
    Service     = "rabbitmq"
    Terraform   = "true"
  }
}

# Redis credentials secret
resource "aws_secretsmanager_secret" "redis_credentials" {
  name                    = "mca/redis/credentials"
  description             = "Redis credentials for MCA Application Processing System"
  recovery_window_in_days = 7
  
  tags = {
    Name        = "mca-redis-credentials"
    Environment = var.environment
    Service     = "redis"
    Terraform   = "true"
  }
}

# Email service credentials secret
resource "aws_secretsmanager_secret" "email_service_credentials" {
  name                    = "mca/email-service/credentials"
  description             = "Email service IMAPS credentials for MCA Application Processing System"
  recovery_window_in_days = 7
  
  tags = {
    Name        = "mca-email-service-credentials"
    Environment = var.environment
    Service     = "email-service"
    Terraform   = "true"
  }
}

# Webhook HMAC key secret
resource "aws_secretsmanager_secret" "webhook_hmac_key" {
  name                    = "mca/notification-service/webhook-hmac-key"
  description             = "HMAC key for webhook signature verification"
  recovery_window_in_days = 7
  
  tags = {
    Name        = "mca-webhook-hmac-key"
    Environment = var.environment
    Service     = "notification-service"
    Terraform   = "true"
  }
}

# Customer-specific webhook HMAC key secret
resource "aws_secretsmanager_secret" "customer_webhook_hmac_key" {
  for_each = var.customer_ids
  
  name                    = "mca/notification-service/customer-${each.key}-webhook-hmac-key"
  description             = "Customer-specific HMAC key for webhook signature verification"
  recovery_window_in_days = 7
  
  tags = {
    Name        = "mca-customer-${each.key}-webhook-hmac-key"
    Environment = var.environment
    Service     = "notification-service"
    CustomerId  = each.key
    Terraform   = "true"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS SECRETS MANAGER SECRET VERSIONS
# ---------------------------------------------------------------------------------------------------------------------

# RabbitMQ credentials secret version
resource "aws_secretsmanager_secret_version" "rabbitmq_credentials" {
  secret_id = aws_secretsmanager_secret.rabbitmq_credentials.id
  secret_string = jsonencode({
    username = "admin"
    password = random_password.rabbitmq_admin.result
    host     = var.rabbitmq_host
    port     = 5672
    vhost    = "/"
  })
}

# Redis credentials secret version
resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    username = "default"
    password = random_password.redis.result
    host     = var.redis_host
    port     = 6379
  })
}

# Email service credentials secret version
resource "aws_secretsmanager_secret_version" "email_service_credentials" {
  secret_id = aws_secretsmanager_secret.email_service_credentials.id
  secret_string = jsonencode({
    username      = "submissions@dollarfunding.com"
    password      = random_password.email_service.result
    host          = var.email_host
    port          = 993
    protocol      = "imaps"
    tls           = true
    tls_options   = {
      rejectUnauthorized = true
      minVersion        = "TLSv1.2"
    }
    auth_timeout  = 3000
    conn_timeout  = 10000
    poll_interval = 60000
  })
}

# Webhook HMAC key secret version
resource "aws_secretsmanager_secret_version" "webhook_hmac_key" {
  secret_id = aws_secretsmanager_secret.webhook_hmac_key.id
  secret_string = jsonencode({
    key       = random_password.webhook_hmac.result
    algorithm = "sha256"
  })
}

# Customer-specific webhook HMAC key secret versions
resource "aws_secretsmanager_secret_version" "customer_webhook_hmac_key" {
  for_each = var.customer_ids
  
  secret_id = aws_secretsmanager_secret.customer_webhook_hmac_key[each.key].id
  secret_string = jsonencode({
    key       = random_password.webhook_hmac.result
    algorithm = "sha256"
    customer_id = each.key
  })
}

# ---------------------------------------------------------------------------------------------------------------------
# VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "rabbitmq_host" {
  description = "RabbitMQ host address"
  type        = string
}

variable "redis_host" {
  description = "Redis host address"
  type        = string
}

variable "email_host" {
  description = "Email IMAPS host address"
  type        = string
}

variable "customer_ids" {
  description = "Map of customer IDs for customer-specific webhook HMAC keys"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "rabbitmq_credentials_secret_arn" {
  description = "ARN of the RabbitMQ credentials secret"
  value       = aws_secretsmanager_secret.rabbitmq_credentials.arn
}

output "redis_credentials_secret_arn" {
  description = "ARN of the Redis credentials secret"
  value       = aws_secretsmanager_secret.redis_credentials.arn
}

output "email_service_credentials_secret_arn" {
  description = "ARN of the email service credentials secret"
  value       = aws_secretsmanager_secret.email_service_credentials.arn
}

output "webhook_hmac_key_secret_arn" {
  description = "ARN of the webhook HMAC key secret"
  value       = aws_secretsmanager_secret.webhook_hmac_key.arn
}

output "customer_webhook_hmac_key_secret_arns" {
  description = "Map of customer IDs to ARNs of their webhook HMAC key secrets"
  value       = { for k, v in aws_secretsmanager_secret.customer_webhook_hmac_key : k => v.arn }
}