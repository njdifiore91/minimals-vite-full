# Redis Cache Security Configuration
# This file implements comprehensive security measures for the Redis cluster, including:
# - Network security groups with restricted access
# - TLS for transit encryption
# - Encryption at rest
# - Authentication with password and access control lists
# - Network isolation and VPC settings

# Security group for Redis cluster
resource "aws_security_group" "redis" {
  name        = "${var.name_prefix}-redis-sg"
  description = "Security group for Redis cluster with restricted access"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis-sg"
    }
  )

  # Use create_before_destroy to minimize downtime during changes
  lifecycle {
    create_before_destroy = true
  }
}

# Ingress rule - Allow access only from specified security groups
resource "aws_security_group_rule" "redis_ingress" {
  count = length(var.allowed_security_group_ids)

  type                     = "ingress"
  from_port                = var.redis_port
  to_port                  = var.redis_port
  protocol                 = "tcp"
  source_security_group_id = var.allowed_security_group_ids[count.index]
  security_group_id        = aws_security_group.redis.id
  description              = "Allow inbound traffic from authorized services"
}

# Ingress rule - Allow access from CIDR blocks if specified
resource "aws_security_group_rule" "redis_ingress_cidr" {
  count = length(var.allowed_cidr_blocks) > 0 ? 1 : 0

  type              = "ingress"
  from_port         = var.redis_port
  to_port           = var.redis_port
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  security_group_id = aws_security_group.redis.id
  description       = "Allow inbound traffic from authorized CIDR blocks"
}

# Egress rule - Allow all outbound traffic
resource "aws_security_group_rule" "redis_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.redis.id
  description       = "Allow all outbound traffic"
}

# Redis Auth Token (Password) for authentication
resource "random_password" "redis_auth_token" {
  count = var.create_random_auth_token ? 1 : 0

  length           = 32
  special          = true
  override_special = "!&#$^<>-"
  min_lower        = 8
  min_upper        = 8
  min_numeric      = 8
  min_special      = 4
}

# Redis Auth Token (Password) for authentication
resource "random_password" "redis_auth_token" {
  count = var.create_random_auth_token ? 1 : 0

  length           = 32
  special          = true
  override_special = "!&#$^<>-"
  min_lower        = 8
  min_upper        = 8
  min_numeric      = 8
  min_special      = 4
}

# Redis User for ACL-based access control
resource "aws_elasticache_user" "redis_admin_user" {
  count = var.enable_user_group_access ? 1 : 0

  user_id       = "${var.name_prefix}-admin-user"
  user_name     = "admin"
  access_string = "on ~* +@all"
  engine        = "REDIS"
  passwords     = var.create_random_auth_token ? [random_password.redis_auth_token[0].result] : var.auth_token_list
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-admin-user"
    }
  )
}

# Redis User for read-only access
resource "aws_elasticache_user" "redis_readonly_user" {
  count = var.enable_user_group_access && var.create_readonly_user ? 1 : 0

  user_id       = "${var.name_prefix}-readonly-user"
  user_name     = "readonly"
  access_string = "on ~* -@all +@read"
  engine        = "REDIS"
  passwords     = var.create_random_auth_token ? [random_password.redis_auth_token[0].result] : var.auth_token_list
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-readonly-user"
    }
  )
}

# Redis User for ACL-based access control
resource "aws_elasticache_user" "redis_admin_user" {
  count = var.enable_user_group_access ? 1 : 0

  user_id       = "${var.name_prefix}-admin-user"
  user_name     = "admin"
  access_string = "on ~* +@all"
  engine        = "REDIS"
  passwords     = var.create_random_auth_token ? [random_password.redis_auth_token[0].result] : var.auth_token_list
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-admin-user"
    }
  )
}

# Redis User for read-only access
resource "aws_elasticache_user" "redis_readonly_user" {
  count = var.enable_user_group_access && var.create_readonly_user ? 1 : 0

  user_id       = "${var.name_prefix}-readonly-user"
  user_name     = "readonly"
  access_string = "on ~* -@all +@read"
  engine        = "REDIS"
  passwords     = var.create_random_auth_token ? [random_password.redis_auth_token[0].result] : var.auth_token_list
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-readonly-user"
    }
  )
}

# Redis User Group for managing users
resource "aws_elasticache_user_group" "redis_user_group" {
  count = var.enable_user_group_access ? 1 : 0

  user_group_id = "${var.name_prefix}-user-group"
  engine        = "REDIS"
  user_ids      = compact(
    concat(
      var.create_readonly_user ? [aws_elasticache_user.redis_readonly_user[0].user_id] : [],
      [aws_elasticache_user.redis_admin_user[0].user_id]
    )
  )
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-user-group"
    }
  )
}

# Redis User Group for managing users
resource "aws_elasticache_user_group" "redis_user_group" {
  count = var.enable_user_group_access ? 1 : 0

  user_group_id = "${var.name_prefix}-user-group"
  engine        = "REDIS"
  user_ids      = compact(
    concat(
      var.create_readonly_user ? [aws_elasticache_user.redis_readonly_user[0].user_id] : [],
      [aws_elasticache_user.redis_admin_user[0].user_id]
    )
  )
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-user-group"
    }
  )
}

# KMS Key for encryption at rest (if enabled)
resource "aws_kms_key" "redis_encryption_key" {
  count = var.encryption_at_rest_kms_key_id == "" && var.at_rest_encryption_enabled ? 1 : 0

  description             = "KMS key for Redis encryption at rest"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis-encryption-key"
    }
  )
}

# KMS Key Alias
resource "aws_kms_alias" "redis_encryption_key_alias" {
  count = var.encryption_at_rest_kms_key_id == "" && var.at_rest_encryption_enabled ? 1 : 0

  name          = "alias/${var.name_prefix}-redis-encryption-key"
  target_key_id = aws_kms_key.redis_encryption_key[0].key_id
}

# KMS Key for encryption at rest (if enabled)
resource "aws_kms_key" "redis_encryption_key" {
  count = var.encryption_at_rest_kms_key_id == "" && var.at_rest_encryption_enabled ? 1 : 0

  description             = "KMS key for Redis encryption at rest"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis-encryption-key"
    }
  )
}

# KMS Key Alias
resource "aws_kms_alias" "redis_encryption_key_alias" {
  count = var.encryption_at_rest_kms_key_id == "" && var.at_rest_encryption_enabled ? 1 : 0

  name          = "alias/${var.name_prefix}-redis-encryption-key"
  target_key_id = aws_kms_key.redis_encryption_key[0].key_id
}

# Security configuration for Redis parameter group
resource "aws_elasticache_parameter_group" "redis_security_parameters" {
  count = var.create_security_parameter_group ? 1 : 0

  name        = "${var.name_prefix}-redis-security-params"
  family      = "redis7"
  description = "Redis security parameter group with enhanced security settings"

  # TLS-related parameters
  parameter {
    name  = "tls-enabled"
    value = "yes"
  }

  # Disable commands that could be harmful in production
  parameter {
    name  = "rename-commands"
    value = "FLUSHDB FLUSHALL"
  }

  # Set client output buffer limits to prevent memory issues
  parameter {
    name  = "client-output-buffer-limit-normal-hard-limit"
    value = "${var.client_output_buffer_limit_normal_hard}"
  }

  parameter {
    name  = "client-output-buffer-limit-normal-soft-limit"
    value = "${var.client_output_buffer_limit_normal_soft}"
  }

  parameter {
    name  = "client-output-buffer-limit-normal-soft-seconds"
    value = "${var.client_output_buffer_limit_normal_soft_seconds}"
  }

  # Set maximum memory policy
  parameter {
    name  = "maxmemory-policy"
    value = var.is_session_cache ? "noeviction" : "allkeys-lru"
  }
}

# Security configuration for Redis parameter group
resource "aws_elasticache_parameter_group" "redis_security_parameters" {
  count = var.create_security_parameter_group ? 1 : 0

  name        = "${var.name_prefix}-redis-security-params"
  family      = "redis7"
  description = "Redis security parameter group with enhanced security settings"

  # TLS-related parameters
  parameter {
    name  = "tls-enabled"
    value = "yes"
  }

  # Disable commands that could be harmful in production
  parameter {
    name  = "rename-commands"
    value = "FLUSHDB FLUSHALL"
  }

  # Set client output buffer limits to prevent memory issues
  parameter {
    name  = "client-output-buffer-limit-normal-hard-limit"
    value = "${var.client_output_buffer_limit_normal_hard}"
  }

  parameter {
    name  = "client-output-buffer-limit-normal-soft-limit"
    value = "${var.client_output_buffer_limit_normal_soft}"
  }

  parameter {
    name  = "client-output-buffer-limit-normal-soft-seconds"
    value = "${var.client_output_buffer_limit_normal_soft_seconds}"
  }

  # Set maximum memory policy
  parameter {
    name  = "maxmemory-policy"
    value = var.is_session_cache ? "noeviction" : "allkeys-lru"
  }
}

# Security configuration for Redis subnet group
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  count = var.create_subnet_group ? 1 : 0

  name        = "${var.name_prefix}-redis-subnet-group"
  description = "Redis subnet group for network isolation"
  subnet_ids  = var.subnet_ids
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis-subnet-group"
    }
  )
}

# Security configuration for Redis subnet group
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  count = var.create_subnet_group ? 1 : 0

  name        = "${var.name_prefix}-redis-subnet-group"
  description = "Redis subnet group for network isolation"
  subnet_ids  = var.subnet_ids
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis-subnet-group"
    }
  )
}