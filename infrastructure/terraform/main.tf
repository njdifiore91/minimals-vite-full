# =============================================================================
# MCA Application Processing System - Main Terraform Configuration
# =============================================================================
# This file serves as the entry point for Terraform operations and orchestrates
# the deployment of various infrastructure components for the MCA Application
# Processing System.
# =============================================================================

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.0"
    }
  }
  
  # Backend configuration for remote state storage
  # This will be configured per environment
  backend "s3" {}
}

# Provider configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = local.common_tags
  }
}

provider "kubernetes" {
  host                   = module.kubernetes.cluster_endpoint
  cluster_ca_certificate = module.kubernetes.cluster_ca_certificate
  token                  = module.kubernetes.cluster_token
}

provider "helm" {
  kubernetes {
    host                   = module.kubernetes.cluster_endpoint
    cluster_ca_certificate = module.kubernetes.cluster_ca_certificate
    token                  = module.kubernetes.cluster_token
  }
}

# Local variables
locals {
  environment = var.environment
  
  # Common tags for all resources
  common_tags = {
    Environment     = var.environment
    Project         = "MCA-Application-System"
    ManagedBy       = "Terraform"
    CostCenter      = var.cost_center
    ApplicationName = "DollarFunding-MCA"
  }
}

# =============================================================================
# Database Module - PostgreSQL 14
# =============================================================================
module "database" {
  source = "./modules/database"
  
  environment         = local.environment
  vpc_id              = module.network.vpc_id
  subnet_ids          = module.network.private_subnet_ids
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  db_name             = "mca_${local.environment}"
  db_username         = var.db_username
  db_password         = var.db_password
  multi_az            = var.db_multi_az
  backup_retention    = var.db_backup_retention
  read_replica_count  = var.db_read_replica_count
  tags                = local.common_tags
  
  depends_on = [module.network]
}

# =============================================================================
# Messaging Module - RabbitMQ
# =============================================================================
module "messaging" {
  source = "./modules/messaging"
  
  environment       = local.environment
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.private_subnet_ids
  instance_type     = var.mq_instance_type
  cluster_size      = var.mq_cluster_size
  username          = var.mq_username
  password          = var.mq_password
  tags              = local.common_tags
  
  depends_on = [module.network]
}

# =============================================================================
# Cache Module - Redis 7.0
# =============================================================================
module "cache" {
  source = "./modules/cache"
  
  environment       = local.environment
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.private_subnet_ids
  node_type         = var.redis_node_type
  num_cache_nodes   = var.redis_num_cache_nodes
  parameter_group   = "default.redis7"
  engine_version    = "7.0"
  tags              = local.common_tags
  
  depends_on = [module.network]
}

# =============================================================================
# Storage Module - S3 Compatible Storage
# =============================================================================
module "storage" {
  source = "./modules/storage"
  
  environment       = local.environment
  bucket_name       = "mca-documents-${local.environment}"
  versioning        = true
  encryption        = true
  lifecycle_rules   = var.s3_lifecycle_rules
  tags              = local.common_tags
}

# =============================================================================
# Network Module - VPC, Subnets, Security Groups
# =============================================================================
module "network" {
  source = "./modules/network"
  
  environment       = local.environment
  vpc_cidr          = var.vpc_cidr
  availability_zones = var.availability_zones
  tags              = local.common_tags
}

# =============================================================================
# Kubernetes Module - EKS Cluster
# =============================================================================
module "kubernetes" {
  source = "./modules/kubernetes"
  
  environment       = local.environment
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.private_subnet_ids
  cluster_name      = "mca-${local.environment}"
  cluster_version   = var.k8s_cluster_version
  node_groups       = var.k8s_node_groups
  tags              = local.common_tags
  
  depends_on = [module.network]
}

# =============================================================================
# Monitoring Module - CloudWatch, Prometheus, Grafana
# =============================================================================
module "monitoring" {
  source = "./modules/monitoring"
  
  environment       = local.environment
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.private_subnet_ids
  cluster_name      = module.kubernetes.cluster_name
  retention_days    = var.log_retention_days
  tags              = local.common_tags
  
  depends_on = [module.kubernetes]
}

# =============================================================================
# Security Module - IAM, KMS, Security Groups
# =============================================================================
module "security" {
  source = "./modules/security"
  
  environment       = local.environment
  vpc_id            = module.network.vpc_id
  tags              = local.common_tags
  
  depends_on = [module.network]
}

# Output important information
output "database_endpoint" {
  description = "The connection endpoint for the PostgreSQL database"
  value       = module.database.endpoint
  sensitive   = true
}

output "rabbitmq_endpoint" {
  description = "The connection endpoint for RabbitMQ"
  value       = module.messaging.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "The connection endpoint for Redis"
  value       = module.cache.endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage"
  value       = module.storage.bucket_name
}

output "kubernetes_cluster_name" {
  description = "The name of the Kubernetes cluster"
  value       = module.kubernetes.cluster_name
}

output "kubernetes_cluster_endpoint" {
  description = "The endpoint for the Kubernetes API server"
  value       = module.kubernetes.cluster_endpoint
  sensitive   = true
}