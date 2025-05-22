# route_tables.tf - Defines route tables for VPC subnets, including routes for internet access, NAT gateways, and internal communication
# This file establishes the network traffic flow patterns within the VPC and to external networks

# This implementation supports:
# 1. Network segmentation as required in section 3.8.3
# 2. Secure routing patterns as implied in section 3.8.6
# 3. Support for multi-AZ deployment as specified in section 8.2.1
# 4. Database isolation as outlined in section 8.4.3

# ---------------------------------------------------------------------------------------------------------------------
# PUBLIC ROUTE TABLES - Allow internet access via Internet Gateway
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_route_table" "public" {
  count  = length(var.availability_zones)
  vpc_id = var.vpc_id

  # Default route to internet via Internet Gateway
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = var.internet_gateway_id
  }

  # TLS 1.3 enforcement is handled at the application level and through security groups
  # Network segmentation is implemented through subnet associations and security groups

  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-rt-public-${var.availability_zones[count.index]}"
      Environment = var.environment
      Tier        = "public"
      AZ          = var.availability_zones[count.index]
      ManagedBy   = "terraform"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# PRIVATE ROUTE TABLES - Allow outbound internet access via NAT Gateway (one per AZ for high availability)
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = var.vpc_id

  # Default route to internet via NAT Gateway (AZ-specific for high availability)
  # This follows AWS best practices for multi-AZ deployments as specified in section 8.2.1
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = var.nat_gateway_ids[count.index]
  }

  # Additional routes can be added dynamically using aws_route resources
  # This separation allows for cleaner management of routes

  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-rt-private-${var.availability_zones[count.index]}"
      Environment = var.environment
      Tier        = "private"
      AZ          = var.availability_zones[count.index]
      ManagedBy   = "terraform"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# DATABASE ROUTE TABLES - Internal-only routes with no direct internet access
# Implements database isolation as outlined in section 8.4.3
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_route_table" "database" {
  count  = length(var.availability_zones)
  vpc_id = var.vpc_id

  # No default route to internet - database subnets are isolated
  # Only local VPC routes are automatically added
  # This implements the database isolation requirement from section 8.4.3
  
  # For database maintenance access, specific routes can be added to the private subnets
  # This maintains security while allowing controlled access

  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-rt-database-${var.availability_zones[count.index]}"
      Environment = var.environment
      Tier        = "database"
      AZ          = var.availability_zones[count.index]
      ManagedBy   = "terraform"
      Isolated    = "true"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# ROUTE TABLE ASSOCIATIONS - Associate route tables with their respective subnets
# Implements network segmentation as required in section 3.8.3
# ---------------------------------------------------------------------------------------------------------------------

# Public subnet associations - for API Gateway and public-facing components
resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_ids)
  subnet_id      = var.public_subnet_ids[count.index]
  route_table_id = aws_route_table.public[count.index % length(var.availability_zones)].id
}

# Private subnet associations - for application services (microservices)
# These implement the network segmentation requirement from section 3.8.3
resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_ids)
  subnet_id      = var.private_subnet_ids[count.index]
  route_table_id = aws_route_table.private[count.index % length(var.availability_zones)].id
}

# Database subnet associations - for PostgreSQL and other data services
# These implement the database isolation requirement from section 8.4.3
resource "aws_route_table_association" "database" {
  count          = length(var.database_subnet_ids)
  subnet_id      = var.database_subnet_ids[count.index]
  route_table_id = aws_route_table.database[count.index % length(var.availability_zones)].id
}