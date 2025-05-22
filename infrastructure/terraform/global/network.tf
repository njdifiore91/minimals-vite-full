# Global Network Infrastructure for MCA Application Processing System

# -----------------------------------------------------------------------------
# Global VPC for shared resources
# -----------------------------------------------------------------------------
resource "aws_vpc" "global" {
  cidr_block           = var.global_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  instance_tenancy     = "default"

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-vpc"
    }
  )
}

# -----------------------------------------------------------------------------
# Global Subnets (across multiple availability zones)
# -----------------------------------------------------------------------------
resource "aws_subnet" "global_public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.global.id
  cidr_block        = cidrsubnet(var.global_vpc_cidr, 8, count.index)
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-public-${var.availability_zones[count.index]}"
      Tier = "public"
    }
  )
}

resource "aws_subnet" "global_private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.global.id
  cidr_block        = cidrsubnet(var.global_vpc_cidr, 8, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-private-${var.availability_zones[count.index]}"
      Tier = "private"
    }
  )
}

# -----------------------------------------------------------------------------
# Internet Gateway for global VPC
# -----------------------------------------------------------------------------
resource "aws_internet_gateway" "global" {
  vpc_id = aws_vpc.global.id

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-igw"
    }
  )
}

# -----------------------------------------------------------------------------
# NAT Gateways for private subnet internet access
# -----------------------------------------------------------------------------
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-nat-eip-${count.index}"
    }
  )
}

resource "aws_nat_gateway" "global" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.global_public[count.index].id

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-nat-${var.availability_zones[count.index]}"
    }
  )

  depends_on = [aws_internet_gateway.global]
}

# -----------------------------------------------------------------------------
# Route Tables for global VPC
# -----------------------------------------------------------------------------
resource "aws_route_table" "global_public" {
  vpc_id = aws_vpc.global.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.global.id
  }

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-public-rt"
    }
  )
}

resource "aws_route_table" "global_private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.global.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.global[count.index].id
  }

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-private-rt-${var.availability_zones[count.index]}"
    }
  )
}

# -----------------------------------------------------------------------------
# Route Table Associations
# -----------------------------------------------------------------------------
resource "aws_route_table_association" "global_public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.global_public[count.index].id
  route_table_id = aws_route_table.global_public.id
}

resource "aws_route_table_association" "global_private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.global_private[count.index].id
  route_table_id = aws_route_table.global_private[count.index].id
}

# -----------------------------------------------------------------------------
# Transit Gateway for inter-environment communication
# -----------------------------------------------------------------------------
resource "aws_ec2_transit_gateway" "main" {
  description                     = "Transit Gateway for MCA Application environments"
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  dns_support                     = "enable"
  vpn_ecmp_support                = "enable"
  
  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-transit-gateway"
    }
  )
}

# Attach global VPC to Transit Gateway
resource "aws_ec2_transit_gateway_vpc_attachment" "global" {
  subnet_ids         = [for subnet in aws_subnet.global_private : subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.global.id
  
  dns_support                                     = "enable"
  transit_gateway_default_route_table_association = true
  transit_gateway_default_route_table_propagation = true
  
  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-tgw-attachment"
    }
  )
}

# -----------------------------------------------------------------------------
# CIDR Block Allocations for Environments
# -----------------------------------------------------------------------------
# These CIDR blocks are reserved for each environment to avoid IP conflicts
# They will be used in environment-specific Terraform configurations

resource "aws_vpc_ipv4_cidr_block_association" "development" {
  vpc_id     = aws_vpc.global.id
  cidr_block = var.development_cidr
}

resource "aws_vpc_ipv4_cidr_block_association" "staging" {
  vpc_id     = aws_vpc.global.id
  cidr_block = var.staging_cidr
}

resource "aws_vpc_ipv4_cidr_block_association" "production" {
  vpc_id     = aws_vpc.global.id
  cidr_block = var.production_cidr
}

# -----------------------------------------------------------------------------
# VPC Peering for direct environment communication (if needed)
# -----------------------------------------------------------------------------
# These resources will be created when environment-specific VPCs are created
# They are commented out here as they depend on environment VPCs that are defined
# in their respective environment directories

# resource "aws_vpc_peering_connection" "dev_to_staging" {
#   vpc_id      = var.development_vpc_id
#   peer_vpc_id = var.staging_vpc_id
#   auto_accept = true
#
#   tags = merge(
#     var.global_tags,
#     {
#       Name = "${var.resource_prefix}-dev-to-staging-peering"
#     }
#   )
# }
#
# resource "aws_vpc_peering_connection" "staging_to_prod" {
#   vpc_id      = var.staging_vpc_id
#   peer_vpc_id = var.production_vpc_id
#   auto_accept = true
#
#   tags = merge(
#     var.global_tags,
#     {
#       Name = "${var.resource_prefix}-staging-to-prod-peering"
#     }
#   )
# }

# -----------------------------------------------------------------------------
# Network ACLs for enhanced security
# -----------------------------------------------------------------------------
resource "aws_network_acl" "global_public" {
  vpc_id     = aws_vpc.global.id
  subnet_ids = [for subnet in aws_subnet.global_public : subnet.id]

  # Allow all inbound HTTP/HTTPS traffic
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  # Allow all return traffic
  ingress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
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
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-public-nacl"
    }
  )
}

resource "aws_network_acl" "global_private" {
  vpc_id     = aws_vpc.global.id
  subnet_ids = [for subnet in aws_subnet.global_private : subnet.id]

  # Allow inbound traffic from public subnets
  ingress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = var.global_vpc_cidr
    from_port  = 0
    to_port    = 0
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
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-private-nacl"
    }
  )
}

# -----------------------------------------------------------------------------
# VPC Flow Logs for network traffic monitoring
# -----------------------------------------------------------------------------
resource "aws_flow_log" "global" {
  iam_role_arn    = var.flow_log_role_arn
  log_destination = var.flow_log_destination
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.global.id

  tags = merge(
    var.global_tags,
    {
      Name = "${var.resource_prefix}-global-vpc-flow-log"
    }
  )
}

# -----------------------------------------------------------------------------
# Multi-region configuration for high availability
# -----------------------------------------------------------------------------
# These resources would be replicated in a secondary region for disaster recovery
# They are commented out here as they would be part of a separate Terraform configuration
# for the secondary region

# resource "aws_vpc" "global_secondary" {
#   provider             = aws.secondary_region
#   cidr_block           = var.global_vpc_secondary_cidr
#   enable_dns_support   = true
#   enable_dns_hostnames = true
#   instance_tenancy     = "default"
#
#   tags = merge(
#     var.global_tags,
#     {
#       Name = "${var.resource_prefix}-global-vpc-secondary"
#     }
#   )
# }