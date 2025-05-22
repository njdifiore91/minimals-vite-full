# Main Terraform configuration for PostgreSQL database infrastructure
# This file serves as the entry point for the database module configuration

# Terraform version and provider constraints
terraform {
  required_version = ">= 1.0.0"

  # Backend configuration for state management
  backend "s3" {
    bucket         = "mca-terraform-state"
    key            = "database/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
}

# Provider configuration
provider "aws" {
  region = local.region

  default_tags {
    tags = {
      Project     = "MCA Application Processing System"
      Environment = var.environment
      Terraform   = "true"
    }
  }
}

# Local variables for database configuration
locals {
  region = var.region
  
  # Environment-specific configurations
  is_production = var.environment == "production"
  replica_count = local.is_production ? 2 : 1
  
  # Database configuration
  db_name     = "mca_${var.environment}"
  db_username = "mca_admin"
  
  # Common tags
  common_tags = {
    Project     = "MCA Application Processing System"
    Environment = var.environment
    Terraform   = "true"
    Service     = "Database"
  }
}

# Data sources for environment-specific configurations
data "aws_availability_zones" "available" {}

# Import PostgreSQL database module
module "postgresql" {
  source = "../../modules/database"

  # General settings
  environment         = var.environment
  db_name             = local.db_name
  db_username         = local.db_username
  db_password         = var.db_password
  db_port             = 5432
  engine_version      = "14"
  instance_class      = var.db_instance_class
  storage_type        = "gp2"
  allocated_storage   = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  multi_az            = true
  publicly_accessible = false

  # Read replica configuration
  replica_count       = local.replica_count
  replica_instance_class = var.db_replica_instance_class

  # Backup and maintenance configuration
  backup_retention_period = 30
  backup_window          = "03:00-06:00"
  maintenance_window     = "Mon:00:00-Mon:03:00"
  skip_final_snapshot    = false
  final_snapshot_identifier = "${local.db_name}-final-snapshot"

  # Security configuration
  storage_encrypted     = true
  kms_key_id            = var.kms_key_id
  vpc_security_group_ids = var.vpc_security_group_ids
  subnet_ids            = var.subnet_ids

  # Monitoring configuration
  monitoring_interval             = 15
  monitoring_role_arn             = var.monitoring_role_arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true

  # Performance configuration
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  # Connection pooling configuration
  parameter_group_name = var.parameter_group_name
  parameter_group_parameters = [
    {
      name  = "max_connections"
      value = "200"
    },
    {
      name  = "shared_buffers"
      value = "{DBInstanceClassMemory/32768}MB"
    }
  ]

  # Tags
  tags = local.common_tags
}

# Output the database endpoints and connection information
output "primary_endpoint" {
  description = "The endpoint of the primary database"
  value       = module.postgresql.primary_endpoint
}

output "replica_endpoints" {
  description = "The endpoints of the read replica databases"
  value       = module.postgresql.replica_endpoints
}

output "connection_string" {
  description = "PostgreSQL connection string for the primary database"
  value       = "postgresql://${local.db_username}:${var.db_password}@${module.postgresql.primary_endpoint}:5432/${local.db_name}"
  sensitive   = true
}

output "read_connection_string" {
  description = "PostgreSQL connection string for read replicas"
  value       = [for endpoint in module.postgresql.replica_endpoints : "postgresql://${local.db_username}:${var.db_password}@${endpoint}:5432/${local.db_name}"]
  sensitive   = true
}