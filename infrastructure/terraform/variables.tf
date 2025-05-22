# =============================================================================
# MCA Application Processing System - Terraform Variables
# =============================================================================
# This file defines all variables used in the main.tf configuration file
# for the MCA Application Processing System infrastructure.
# =============================================================================

# General variables
variable "environment" {
  description = "The deployment environment (development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "The AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "cost_center" {
  description = "Cost center for resource tagging and billing"
  type        = string
  default     = "MCA-Application"
}

# Network variables
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# Database variables
variable "db_instance_class" {
  description = "Instance class for the PostgreSQL database"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage for the PostgreSQL database in GB"
  type        = number
  default     = 20
}

variable "db_username" {
  description = "Master username for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Master password for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for the PostgreSQL database"
  type        = bool
  default     = true
}

variable "db_backup_retention" {
  description = "Number of days to retain database backups"
  type        = number
  default     = 30
}

variable "db_read_replica_count" {
  description = "Number of read replicas for the PostgreSQL database"
  type        = number
  default     = 2
}

# RabbitMQ variables
variable "mq_instance_type" {
  description = "Instance type for RabbitMQ nodes"
  type        = string
  default     = "mq.t3.micro"
}

variable "mq_cluster_size" {
  description = "Number of nodes in the RabbitMQ cluster"
  type        = number
  default     = 3
}

variable "mq_username" {
  description = "Username for RabbitMQ"
  type        = string
  sensitive   = true
}

variable "mq_password" {
  description = "Password for RabbitMQ"
  type        = string
  sensitive   = true
}

# Redis variables
variable "redis_node_type" {
  description = "Node type for Redis cluster"
  type        = string
  default     = "cache.t3.small"
}

variable "redis_num_cache_nodes" {
  description = "Number of nodes in the Redis cluster"
  type        = number
  default     = 3
}

# S3 variables
variable "s3_lifecycle_rules" {
  description = "Lifecycle rules for S3 bucket"
  type        = list(object({
    id                       = string
    status                   = string
    prefix                   = string
    transition_days          = number
    transition_storage_class = string
    expiration_days          = number
  }))
  default     = [
    {
      id                       = "archive-after-30-days"
      status                   = "Enabled"
      prefix                   = ""
      transition_days          = 30
      transition_storage_class = "STANDARD_IA"
      expiration_days          = 0
    }
  ]
}

# Kubernetes variables
variable "k8s_cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.27"
}

variable "k8s_node_groups" {
  description = "Node groups configuration for the EKS cluster"
  type        = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
  }))
  default     = {
    standard = {
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 5
      desired_size   = 2
      disk_size      = 50
    },
    gpu = {
      instance_types = ["g4dn.xlarge"]
      min_size       = 1
      max_size       = 3
      desired_size   = 1
      disk_size      = 100
    }
  }
}

# Monitoring variables
variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}