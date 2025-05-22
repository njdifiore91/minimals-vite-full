# PostgreSQL 14 Configuration for MCA Application Processing System
# This file defines the PostgreSQL resources in a primary-replica configuration
# with environment-specific settings (2 read replicas for production, 1 for staging)

# Local variables for database configuration
locals {
  # Environment-specific settings
  is_production = var.environment == "production"
  replica_count = local.is_production ? 2 : 1
  
  # Instance sizing based on environment
  instance_class = local.is_production ? "db.r6g.2xlarge" : "db.r6g.large"
  
  # Storage configuration
  allocated_storage     = local.is_production ? 500 : 200
  max_allocated_storage = local.is_production ? 1000 : 500
  
  # Backup retention period (days)
  backup_retention_period = local.is_production ? 30 : 7
  
  # Database name and credentials
  db_name  = "mca_application_db"
  db_port  = 5432
  
  # Connection pooling settings
  min_connections = 10
  max_connections = local.is_production ? 50 : 30
  
  # Availability zones for replica distribution
  azs = slice(data.aws_availability_zones.available.names, 0, local.replica_count + 1)
}

# Data source to get available availability zones
data "aws_availability_zones" "available" {}

# Primary PostgreSQL database instance
module "postgres_primary" {
  source = "../modules/database/main"
  
  # Basic configuration
  identifier        = "mca-postgres-${var.environment}"
  engine            = "postgres"
  engine_version    = "14.7"
  instance_class    = local.instance_class
  allocated_storage = local.allocated_storage
  max_allocated_storage = local.max_allocated_storage
  
  # Database settings
  db_name  = local.db_name
  port     = local.db_port
  username = var.db_master_username
  password = var.db_master_password
  
  # Network settings
  vpc_security_group_ids = [module.postgres_security.security_group_id]
  subnet_ids             = var.database_subnet_ids
  multi_az               = true
  availability_zone      = local.azs[0]
  
  # Performance settings
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  
  # Storage settings
  storage_type      = "gp3"
  iops              = 3000
  storage_encrypted = true
  kms_key_id        = module.postgres_security.kms_key_id
  
  # Maintenance settings
  maintenance_window = "Sun:00:00-Sun:03:00"
  backup_window      = "03:00-06:00"
  
  # Backup settings
  backup_retention_period = local.backup_retention_period
  delete_automated_backups = false
  skip_final_snapshot = false
  final_snapshot_identifier = "mca-postgres-${var.environment}-final-snapshot"
  
  # Parameter group settings
  parameter_group_name = aws_db_parameter_group.postgres_params.name
  
  # Connection pooling
  connection_pooling_enabled = true
  connection_pooling_min     = local.min_connections
  connection_pooling_max     = local.max_connections
  
  # Tags
  tags = merge(var.common_tags, {
    Name = "MCA PostgreSQL Primary - ${var.environment}"
    Role = "Primary Database"
  })
}

# Read replicas for PostgreSQL
module "postgres_replicas" {
  source = "../modules/database/replicas"
  
  # Number of replicas based on environment
  replica_count = local.replica_count
  
  # Primary database reference
  primary_db_instance_id = module.postgres_primary.db_instance_id
  
  # Basic configuration
  instance_class = local.is_production ? local.instance_class : "db.r6g.medium"
  
  # Replica distribution across AZs
  availability_zones = slice(local.azs, 1, length(local.azs))
  
  # Performance settings
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  
  # Storage settings
  storage_encrypted = true
  kms_key_id        = module.postgres_security.kms_key_id
  
  # Parameter group settings
  parameter_group_name = aws_db_parameter_group.postgres_params.name
  
  # Tags
  environment = var.environment
  common_tags = var.common_tags
}

# Security configuration for PostgreSQL
module "postgres_security" {
  source = "../modules/database/security"
  
  # Basic configuration
  name        = "mca-postgres-${var.environment}"
  environment = var.environment
  
  # Network settings
  vpc_id             = var.vpc_id
  allowed_cidr_blocks = var.allowed_cidr_blocks
  
  # Encryption settings
  enable_encryption = true
  key_rotation_period = 90 # days
  
  # Tags
  common_tags = var.common_tags
}

# Backup and recovery configuration
module "postgres_backup" {
  source = "../modules/database/backup"
  
  # Basic configuration
  name        = "mca-postgres-${var.environment}"
  environment = var.environment
  
  # Primary database reference
  db_instance_id = module.postgres_primary.db_instance_id
  
  # Backup settings
  backup_retention_period = local.backup_retention_period
  point_in_time_recovery  = true
  backup_window           = "03:00-06:00"
  
  # Long-term backup settings (7-year retention for compliance)
  enable_long_term_backup = true
  long_term_retention_period = 2555 # days (7 years)
  
  # Disaster recovery settings
  enable_cross_region_backup = local.is_production
  cross_region               = var.dr_region
  
  # Recovery point objective (RPO) and recovery time objective (RTO)
  rpo_minutes = 15
  rto_minutes = 30
  
  # Tags
  common_tags = var.common_tags
}

# Monitoring configuration for PostgreSQL
module "postgres_monitoring" {
  source = "../modules/database/monitoring"
  
  # Basic configuration
  name        = "mca-postgres-${var.environment}"
  environment = var.environment
  
  # Database references
  primary_db_instance_id = module.postgres_primary.db_instance_id
  replica_db_instance_ids = module.postgres_replicas.replica_instance_ids
  
  # Monitoring settings
  enhanced_monitoring_interval = 15 # seconds
  create_alarms                = true
  
  # Alarm thresholds
  cpu_utilization_threshold    = 80
  memory_utilization_threshold = 80
  storage_threshold_percent    = 85
  connection_threshold_percent = 80
  
  # Integration with monitoring systems
  enable_datadog_integration = var.enable_datadog
  datadog_api_key           = var.datadog_api_key
  
  # Tags
  common_tags = var.common_tags
}

# Parameter group for PostgreSQL configuration
resource "aws_db_parameter_group" "postgres_params" {
  name   = "mca-postgres-params-${var.environment}"
  family = "postgres14"
  
  # Connection settings
  parameter {
    name  = "max_connections"
    value = local.is_production ? "500" : "200"
  }
  
  # Memory settings
  parameter {
    name  = "shared_buffers"
    value = local.is_production ? "8GB" : "4GB"
  }
  
  parameter {
    name  = "work_mem"
    value = local.is_production ? "64MB" : "32MB"
  }
  
  # Query optimization
  parameter {
    name  = "effective_cache_size"
    value = local.is_production ? "24GB" : "12GB"
  }
  
  # Logging settings
  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # ms
  }
  
  parameter {
    name  = "log_statement"
    value = "ddl" # Log all DDL statements
  }
  
  # Partitioning settings
  parameter {
    name  = "max_locks_per_transaction"
    value = "128"
  }
  
  # Field-level encryption settings
  parameter {
    name  = "pgcrypto.enable"
    value = "1"
  }
  
  # Tags
  tags = merge(var.common_tags, {
    Name = "MCA PostgreSQL Parameters - ${var.environment}"
  })
}

# Option group for PostgreSQL extensions
resource "aws_db_option_group" "postgres_options" {
  name                 = "mca-postgres-options-${var.environment}"
  engine_name          = "postgres"
  major_engine_version = "14"
  
  # Enable pgcrypto extension for field-level encryption
  option {
    option_name = "PGCRYPTO"
  }
  
  # Enable pg_partman extension for table partitioning
  option {
    option_name = "PG_PARTMAN"
  }
  
  # Tags
  tags = merge(var.common_tags, {
    Name = "MCA PostgreSQL Options - ${var.environment}"
  })
}

# SQL script to create partitioned tables for large datasets
resource "null_resource" "create_partitioned_tables" {
  depends_on = [module.postgres_primary]
  
  # Only run this in production and staging environments
  count = var.environment == "development" ? 0 : 1
  
  provisioner "local-exec" {
    command = <<-EOT
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "CREATE EXTENSION IF NOT EXISTS pg_partman;"
      
      # Create partitioned applications table by created_at date
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "CREATE TABLE IF NOT EXISTS applications (
          id UUID PRIMARY KEY,
          status VARCHAR(50) NOT NULL,
          metadata JSONB,
          created_at TIMESTAMP NOT NULL,
          updated_at TIMESTAMP NOT NULL,
          review_status VARCHAR(50)
        ) PARTITION BY RANGE (created_at);"
      
      # Create partitioned documents table by uploaded_at date
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "CREATE TABLE IF NOT EXISTS documents (
          id UUID PRIMARY KEY,
          application_id UUID NOT NULL,
          type VARCHAR(100) NOT NULL,
          storage_path VARCHAR(255) NOT NULL,
          classification VARCHAR(100),
          uploaded_at TIMESTAMP NOT NULL,
          metadata JSONB,
          FOREIGN KEY (application_id) REFERENCES applications(id)
        ) PARTITION BY RANGE (uploaded_at);"
      
      # Create merchant_details table with encrypted PII fields
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "CREATE TABLE IF NOT EXISTS merchant_details (
          id UUID PRIMARY KEY,
          application_id UUID NOT NULL,
          legal_name VARCHAR(255) NOT NULL,
          dba_name VARCHAR(255),
          ein VARCHAR(255) NOT NULL,
          address JSONB NOT NULL,
          industry VARCHAR(100) NOT NULL,
          revenue NUMERIC(15,2),
          FOREIGN KEY (application_id) REFERENCES applications(id)
        );"
      
      # Create function for field-level encryption
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "CREATE OR REPLACE FUNCTION encrypt_pii(data TEXT, key TEXT) RETURNS TEXT AS $$
          BEGIN
            RETURN pgp_sym_encrypt(data, key);
          END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;"
      
      # Create function for field-level decryption
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "CREATE OR REPLACE FUNCTION decrypt_pii(data TEXT, key TEXT) RETURNS TEXT AS $$
          BEGIN
            RETURN pgp_sym_decrypt(data, key);
          END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;"
      
      # Set up partitioning for applications table
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "SELECT create_parent('public.applications', 'created_at', 'native', 'monthly');"
      
      # Set up partitioning for documents table
      PGPASSWORD=${var.db_master_password} psql \
        -h ${module.postgres_primary.db_instance_endpoint} \
        -U ${var.db_master_username} \
        -d ${local.db_name} \
        -c "SELECT create_parent('public.documents', 'uploaded_at', 'native', 'monthly');"
    EOT
  }
}

# Output the PostgreSQL connection information
output "postgres_primary_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL instance"
  value       = module.postgres_primary.db_instance_endpoint
}

output "postgres_replica_endpoints" {
  description = "The connection endpoints for the PostgreSQL read replicas"
  value       = module.postgres_replicas.replica_endpoints
}

output "postgres_connection_string" {
  description = "The connection string for the PostgreSQL database"
  value       = "postgresql://${var.db_master_username}:${var.db_master_password}@${module.postgres_primary.db_instance_endpoint}:${local.db_port}/${local.db_name}"
  sensitive   = true
}

output "postgres_read_connection_string" {
  description = "The connection string for the PostgreSQL read replicas"
  value       = [for endpoint in module.postgres_replicas.replica_endpoints : "postgresql://${var.db_master_username}:${var.db_master_password}@${endpoint}:${local.db_port}/${local.db_name}"]
  sensitive   = true
}