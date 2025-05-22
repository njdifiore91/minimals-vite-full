# VPC Configuration for MCA Application Processing System
# This file defines the VPC and subnet configurations for the application,
# including public and private subnets across multiple availability zones.

# ---------------------------------------------------------------------------------------------------------------------
# VPC RESOURCE
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-vpc"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# INTERNET GATEWAY
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-igw"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# PUBLIC SUBNETS
# Creates public subnets across multiple availability zones for components that need internet access
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  
  tags = merge(
    var.tags,
    {
      Name                                           = "${var.environment}-public-subnet-${var.availability_zones[count.index]}"
      "kubernetes.io/role/elb"                     = "1"
      "kubernetes.io/cluster/${var.environment}"   = "shared"
      Tier                                           = "Public"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# PRIVATE SUBNETS
# Creates private subnets across multiple availability zones for application services
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_subnet" "private" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false
  
  tags = merge(
    var.tags,
    {
      Name                                           = "${var.environment}-private-subnet-${var.availability_zones[count.index]}"
      "kubernetes.io/role/internal-elb"            = "1"
      "kubernetes.io/cluster/${var.environment}"   = "shared"
      Tier                                           = "Private"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# DATABASE SUBNETS
# Creates database subnets across multiple availability zones for PostgreSQL deployment
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_subnet" "database" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.database_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-database-subnet-${var.availability_zones[count.index]}"
      Tier = "Database"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# DATABASE SUBNET GROUP
# Creates a subnet group for RDS PostgreSQL deployment
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_db_subnet_group" "database" {
  name        = "${var.environment}-database-subnet-group"
  description = "Database subnet group for ${var.environment} environment"
  subnet_ids  = aws_subnet.database[*].id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-database-subnet-group"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# VPC ENDPOINTS
# Creates VPC endpoints for AWS services to enable private communication
# ---------------------------------------------------------------------------------------------------------------------
# S3 Gateway Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat(aws_route_table.private[*].id, aws_route_table.database[*].id)
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-s3-endpoint"
    }
  )
}

# ECR API Interface Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [var.vpc_endpoint_security_group_id]
  private_dns_enabled = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ecr-api-endpoint"
    }
  )
}

# ECR DKR Interface Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [var.vpc_endpoint_security_group_id]
  private_dns_enabled = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ecr-dkr-endpoint"
    }
  )
}

# CloudWatch Logs Interface Endpoint
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [var.vpc_endpoint_security_group_id]
  private_dns_enabled = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-logs-endpoint"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# VPC FLOW LOGS
# Enables flow logs for network traffic monitoring and security analysis
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_flow_log" "vpc_flow_logs" {
  log_destination      = var.flow_log_destination_arn
  log_destination_type = "s3"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-vpc-flow-logs"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# ROUTE TABLES
# Creates route tables for public, private, and database subnets
# ---------------------------------------------------------------------------------------------------------------------
# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-public-route-table"
      Tier = "Public"
    }
  )
}

# Public Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private Route Tables
resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-private-route-table-${var.availability_zones[count.index]}"
      Tier = "Private"
    }
  )
}

# Private Route Table Associations
resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Database Route Tables
resource "aws_route_table" "database" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-database-route-table-${var.availability_zones[count.index]}"
      Tier = "Database"
    }
  )
}

# Database Route Table Associations
resource "aws_route_table_association" "database" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database[count.index].id
}