# Route Tables Configuration for MCA Application Processing System
# This file defines route tables for VPC subnets, including routes for internet access,
# NAT gateways, and internal communication. This establishes the network traffic flow
# patterns within the VPC and to external networks.
#
# Key features implemented:
# - Network segmentation with separate route tables for public, private, and database subnets
# - Secure routing patterns with controlled internet access
# - Multi-AZ deployment support for high availability
# - Database subnet isolation with no direct internet access
# - VPC endpoint integration for secure AWS service access
# - Optional Transit Gateway and Network Firewall integration points

# ---------------------------------------------------------------------------------------------------------------------
# PUBLIC ROUTE TABLE
# Route table for public subnets with direct internet access via Internet Gateway
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-public-route-table"
      Tier = "Public"
    }
  )
}

# Add route to Internet Gateway for public subnets
resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Associate public route table with public subnets
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------------------------------------------------
# PRIVATE ROUTE TABLES
# Route tables for private subnets with outbound internet access via NAT Gateways
# One route table per AZ for fault isolation
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-private-route-table-${var.availability_zones[count.index]}"
      Tier = "Private"
      AZ   = var.availability_zones[count.index]
    }
  )
}

# Add routes to NAT Gateways for private subnets
# Each private subnet in an AZ routes through the NAT Gateway in the same AZ
resource "aws_route" "private_nat_gateway" {
  count                  = length(var.availability_zones)
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[count.index].id
}

# Associate private route tables with private subnets
resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ---------------------------------------------------------------------------------------------------------------------
# DATABASE ROUTE TABLES
# Route tables for database subnets with no direct internet access
# One route table per AZ for fault isolation
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_route_table" "database" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-database-route-table-${var.availability_zones[count.index]}"
      Tier = "Database"
      AZ   = var.availability_zones[count.index]
    }
  )
}

# Associate database route tables with database subnets
resource "aws_route_table_association" "database" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database[count.index].id
}

# ---------------------------------------------------------------------------------------------------------------------
# VPC ENDPOINT ROUTE TABLE ASSOCIATIONS
# Associates VPC endpoints with appropriate route tables
# ---------------------------------------------------------------------------------------------------------------------
# Associate S3 Gateway Endpoint with private and database route tables
resource "aws_vpc_endpoint_route_table_association" "private_s3" {
  count           = length(var.availability_zones)
  route_table_id  = aws_route_table.private[count.index].id
  vpc_endpoint_id = aws_vpc_endpoint.s3.id
}

resource "aws_vpc_endpoint_route_table_association" "database_s3" {
  count           = length(var.availability_zones)
  route_table_id  = aws_route_table.database[count.index].id
  vpc_endpoint_id = aws_vpc_endpoint.s3.id
}

# ---------------------------------------------------------------------------------------------------------------------
# TRANSIT GATEWAY ROUTE (OPTIONAL)
# Routes for connecting to on-premises or other VPCs via Transit Gateway
# Uncomment and configure if Transit Gateway integration is required
# ---------------------------------------------------------------------------------------------------------------------
# resource "aws_route" "private_transit_gateway" {
#   count                  = length(var.availability_zones)
#   route_table_id         = aws_route_table.private[count.index].id
#   destination_cidr_block = var.on_premises_cidr
#   transit_gateway_id     = var.transit_gateway_id
# }

# resource "aws_route" "database_transit_gateway" {
#   count                  = length(var.availability_zones)
#   route_table_id         = aws_route_table.database[count.index].id
#   destination_cidr_block = var.on_premises_cidr
#   transit_gateway_id     = var.transit_gateway_id
# }

# ---------------------------------------------------------------------------------------------------------------------
# TRANSIT GATEWAY ATTACHMENTS (OPTIONAL)
# For hybrid connectivity to on-premises networks or other VPCs
# Uncomment and configure if Transit Gateway integration is required
# ---------------------------------------------------------------------------------------------------------------------
# resource "aws_ec2_transit_gateway_vpc_attachment" "tgw_attachment" {
#   subnet_ids         = aws_subnet.private[*].id
#   transit_gateway_id = var.transit_gateway_id
#   vpc_id             = aws_vpc.main.id
#   
#   dns_support                 = "enable"
#   ipv6_support               = "disable"
#   transit_gateway_default_route_table_association = false
#   transit_gateway_default_route_table_propagation = false
#   
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.environment}-tgw-attachment"
#     }
#   )
# }

# ---------------------------------------------------------------------------------------------------------------------
# NETWORK FIREWALL ROUTE TABLE (OPTIONAL)
# For implementing AWS Network Firewall for enhanced security
# Uncomment and configure if Network Firewall is required
# ---------------------------------------------------------------------------------------------------------------------
# resource "aws_route_table" "network_firewall" {
#   vpc_id = aws_vpc.main.id
#   
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.environment}-network-firewall-route-table"
#       Tier = "NetworkFirewall"
#     }
#   )
# }

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = aws_route_table.private[*].id
}

output "database_route_table_ids" {
  description = "IDs of the database route tables"
  value       = aws_route_table.database[*].id
}