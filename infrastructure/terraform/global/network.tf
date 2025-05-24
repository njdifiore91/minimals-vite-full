# Global Network Infrastructure for MCA Application Processing System
# This file defines the global network infrastructure including VPCs, subnets, transit gateways,
# and peering connections that enable communication between environments.

# ---------------------------------------------------------------------------------------------------------------------
# GLOBAL VPC
# Creates a shared VPC for global resources that need to be accessed from all environments
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_vpc" "global" {
  cidr_block           = var.global_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  
  tags = merge(
    var.tags,
    {
      Name = "global-vpc"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# GLOBAL VPC SUBNETS
# Creates subnets in multiple availability zones for global resources
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_subnet" "global" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.global.id
  cidr_block              = var.global_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false
  
  tags = merge(
    var.tags,
    {
      Name = "global-subnet-${var.availability_zones[count.index]}"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# INTERNET GATEWAY FOR GLOBAL VPC
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_internet_gateway" "global" {
  vpc_id = aws_vpc.global.id
  
  tags = merge(
    var.tags,
    {
      Name = "global-igw"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# ROUTE TABLE FOR GLOBAL VPC
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_route_table" "global" {
  vpc_id = aws_vpc.global.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.global.id
  }
  
  tags = merge(
    var.tags,
    {
      Name = "global-route-table"
      Environment = "global"
    }
  )
}

resource "aws_route_table_association" "global" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.global[count.index].id
  route_table_id = aws_route_table.global.id
}

# ---------------------------------------------------------------------------------------------------------------------
# TRANSIT GATEWAY
# Creates a transit gateway to enable communication between different environment VPCs
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_ec2_transit_gateway" "main" {
  description                     = "Transit Gateway for MCA Application Processing System"
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  dns_support                     = "enable"
  vpn_ecmp_support                = "enable"
  
  tags = merge(
    var.tags,
    {
      Name = "mca-transit-gateway"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# TRANSIT GATEWAY ATTACHMENTS
# Attaches each environment VPC to the transit gateway
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_ec2_transit_gateway_vpc_attachment" "development" {
  subnet_ids         = data.terraform_remote_state.development.outputs.private_subnet_ids
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = data.terraform_remote_state.development.outputs.vpc_id
  
  dns_support                                     = "enable"
  transit_gateway_default_route_table_association = true
  transit_gateway_default_route_table_propagation = true
  
  tags = merge(
    var.tags,
    {
      Name = "development-tgw-attachment"
      Environment = "development"
    }
  )
}

resource "aws_ec2_transit_gateway_vpc_attachment" "staging" {
  subnet_ids         = data.terraform_remote_state.staging.outputs.private_subnet_ids
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = data.terraform_remote_state.staging.outputs.vpc_id
  
  dns_support                                     = "enable"
  transit_gateway_default_route_table_association = true
  transit_gateway_default_route_table_propagation = true
  
  tags = merge(
    var.tags,
    {
      Name = "staging-tgw-attachment"
      Environment = "staging"
    }
  )
}

resource "aws_ec2_transit_gateway_vpc_attachment" "production" {
  subnet_ids         = data.terraform_remote_state.production.outputs.private_subnet_ids
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = data.terraform_remote_state.production.outputs.vpc_id
  
  dns_support                                     = "enable"
  transit_gateway_default_route_table_association = true
  transit_gateway_default_route_table_propagation = true
  
  tags = merge(
    var.tags,
    {
      Name = "production-tgw-attachment"
      Environment = "production"
    }
  )
}

resource "aws_ec2_transit_gateway_vpc_attachment" "global" {
  subnet_ids         = aws_subnet.global[*].id
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.global.id
  
  dns_support                                     = "enable"
  transit_gateway_default_route_table_association = true
  transit_gateway_default_route_table_propagation = true
  
  tags = merge(
    var.tags,
    {
      Name = "global-tgw-attachment"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# TRANSIT GATEWAY ROUTE TABLE
# Creates a route table for the transit gateway and adds routes for each environment VPC
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_ec2_transit_gateway_route_table" "main" {
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "mca-transit-gateway-route-table"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# VPC PEERING CONNECTIONS (ALTERNATIVE TO TRANSIT GATEWAY)
# Creates peering connections between environment VPCs for direct communication
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_vpc_peering_connection" "dev_staging" {
  vpc_id      = data.terraform_remote_state.development.outputs.vpc_id
  peer_vpc_id = data.terraform_remote_state.staging.outputs.vpc_id
  auto_accept = true
  
  accepter {
    allow_remote_vpc_dns_resolution = true
  }
  
  requester {
    allow_remote_vpc_dns_resolution = true
  }
  
  tags = merge(
    var.tags,
    {
      Name = "dev-staging-peering"
      Side = "Requester"
    }
  )
}

resource "aws_vpc_peering_connection" "staging_production" {
  vpc_id      = data.terraform_remote_state.staging.outputs.vpc_id
  peer_vpc_id = data.terraform_remote_state.production.outputs.vpc_id
  auto_accept = true
  
  accepter {
    allow_remote_vpc_dns_resolution = true
  }
  
  requester {
    allow_remote_vpc_dns_resolution = true
  }
  
  tags = merge(
    var.tags,
    {
      Name = "staging-production-peering"
      Side = "Requester"
    }
  )
}

resource "aws_vpc_peering_connection" "dev_production" {
  vpc_id      = data.terraform_remote_state.development.outputs.vpc_id
  peer_vpc_id = data.terraform_remote_state.production.outputs.vpc_id
  auto_accept = true
  
  accepter {
    allow_remote_vpc_dns_resolution = true
  }
  
  requester {
    allow_remote_vpc_dns_resolution = true
  }
  
  tags = merge(
    var.tags,
    {
      Name = "dev-production-peering"
      Side = "Requester"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# ROUTE TABLE ENTRIES FOR VPC PEERING
# Adds routes to each environment's route tables for the peering connections
# ---------------------------------------------------------------------------------------------------------------------
# Development to Staging
resource "aws_route" "dev_to_staging" {
  count                     = length(data.terraform_remote_state.development.outputs.private_route_table_ids)
  route_table_id            = data.terraform_remote_state.development.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.staging.outputs.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_staging.id
}

# Staging to Development
resource "aws_route" "staging_to_dev" {
  count                     = length(data.terraform_remote_state.staging.outputs.private_route_table_ids)
  route_table_id            = data.terraform_remote_state.staging.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.development.outputs.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_staging.id
}

# Staging to Production
resource "aws_route" "staging_to_production" {
  count                     = length(data.terraform_remote_state.staging.outputs.private_route_table_ids)
  route_table_id            = data.terraform_remote_state.staging.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.production.outputs.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.staging_production.id
}

# Production to Staging
resource "aws_route" "production_to_staging" {
  count                     = length(data.terraform_remote_state.production.outputs.private_route_table_ids)
  route_table_id            = data.terraform_remote_state.production.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.staging.outputs.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.staging_production.id
}

# Development to Production
resource "aws_route" "dev_to_production" {
  count                     = length(data.terraform_remote_state.development.outputs.private_route_table_ids)
  route_table_id            = data.terraform_remote_state.development.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.production.outputs.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_production.id
}

# Production to Development
resource "aws_route" "production_to_dev" {
  count                     = length(data.terraform_remote_state.production.outputs.private_route_table_ids)
  route_table_id            = data.terraform_remote_state.production.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.development.outputs.vpc_cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_production.id
}

# ---------------------------------------------------------------------------------------------------------------------
# ROUTE TABLE ENTRIES FOR TRANSIT GATEWAY
# Adds routes to each environment's route tables for the transit gateway
# ---------------------------------------------------------------------------------------------------------------------
# Development to Transit Gateway (for global VPC)
resource "aws_route" "dev_to_global_via_tgw" {
  count                  = length(data.terraform_remote_state.development.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.development.outputs.private_route_table_ids[count.index]
  destination_cidr_block = var.global_vpc_cidr
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.development]
}

# Development to Staging via Transit Gateway
resource "aws_route" "dev_to_staging_via_tgw" {
  count                  = length(data.terraform_remote_state.development.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.development.outputs.private_route_table_ids[count.index]
  destination_cidr_block = data.terraform_remote_state.staging.outputs.vpc_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.development]
}

# Development to Production via Transit Gateway
resource "aws_route" "dev_to_production_via_tgw" {
  count                  = length(data.terraform_remote_state.development.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.development.outputs.private_route_table_ids[count.index]
  destination_cidr_block = data.terraform_remote_state.production.outputs.vpc_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.development]
}

# Staging to Transit Gateway (for global VPC)
resource "aws_route" "staging_to_global_via_tgw" {
  count                  = length(data.terraform_remote_state.staging.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.staging.outputs.private_route_table_ids[count.index]
  destination_cidr_block = var.global_vpc_cidr
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.staging]
}

# Staging to Development via Transit Gateway
resource "aws_route" "staging_to_dev_via_tgw" {
  count                  = length(data.terraform_remote_state.staging.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.staging.outputs.private_route_table_ids[count.index]
  destination_cidr_block = data.terraform_remote_state.development.outputs.vpc_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.staging]
}

# Staging to Production via Transit Gateway
resource "aws_route" "staging_to_production_via_tgw" {
  count                  = length(data.terraform_remote_state.staging.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.staging.outputs.private_route_table_ids[count.index]
  destination_cidr_block = data.terraform_remote_state.production.outputs.vpc_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.staging]
}

# Production to Transit Gateway (for global VPC)
resource "aws_route" "production_to_global_via_tgw" {
  count                  = length(data.terraform_remote_state.production.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.production.outputs.private_route_table_ids[count.index]
  destination_cidr_block = var.global_vpc_cidr
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.production]
}

# Production to Development via Transit Gateway
resource "aws_route" "production_to_dev_via_tgw" {
  count                  = length(data.terraform_remote_state.production.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.production.outputs.private_route_table_ids[count.index]
  destination_cidr_block = data.terraform_remote_state.development.outputs.vpc_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.production]
}

# Production to Staging via Transit Gateway
resource "aws_route" "production_to_staging_via_tgw" {
  count                  = length(data.terraform_remote_state.production.outputs.private_route_table_ids)
  route_table_id         = data.terraform_remote_state.production.outputs.private_route_table_ids[count.index]
  destination_cidr_block = data.terraform_remote_state.staging.outputs.vpc_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.production]
}

# Global to Transit Gateway
resource "aws_route" "global_to_tgw" {
  route_table_id         = aws_route_table.global.id
  destination_cidr_block = "0.0.0.0/0"
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
  
  depends_on = [aws_ec2_transit_gateway_vpc_attachment.global]
}

# ---------------------------------------------------------------------------------------------------------------------
# NETWORK ACLs FOR GLOBAL VPC
# Creates network ACLs for the global VPC to control traffic at the subnet level
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_network_acl" "global" {
  vpc_id     = aws_vpc.global.id
  subnet_ids = aws_subnet.global[*].id
  
  # Allow all inbound traffic from environment VPCs
  ingress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = data.terraform_remote_state.development.outputs.vpc_cidr_block
    from_port  = 0
    to_port    = 0
  }
  
  ingress {
    protocol   = -1
    rule_no    = 110
    action     = "allow"
    cidr_block = data.terraform_remote_state.staging.outputs.vpc_cidr_block
    from_port  = 0
    to_port    = 0
  }
  
  ingress {
    protocol   = -1
    rule_no    = 120
    action     = "allow"
    cidr_block = data.terraform_remote_state.production.outputs.vpc_cidr_block
    from_port  = 0
    to_port    = 0
  }
  
  # Allow all outbound traffic
  egress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  
  tags = merge(
    var.tags,
    {
      Name = "global-network-acl"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# SECURITY GROUPS FOR GLOBAL VPC
# Creates security groups for the global VPC to control traffic at the instance level
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_security_group" "global" {
  name        = "global-sg"
  description = "Security group for global VPC resources"
  vpc_id      = aws_vpc.global.id
  
  # Allow all inbound traffic from environment VPCs
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [
      data.terraform_remote_state.development.outputs.vpc_cidr_block,
      data.terraform_remote_state.staging.outputs.vpc_cidr_block,
      data.terraform_remote_state.production.outputs.vpc_cidr_block
    ]
    description = "Allow all traffic from environment VPCs"
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
    var.tags,
    {
      Name = "global-security-group"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# FLOW LOGS FOR GLOBAL VPC
# Enables flow logs for the global VPC to monitor network traffic
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_flow_log" "global" {
  log_destination      = var.flow_log_destination_arn
  log_destination_type = "s3"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.global.id
  
  tags = merge(
    var.tags,
    {
      Name = "global-vpc-flow-logs"
      Environment = "global"
    }
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# DATA SOURCES
# Retrieves information about environment-specific resources from remote state
# ---------------------------------------------------------------------------------------------------------------------
data "terraform_remote_state" "development" {
  backend = "s3"
  
  config = {
    bucket = var.terraform_state_bucket
    key    = "environments/development/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "staging" {
  backend = "s3"
  
  config = {
    bucket = var.terraform_state_bucket
    key    = "environments/staging/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "production" {
  backend = "s3"
  
  config = {
    bucket = var.terraform_state_bucket
    key    = "environments/production/terraform.tfstate"
    region = var.aws_region
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# VARIABLES
# ---------------------------------------------------------------------------------------------------------------------
variable "global_vpc_cidr" {
  description = "CIDR block for the global VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "global_subnet_cidrs" {
  description = "CIDR blocks for the global VPC subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "availability_zones" {
  description = "List of availability zones to use for resources"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "terraform_state_bucket" {
  description = "S3 bucket containing Terraform state files"
  type        = string
  default     = "mca-terraform-state"
}

variable "flow_log_destination_arn" {
  description = "ARN of the S3 bucket for VPC flow logs"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {
    Project     = "MCA Application Processing System"
    ManagedBy   = "Terraform"
    Environment = "global"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "transit_gateway_id" {
  description = "ID of the transit gateway"
  value       = aws_ec2_transit_gateway.main.id
}

output "transit_gateway_route_table_id" {
  description = "ID of the transit gateway route table"
  value       = aws_ec2_transit_gateway_route_table.main.id
}

output "global_vpc_id" {
  description = "ID of the global VPC"
  value       = aws_vpc.global.id
}

output "global_subnet_ids" {
  description = "IDs of the global VPC subnets"
  value       = aws_subnet.global[*].id
}

output "global_security_group_id" {
  description = "ID of the global security group"
  value       = aws_security_group.global.id
}

output "global_vpc_cidr_block" {
  description = "CIDR block of the global VPC"
  value       = aws_vpc.global.cidr_block
}

output "vpc_peering_connection_ids" {
  description = "IDs of the VPC peering connections"
  value       = {
    dev_staging     = aws_vpc_peering_connection.dev_staging.id
    staging_production = aws_vpc_peering_connection.staging_production.id
    dev_production  = aws_vpc_peering_connection.dev_production.id
  }
}