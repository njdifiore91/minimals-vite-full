# Network Module Outputs
# This file defines output values from the network module that are consumed by other modules
# for the Merchant Cash Advance (MCA) Application Processing System

# VPC Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_name" {
  description = "The name of the VPC"
  value       = aws_vpc.main.tags["Name"]
}

# Subnet Outputs
output "public_subnet_ids" {
  description = "List of IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "List of IDs of database subnets"
  value       = aws_subnet.database[*].id
}

output "public_subnet_cidr_blocks" {
  description = "List of CIDR blocks of public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "private_subnet_cidr_blocks" {
  description = "List of CIDR blocks of private subnets"
  value       = aws_subnet.private[*].cidr_block
}

output "database_subnet_cidr_blocks" {
  description = "List of CIDR blocks of database subnets"
  value       = aws_subnet.database[*].cidr_block
}

# Availability Zone Outputs
output "availability_zones" {
  description = "List of availability zones used"
  value       = var.availability_zones
}

# Security Group Outputs
output "default_security_group_id" {
  description = "The ID of the default security group"
  value       = aws_security_group.default.id
}

output "api_security_group_id" {
  description = "The ID of the API Gateway security group"
  value       = aws_security_group.api_gateway.id
}

output "app_security_group_id" {
  description = "The ID of the application security group"
  value       = aws_security_group.application.id
}

output "db_security_group_id" {
  description = "The ID of the database security group"
  value       = aws_security_group.database.id
}

output "cache_security_group_id" {
  description = "The ID of the Redis cache security group"
  value       = aws_security_group.redis.id
}

output "mq_security_group_id" {
  description = "The ID of the RabbitMQ security group"
  value       = aws_security_group.rabbitmq.id
}

output "ocr_service_security_group_id" {
  description = "The ID of the OCR service security group with GPU access"
  value       = aws_security_group.ocr_service.id
}

# Load Balancer Outputs
output "public_alb_id" {
  description = "The ID of the public Application Load Balancer"
  value       = aws_lb.public.id
}

output "public_alb_arn" {
  description = "The ARN of the public Application Load Balancer"
  value       = aws_lb.public.arn
}

output "public_alb_dns_name" {
  description = "The DNS name of the public Application Load Balancer"
  value       = aws_lb.public.dns_name
}

output "public_alb_zone_id" {
  description = "The canonical hosted zone ID of the public Application Load Balancer"
  value       = aws_lb.public.zone_id
}

output "internal_alb_id" {
  description = "The ID of the internal Application Load Balancer"
  value       = aws_lb.internal.id
}

output "internal_alb_arn" {
  description = "The ARN of the internal Application Load Balancer"
  value       = aws_lb.internal.arn
}

output "internal_alb_dns_name" {
  description = "The DNS name of the internal Application Load Balancer"
  value       = aws_lb.internal.dns_name
}

# NAT Gateway Outputs
output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.nat[*].id
}

output "nat_gateway_public_ips" {
  description = "List of public Elastic IPs created for NAT Gateways"
  value       = aws_nat_gateway.nat[*].public_ip
}

# Route Table Outputs
output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "List of IDs of private route tables"
  value       = aws_route_table.private[*].id
}

output "database_route_table_id" {
  description = "ID of the database route table"
  value       = aws_route_table.database.id
}

# Network ACL Outputs
output "public_network_acl_id" {
  description = "ID of the public network ACL"
  value       = aws_network_acl.public.id
}

output "private_network_acl_id" {
  description = "ID of the private network ACL"
  value       = aws_network_acl.private.id
}

output "database_network_acl_id" {
  description = "ID of the database network ACL"
  value       = aws_network_acl.database.id
}

# Internet Gateway Output
output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.igw.id
}

# Target Group Outputs
output "api_gateway_target_group_arn" {
  description = "ARN of the API Gateway target group"
  value       = aws_lb_target_group.api_gateway.arn
}

output "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  value       = aws_lb_target_group.frontend.arn
}

# Listener Outputs
output "http_listener_arn" {
  description = "ARN of the HTTP listener"
  value       = aws_lb_listener.http.arn
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener"
  value       = aws_lb_listener.https.arn
}

# Network Interface Outputs
output "nat_network_interface_ids" {
  description = "List of network interface IDs for the NAT Gateways"
  value       = aws_nat_gateway.nat[*].network_interface_id
}

# VPC Endpoint Outputs
output "s3_vpc_endpoint_id" {
  description = "ID of the S3 VPC Endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "dynamodb_vpc_endpoint_id" {
  description = "ID of the DynamoDB VPC Endpoint"
  value       = aws_vpc_endpoint.dynamodb.id
}