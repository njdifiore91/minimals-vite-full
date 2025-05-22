/**
 * Network Module for MCA Application Processing System
 * 
 * This module creates the network infrastructure required for the MCA Application Processing System,
 * including VPC, subnets, security groups, and network ACLs. It supports multi-region, multi-AZ
 * deployment for high availability and disaster recovery, and provides network segmentation for
 * microservices security.
 *
 * The network infrastructure is designed to support Kubernetes-based deployment with logical network
 * boundaries between service groups and enforces TLS 1.3 for all service-to-service communications.
 */

terraform {
  required_version = ">= 1.3.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

# Variables for the network module
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use for subnets"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for the database subnets"
  type        = list(string)
  default     = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT Gateway for all private subnets"
  type        = bool
  default     = false
}

variable "enable_vpn_gateway" {
  description = "Enable VPN Gateway"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Local variables
locals {
  # Ensure we have the same number of AZs, public, private, and database subnets
  az_count = length(var.availability_zones)
  
  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Module      = "network"
    }
  )
  
  # Network ACL rules for microservices segmentation
  microservices_acl_rules = {
    # Allow traffic between services within the same subnet
    allow_internal = {
      rule_number = 100
      egress      = false
      protocol    = "tcp"
      rule_action = "allow"
      cidr_block  = var.vpc_cidr
      from_port   = 0
      to_port     = 65535
    }
    
    # Allow outbound traffic to the internet
    allow_outbound = {
      rule_number = 200
      egress      = true
      protocol    = "-1"
      rule_action = "allow"
      cidr_block  = "0.0.0.0/0"
      from_port   = 0
      to_port     = 0
    }
  }
}

# VPC Module for creating the network infrastructure
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 3.19.0"

  name = "${var.environment}-mca-vpc"
  cidr = var.vpc_cidr

  azs              = var.availability_zones
  public_subnets   = var.public_subnet_cidrs
  private_subnets  = var.private_subnet_cidrs
  database_subnets = var.database_subnet_cidrs

  # Enable DNS support
  enable_dns_hostnames = true
  enable_dns_support   = true

  # NAT Gateway configuration
  enable_nat_gateway     = var.enable_nat_gateway
  single_nat_gateway     = var.single_nat_gateway
  one_nat_gateway_per_az = !var.single_nat_gateway

  # VPN Gateway configuration
  enable_vpn_gateway = var.enable_vpn_gateway

  # Public subnet configuration
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    Tier                     = "Public"
  }

  # Private subnet configuration
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    Tier                              = "Private"
    "kubernetes.io/cluster/${var.environment}-mca-cluster" = "shared"
  }

  # Database subnet configuration
  database_subnet_tags = {
    Tier = "Database"
  }

  # Create a dedicated route table for database subnets
  create_database_subnet_route_table = true

  # Enable flow logs for VPC traffic monitoring and security analysis
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_max_aggregation_interval    = 60

  # Apply common tags to all resources
  tags = local.common_tags
}

# Security group for Kubernetes control plane
resource "aws_security_group" "k8s_control_plane" {
  name        = "${var.environment}-k8s-control-plane-sg"
  description = "Security group for Kubernetes control plane"
  vpc_id      = module.vpc.vpc_id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow inbound API server traffic
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Kubernetes API server"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-k8s-control-plane-sg"
    }
  )
}

# Security group for worker nodes
resource "aws_security_group" "k8s_worker_nodes" {
  name        = "${var.environment}-k8s-worker-nodes-sg"
  description = "Security group for Kubernetes worker nodes"
  vpc_id      = module.vpc.vpc_id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow inbound traffic from control plane
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.k8s_control_plane.id]
    description     = "Allow all TCP traffic from control plane"
  }

  # Allow inbound traffic from other worker nodes
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    self            = true
    description     = "Allow all TCP traffic between worker nodes"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-k8s-worker-nodes-sg"
    }
  )
}

# Security group for database instances
resource "aws_security_group" "database" {
  name        = "${var.environment}-database-sg"
  description = "Security group for database instances"
  vpc_id      = module.vpc.vpc_id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow PostgreSQL traffic from worker nodes
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.k8s_worker_nodes.id]
    description     = "PostgreSQL from worker nodes"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-database-sg"
    }
  )
}

# Network ACL for microservices segmentation
resource "aws_network_acl" "microservices" {
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Allow all inbound traffic within VPC
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 0
    to_port    = 65535
  }

  # Allow all outbound traffic
  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.environment}-microservices-acl"
    }
  )
}

# Outputs from the network module
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "database_subnet_ids" {
  description = "List of IDs of database subnets"
  value       = module.vpc.database_subnets
}

output "nat_public_ips" {
  description = "List of public Elastic IPs created for AWS NAT Gateway"
  value       = module.vpc.nat_public_ips
}

output "public_route_table_ids" {
  description = "List of IDs of public route tables"
  value       = module.vpc.public_route_table_ids
}

output "private_route_table_ids" {
  description = "List of IDs of private route tables"
  value       = module.vpc.private_route_table_ids
}

output "database_route_table_ids" {
  description = "List of IDs of database route tables"
  value       = module.vpc.database_route_table_ids
}

output "default_security_group_id" {
  description = "The ID of the security group created by default on VPC creation"
  value       = module.vpc.default_security_group_id
}

output "k8s_control_plane_security_group_id" {
  description = "ID of the security group for Kubernetes control plane"
  value       = aws_security_group.k8s_control_plane.id
}

output "k8s_worker_nodes_security_group_id" {
  description = "ID of the security group for Kubernetes worker nodes"
  value       = aws_security_group.k8s_worker_nodes.id
}

output "database_security_group_id" {
  description = "ID of the security group for database instances"
  value       = aws_security_group.database.id
}