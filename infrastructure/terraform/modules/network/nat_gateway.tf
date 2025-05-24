# NAT Gateway Configuration for MCA Application Processing System
# This file defines NAT gateways for private subnets to allow outbound internet access
# while maintaining security. Services in private subnets can access external resources
# without being directly exposed to the internet.
#
# Key features implemented:
# - High availability with one NAT Gateway per AZ (configurable)
# - Support for microservices in private subnets as outlined in section 0.1.2
# - Secure outbound internet access for private services as required in section 3.8.3
# - Network segmentation support through isolated routing paths
# - Optional single NAT Gateway mode for development environments
# - Support for existing Elastic IP reuse

# ---------------------------------------------------------------------------------------------------------------------
# ELASTIC IP ADDRESSES FOR NAT GATEWAYS
# Creates Elastic IPs that will be attached to the NAT Gateways
# If reuse_nat_ips is true, these resources will not be created and external_nat_ip_ids will be used
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_eip" "nat" {
  count = var.reuse_nat_ips ? 0 : (var.single_nat_gateway ? 1 : length(var.availability_zones))
  domain = "vpc"

  tags = merge(
    var.tags,
    var.nat_eip_tags,
    {
      Name = var.single_nat_gateway ? "${var.environment}-nat-eip" : "${var.environment}-nat-eip-${var.availability_zones[count.index]}"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# NAT GATEWAYS
# Creates NAT Gateways in public subnets to allow private subnet resources to access the internet
# If single_nat_gateway is true, only one NAT Gateway will be created
# If one_nat_gateway_per_az is true, one NAT Gateway per AZ will be created
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_nat_gateway" "main" {
  count = var.single_nat_gateway ? 1 : length(var.availability_zones)

  # Place NAT Gateways in public subnets
  allocation_id = var.reuse_nat_ips ? var.external_nat_ip_ids[count.index] : aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.tags,
    var.nat_gateway_tags,
    {
      Name = var.single_nat_gateway ? "${var.environment}-nat-gateway" : "${var.environment}-nat-gateway-${var.availability_zones[count.index]}"
    }
  )

  # To ensure proper ordering, add explicit dependencies
  depends_on = [aws_internet_gateway.main]

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "List of public Elastic IPs created for AWS NAT Gateway"
  value       = var.reuse_nat_ips ? var.external_nat_ip_ids : aws_eip.nat[*].public_ip
}

output "nat_gateway_private_ips" {
  description = "List of private IPs of the NAT Gateways"
  value       = aws_nat_gateway.main[*].private_ip
}

output "nat_gateway_count" {
  description = "Number of NAT Gateways created"
  value       = var.single_nat_gateway ? 1 : length(var.availability_zones)
}

output "nat_gateway_allocation_ids" {
  description = "List of Elastic IP allocation IDs for NAT Gateways"
  value       = var.reuse_nat_ips ? var.external_nat_ip_ids : aws_eip.nat[*].id
}