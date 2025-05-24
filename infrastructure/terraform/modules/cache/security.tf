# Redis Cache Security Configuration
# This file implements comprehensive security measures for Redis clusters including:
# - Network security groups
# - Encryption settings (transit and at-rest)
# - Authentication methods
# - Access control

# ---------------------------------------------------------------------------------------------------------------------
# Security Group for Redis Clusters
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_security_group" "redis" {
  name        = "${var.environment}-redis-security-group"
  description = "Security group for Redis clusters in ${var.environment} environment"
  vpc_id      = var.vpc_id

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-redis-security-group"
      Environment = var.environment
      Service     = "redis"
    }
  )

  # Prevent deletion of security group via terraform destroy unless force_destroy is set
  lifecycle {
    prevent_destroy = var.prevent_destroy
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Ingress Rules - Allow access only from application security groups
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_security_group_rule" "redis_ingress" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.redis.id
  source_security_group_id = var.app_security_group_id
  description              = "Allow Redis traffic from application servers"
}

# Allow access from data service security group
resource "aws_security_group_rule" "redis_ingress_data_service" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.redis.id
  source_security_group_id = var.data_service_security_group_id
  description              = "Allow Redis traffic from data service"
}

# Allow access from notification service security group
resource "aws_security_group_rule" "redis_ingress_notification_service" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.redis.id
  source_security_group_id = var.notification_service_security_group_id
  description              = "Allow Redis traffic from notification service"
}

# Allow access from OCR service security group
resource "aws_security_group_rule" "redis_ingress_ocr_service" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.redis.id
  source_security_group_id = var.ocr_service_security_group_id
  description              = "Allow Redis traffic from OCR service"
}

# Allow access from document service security group
resource "aws_security_group_rule" "redis_ingress_document_service" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.redis.id
  source_security_group_id = var.document_service_security_group_id
  description              = "Allow Redis traffic from document service"
}

# ---------------------------------------------------------------------------------------------------------------------
# Egress Rules - Allow all outbound traffic
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_security_group_rule" "redis_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.redis.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all outbound traffic"
}

# ---------------------------------------------------------------------------------------------------------------------
# Redis Auth Token (Password)
# ---------------------------------------------------------------------------------------------------------------------
resource "random_password" "redis_auth_token" {
  length           = 32
  special          = true
  override_special = "!&#$^<>-"
  min_lower        = 8
  min_upper        = 8
  min_numeric      = 8
  min_special      = 4
}

# Store Redis auth token in AWS Secrets Manager
resource "aws_secretsmanager_secret" "redis_auth_token" {
  name        = "${var.environment}/redis/auth-token"
  description = "Authentication token for Redis clusters in ${var.environment} environment"
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis"
    }
  )
}

resource "aws_secretsmanager_secret_version" "redis_auth_token" {
  secret_id     = aws_secretsmanager_secret.redis_auth_token.id
  secret_string = random_password.redis_auth_token.result
}

# ---------------------------------------------------------------------------------------------------------------------
# Redis Parameter Groups - Security Settings
# ---------------------------------------------------------------------------------------------------------------------
# Parameter group for Redis cache cluster
resource "aws_elasticache_parameter_group" "redis_cache_params" {
  name        = "${var.environment}-redis-cache-params"
  family      = "redis7"
  description = "Redis parameter group for cache cluster with security settings in ${var.environment} environment"

  # Security parameters
  parameter {
    name  = "notify-keyspace-events"
    value = ""  # Disable keyspace notifications for security
  }

  parameter {
    name  = "protected-mode"
    value = "yes"  # Enable protected mode
  }

  parameter {
    name  = "rename-commands"
    value = "FLUSHDB """ FLUSHALL """ CONFIG """ KEYS """"  # Disable dangerous commands
  }

  parameter {
    name  = "maxclients"
    value = "65000"  # Set maximum number of clients
  }

  parameter {
    name  = "timeout"
    value = "300"  # Connection timeout in seconds
  }
}

# Parameter group for Redis session cluster
resource "aws_elasticache_parameter_group" "redis_session_params" {
  name        = "${var.environment}-redis-session-params"
  family      = "redis7"
  description = "Redis parameter group for session cluster with security settings in ${var.environment} environment"

  # Security parameters
  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"  # Enable keyspace notifications for expiration events only (needed for sessions)
  }

  parameter {
    name  = "protected-mode"
    value = "yes"  # Enable protected mode
  }

  parameter {
    name  = "rename-commands"
    value = "FLUSHDB """ FLUSHALL """ CONFIG """ KEYS """"  # Disable dangerous commands
  }

  parameter {
    name  = "maxclients"
    value = "65000"  # Set maximum number of clients
  }

  parameter {
    name  = "timeout"
    value = "300"  # Connection timeout in seconds
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Redis ACL Configuration
# ---------------------------------------------------------------------------------------------------------------------
# Redis ACL for cache cluster
resource "aws_elasticache_user" "redis_cache_user" {
  user_id       = "${var.environment}-cache-user"
  user_name     = "cache-user"
  access_string = "on ~app:* ~cache:* +@read +@write +@hash +@list +@set +@sortedset +@string -@admin -@dangerous"
  engine        = "REDIS"
  passwords     = [random_password.redis_auth_token.result]
}

# Redis ACL for session cluster
resource "aws_elasticache_user" "redis_session_user" {
  user_id       = "${var.environment}-session-user"
  user_name     = "session-user"
  access_string = "on ~session:* +@read +@write +@string +@hash -@admin -@dangerous"
  engine        = "REDIS"
  passwords     = [random_password.redis_auth_token.result]
}

# Redis user group for cache cluster
resource "aws_elasticache_user_group" "redis_cache_user_group" {
  user_group_id = "${var.environment}-cache-user-group"
  engine        = "REDIS"
  user_ids      = [aws_elasticache_user.redis_cache_user.user_id]
}

# Redis user group for session cluster
resource "aws_elasticache_user_group" "redis_session_user_group" {
  user_group_id = "${var.environment}-session-user-group"
  engine        = "REDIS"
  user_ids      = [aws_elasticache_user.redis_session_user.user_id]
}

# ---------------------------------------------------------------------------------------------------------------------
# CloudWatch Logs for Security Monitoring
# ---------------------------------------------------------------------------------------------------------------------
# Log group for Redis cache cluster
resource "aws_cloudwatch_log_group" "redis_cache_logs" {
  name              = "/aws/elasticache/${var.environment}-redis-cache"
  retention_in_days = 30
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis-cache"
    }
  )
}

# Log group for Redis session cluster
resource "aws_cloudwatch_log_group" "redis_session_logs" {
  name              = "/aws/elasticache/${var.environment}-redis-session"
  retention_in_days = 30
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis-session"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# SNS Topics for Security Alerts
# ---------------------------------------------------------------------------------------------------------------------
# SNS topic for Redis cache cluster alarms
resource "aws_sns_topic" "redis_cache_alarms" {
  name = "${var.environment}-redis-cache-alarms"
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis-cache"
    }
  )
}

# SNS topic for Redis session cluster alarms
resource "aws_sns_topic" "redis_session_alarms" {
  name = "${var.environment}-redis-session-alarms"
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis-session"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# Security Alarms
# ---------------------------------------------------------------------------------------------------------------------
# Alarm for Redis cache cluster connection spikes (potential brute force)
resource "aws_cloudwatch_metric_alarm" "redis_cache_connection_spike" {
  alarm_name          = "${var.environment}-redis-cache-connection-spike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "NewConnections"
  namespace           = "AWS/ElastiCache"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1000"
  alarm_description   = "This alarm monitors for spikes in new connections to Redis cache cluster which may indicate a brute force attack"
  alarm_actions       = [aws_sns_topic.redis_cache_alarms.arn]
  ok_actions          = [aws_sns_topic.redis_cache_alarms.arn]
  
  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.cache.id
  }
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis-cache"
    }
  )
}

# Alarm for Redis session cluster connection spikes (potential brute force)
resource "aws_cloudwatch_metric_alarm" "redis_session_connection_spike" {
  alarm_name          = "${var.environment}-redis-session-connection-spike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "NewConnections"
  namespace           = "AWS/ElastiCache"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1000"
  alarm_description   = "This alarm monitors for spikes in new connections to Redis session cluster which may indicate a brute force attack"
  alarm_actions       = [aws_sns_topic.redis_session_alarms.arn]
  ok_actions          = [aws_sns_topic.redis_session_alarms.arn]
  
  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.sessions.id
  }
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis-session"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# KMS Key for Redis Encryption at Rest (Optional)
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_kms_key" "redis_encryption" {
  count                   = var.enable_encryption_at_rest ? 1 : 0
  description             = "KMS key for Redis encryption at rest in ${var.environment} environment"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      Service     = "redis"
    }
  )
}

resource "aws_kms_alias" "redis_encryption" {
  count         = var.enable_encryption_at_rest ? 1 : 0
  name          = "alias/${var.environment}-redis-encryption"
  target_key_id = aws_kms_key.redis_encryption[0].key_id
}

# ---------------------------------------------------------------------------------------------------------------------
# Network ACL for Redis Subnets
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_network_acl" "redis_acl" {
  vpc_id     = var.vpc_id
  subnet_ids = var.subnet_ids
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-redis-network-acl"
      Environment = var.environment
      Service     = "redis"
    }
  )
}

# Inbound rules
resource "aws_network_acl_rule" "redis_inbound" {
  network_acl_id = aws_network_acl.redis_acl.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 6379
  to_port        = 6379
}

# Allow return traffic
resource "aws_network_acl_rule" "redis_inbound_return" {
  network_acl_id = aws_network_acl.redis_acl.id
  rule_number    = 200
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 1024
  to_port        = 65535
}

# Outbound rules
resource "aws_network_acl_rule" "redis_outbound" {
  network_acl_id = aws_network_acl.redis_acl.id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 1024
  to_port        = 65535
}

# Allow Redis to initiate connections if needed
resource "aws_network_acl_rule" "redis_outbound_redis" {
  network_acl_id = aws_network_acl.redis_acl.id
  rule_number    = 200
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 6379
  to_port        = 6379
}

# ---------------------------------------------------------------------------------------------------------------------
# Variables used in this file
# ---------------------------------------------------------------------------------------------------------------------
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where Redis clusters will be deployed"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC where Redis clusters will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs where Redis clusters will be deployed"
  type        = list(string)
}

variable "app_security_group_id" {
  description = "Security group ID of the application servers"
  type        = string
}

variable "data_service_security_group_id" {
  description = "Security group ID of the data service"
  type        = string
}

variable "notification_service_security_group_id" {
  description = "Security group ID of the notification service"
  type        = string
}

variable "ocr_service_security_group_id" {
  description = "Security group ID of the OCR service"
  type        = string
}

variable "document_service_security_group_id" {
  description = "Security group ID of the document service"
  type        = string
}

variable "enable_encryption_at_rest" {
  description = "Whether to enable encryption at rest for Redis clusters"
  type        = bool
  default     = true
}

variable "prevent_destroy" {
  description = "Whether to prevent destruction of Redis security resources"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}