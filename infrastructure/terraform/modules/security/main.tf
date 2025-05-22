# Security Module - Main Configuration

terraform {
  required_version = ">= 1.12.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.0.0"
    }
  }
}

# Local variables for consistent resource naming and tagging
locals {
  # Common tags to be assigned to all resources
  common_tags = {
    Project     = "MCA-Application-Processing"
    ManagedBy   = "Terraform"
    Environment = var.environment
    CreatedBy   = "Security-Module"
    CreatedAt   = timestamp()
  }
  
  # Resource naming convention with environment-specific prefixes
  name_prefix = "mca-${var.environment}"
  
  # Environment-specific settings
  is_production = var.environment == "production"
  is_staging    = var.environment == "staging"
  is_development = var.environment == "development"
  
  # Security settings based on environment
  security_settings = {
    # JWT settings
    jwt_token_expiry = var.environment == "production" ? 60 : 120  # minutes
    jwt_refresh_expiry = var.environment == "production" ? 7 : 14  # days
    
    # S3 encryption settings
    s3_encryption_algorithm = "AES256"
    use_kms_encryption = var.environment == "production" ? true : false
    
    # TLS settings
    tls_version = "TLS1.3"
    
    # Rate limiting settings (requests per minute)
    rate_limit_authenticated = var.environment == "production" ? 60 : 120
    rate_limit_unauthenticated = var.environment == "production" ? 10 : 30
    
    # Key rotation settings
    kms_key_rotation_days = var.environment == "production" ? 90 : 180
    jwt_key_rotation_days = var.environment == "production" ? 90 : 180
  }
  
  # Service names for IAM role creation
  service_names = [
    "email-service",
    "document-service",
    "ocr-service",
    "data-service",
    "notification-service",
    "api-gateway"
  ]
}

# Module for generating JWT RSA keys
module "jwt_keys" {
  source = "../jwt-keys"
  
  key_name     = "${local.name_prefix}-jwt"
  environment  = var.environment
  rsa_bits     = 2048
  common_tags  = local.common_tags
}

# KMS key for data encryption (PII fields, etc.)
resource "aws_kms_key" "data_encryption_key" {
  description             = "${local.name_prefix}-data-encryption-key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_key_policy.json
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-data-encryption-key"
    },
    var.resource_tags
  )
}

# KMS key alias
resource "aws_kms_alias" "data_encryption_key_alias" {
  name          = "alias/${local.name_prefix}-data-encryption-key"
  target_key_id = aws_kms_key.data_encryption_key.key_id
}

# KMS key policy
data "aws_iam_policy_document" "kms_key_policy" {
  # Allow root account full access
  statement {
    sid       = "EnableIAMUserPermissions"
    effect    = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }
  
  # Allow key administrators to manage the key
  statement {
    sid       = "AllowAdminManagement"
    effect    = "Allow"
    principals {
      type        = "AWS"
      identifiers = length(var.kms_key_administrators) > 0 ? var.kms_key_administrators : [data.aws_caller_identity.current.arn]
    }
    actions   = [
      "kms:Create*",
      "kms:Describe*",
      "kms:Enable*",
      "kms:List*",
      "kms:Put*",
      "kms:Update*",
      "kms:Revoke*",
      "kms:Disable*",
      "kms:Get*",
      "kms:Delete*",
      "kms:TagResource",
      "kms:UntagResource",
      "kms:ScheduleKeyDeletion",
      "kms:CancelKeyDeletion"
    ]
    resources = ["*"]
  }
  
  # Allow services to use the key
  statement {
    sid       = "AllowServiceUse"
    effect    = "Allow"
    principals {
      type        = "AWS"
      identifiers = [for name in local.service_names : aws_iam_role.service_roles[name].arn]
    }
    actions   = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    resources = ["*"]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Security Groups

# API Gateway Security Group
resource "aws_security_group" "api_gateway" {
  name        = "${local.name_prefix}-api-gateway-sg"
  description = "Security group for API Gateway"
  vpc_id      = var.vpc_id
  
  # Allow HTTPS inbound from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS inbound"
  }
  
  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-api-gateway-sg"
    },
    var.resource_tags
  )
}

# Microservices Security Group
resource "aws_security_group" "microservices" {
  name        = "${local.name_prefix}-microservices-sg"
  description = "Security group for microservices"
  vpc_id      = var.vpc_id
  
  # Allow traffic from API Gateway
  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow all traffic from API Gateway"
  }
  
  # Allow traffic between microservices
  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    self            = true
    description     = "Allow all traffic between microservices"
  }
  
  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-microservices-sg"
    },
    var.resource_tags
  )
}

# Database Security Group
resource "aws_security_group" "database" {
  name        = "${local.name_prefix}-database-sg"
  description = "Security group for database access"
  vpc_id      = var.vpc_id
  
  # Allow PostgreSQL traffic from microservices
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.microservices.id]
    description     = "Allow PostgreSQL from microservices"
  }
  
  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-database-sg"
    },
    var.resource_tags
  )
}

# IAM Roles for Services
resource "aws_iam_role" "service_roles" {
  for_each = toset(local.service_names)
  
  name = "${local.name_prefix}-${each.value}-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-${each.value}-role"
      Service = each.value
    },
    var.resource_tags
  )
}

# WAF Web ACL for API protection
resource "aws_wafv2_web_acl" "api_protection" {
  count = var.enable_waf ? 1 : 0
  
  name        = "${local.name_prefix}-api-protection"
  description = "WAF Web ACL for API Gateway protection"
  scope       = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # AWS Managed Rules - Common Rule Set
  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 1
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-AWS-AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }
  
  # AWS Managed Rules - SQL Injection Rule Set
  rule {
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-AWS-AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }
  
  # Rate-based rule to prevent DDoS
  rule {
    name     = "RateLimitRule"
    priority = 3
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = local.is_production ? 1000 : 2000
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-RateLimitRule"
      sampled_requests_enabled   = true
    }
  }
  
  # IP whitelist rule for admin endpoints
  dynamic "rule" {
    for_each = length(var.ip_whitelist) > 0 ? [1] : []
    content {
      name     = "IPWhitelistRule"
      priority = 4
      
      action {
        allow {}
      }
      
      statement {
        and_statement {
          statement {
            byte_match_statement {
              field_to_match {
                uri_path {}
              }
              positional_constraint = "STARTS_WITH"
              search_string         = "/admin"
              text_transformation {
                priority = 0
                type     = "NONE"
              }
            }
          }
          
          statement {
            ip_set_reference_statement {
              arn = aws_wafv2_ip_set.admin_whitelist[0].arn
            }
          }
        }
      }
      
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.name_prefix}-IPWhitelistRule"
        sampled_requests_enabled   = true
      }
    }
  }
  
  # Block admin access if not in IP whitelist
  dynamic "rule" {
    for_each = length(var.ip_whitelist) > 0 ? [1] : []
    content {
      name     = "BlockAdminAccessRule"
      priority = 5
      
      action {
        block {}
      }
      
      statement {
        byte_match_statement {
          field_to_match {
            uri_path {}
          }
          positional_constraint = "STARTS_WITH"
          search_string         = "/admin"
          text_transformation {
            priority = 0
            type     = "NONE"
          }
        }
      }
      
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.name_prefix}-BlockAdminAccessRule"
        sampled_requests_enabled   = true
      }
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-api-protection"
    sampled_requests_enabled   = true
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-api-protection"
    },
    var.resource_tags
  )
}

# IP Set for admin whitelist
resource "aws_wafv2_ip_set" "admin_whitelist" {
  count = length(var.ip_whitelist) > 0 ? 1 : 0
  
  name               = "${local.name_prefix}-admin-whitelist"
  description        = "IP whitelist for admin access"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.ip_whitelist
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-admin-whitelist"
    },
    var.resource_tags
  )
}