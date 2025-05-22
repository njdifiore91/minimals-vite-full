# NAT Gateway Configuration for MCA Application Processing System
# This file defines NAT gateways for private subnets to allow outbound internet access
# while maintaining security. Services in private subnets can access external resources
# without being directly exposed to the internet.

# Elastic IP allocations for NAT Gateways
# One EIP per availability zone for high availability
resource "aws_eip" "nat" {
  count = length(var.availability_zones)
  
  domain = "vpc"
  
  tags = {
    Name        = "${var.environment}-nat-eip-${var.availability_zones[count.index]}"
    Environment = var.environment
    Purpose     = "NAT Gateway"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing"
  }
}

# NAT Gateways - one per availability zone for high availability
# Each NAT gateway is placed in a public subnet but serves private subnets
resource "aws_nat_gateway" "main" {
  count = length(var.availability_zones)
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = var.public_subnet_ids[count.index]
  
  tags = {
    Name        = "${var.environment}-nat-gateway-${var.availability_zones[count.index]}"
    Environment = var.environment
    Purpose     = "Private subnet internet access"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing"
  }
  
  # Ensure the Internet Gateway is available before creating NAT Gateways
  depends_on = [var.internet_gateway_id]
}

# Output the NAT Gateway IDs for use in route tables
output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways created for private subnet internet access"
  value       = aws_nat_gateway.main[*].id
}

# Output the Elastic IP addresses associated with NAT Gateways
output "nat_gateway_eips" {
  description = "Elastic IP addresses associated with NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}