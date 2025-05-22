# Network Module Outputs for MCA Application Processing System
# This file defines output values from the network module that are consumed by other modules,
# including VPC IDs, subnet IDs, security group IDs, and load balancer ARNs.

# ---------------------------------------------------------------------------------------------------------------------
# VPC OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_arn" {
  description = "ARN of the VPC"
  value       = aws_vpc.main.arn
}

# ---------------------------------------------------------------------------------------------------------------------
# SUBNET OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "List of database subnet IDs"
  value       = aws_subnet.database[*].id
}

output "public_subnet_cidrs" {
  description = "List of public subnet CIDR blocks"
  value       = aws_subnet.public[*].cidr_block
}

output "private_subnet_cidrs" {
  description = "List of private subnet CIDR blocks"
  value       = aws_subnet.private[*].cidr_block
}

output "database_subnet_cidrs" {
  description = "List of database subnet CIDR blocks"
  value       = aws_subnet.database[*].cidr_block
}

output "database_subnet_group_name" {
  description = "Name of the database subnet group"
  value       = aws_db_subnet_group.database.name
}

output "database_subnet_group_id" {
  description = "ID of the database subnet group"
  value       = aws_db_subnet_group.database.id
}

# ---------------------------------------------------------------------------------------------------------------------
# INTERNET GATEWAY OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "internet_gateway_id" {
  description = "ID of the internet gateway"
  value       = aws_internet_gateway.main.id
}

# ---------------------------------------------------------------------------------------------------------------------
# NAT GATEWAY OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.nat[*].id
}

output "nat_gateway_public_ips" {
  description = "List of public Elastic IPs created for NAT Gateways"
  value       = aws_nat_gateway.nat[*].public_ip
}

# ---------------------------------------------------------------------------------------------------------------------
# ROUTE TABLE OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "List of private route table IDs"
  value       = aws_route_table.private[*].id
}

output "database_route_table_ids" {
  description = "List of database route table IDs"
  value       = aws_route_table.database[*].id
}

# ---------------------------------------------------------------------------------------------------------------------
# VPC ENDPOINT OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "s3_vpc_endpoint_id" {
  description = "ID of the S3 VPC endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "ecr_api_vpc_endpoint_id" {
  description = "ID of the ECR API VPC endpoint"
  value       = aws_vpc_endpoint.ecr_api.id
}

output "ecr_dkr_vpc_endpoint_id" {
  description = "ID of the ECR Docker VPC endpoint"
  value       = aws_vpc_endpoint.ecr_dkr.id
}

output "logs_vpc_endpoint_id" {
  description = "ID of the CloudWatch Logs VPC endpoint"
  value       = aws_vpc_endpoint.logs.id
}

# ---------------------------------------------------------------------------------------------------------------------
# SECURITY GROUP OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
# Frontend Security Group
output "frontend_security_group_id" {
  description = "ID of the frontend security group"
  value       = aws_security_group.frontend.id
}

# API Gateway Security Group
output "api_gateway_security_group_id" {
  description = "ID of the API Gateway security group"
  value       = aws_security_group.api_gateway.id
}

# Microservices Security Group
output "microservices_security_group_id" {
  description = "ID of the base microservices security group"
  value       = aws_security_group.microservices.id
}

# Email Service Security Group
output "email_service_security_group_id" {
  description = "ID of the Email Service security group"
  value       = aws_security_group.email_service.id
}

# Document Service Security Group
output "document_service_security_group_id" {
  description = "ID of the Document Service security group"
  value       = aws_security_group.document_service.id
}

# OCR Service Security Group
output "ocr_service_security_group_id" {
  description = "ID of the OCR Service security group"
  value       = aws_security_group.ocr_service.id
}

# Data Service Security Group
output "data_service_security_group_id" {
  description = "ID of the Data Service security group"
  value       = aws_security_group.data_service.id
}

# Notification Service Security Group
output "notification_service_security_group_id" {
  description = "ID of the Notification Service security group"
  value       = aws_security_group.notification_service.id
}

# PostgreSQL Security Group
output "postgres_security_group_id" {
  description = "ID of the PostgreSQL security group"
  value       = aws_security_group.postgres.id
}

# RabbitMQ Security Group
output "rabbitmq_security_group_id" {
  description = "ID of the RabbitMQ security group"
  value       = aws_security_group.rabbitmq.id
}

# Redis Security Group
output "redis_security_group_id" {
  description = "ID of the Redis security group"
  value       = aws_security_group.redis.id
}

# Load Balancer Security Groups
output "frontend_alb_security_group_id" {
  description = "ID of the frontend ALB security group"
  value       = aws_security_group.frontend_alb_sg.id
}

output "api_alb_security_group_id" {
  description = "ID of the API ALB security group"
  value       = aws_security_group.api_alb_sg.id
}

# ---------------------------------------------------------------------------------------------------------------------
# LOAD BALANCER OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
# Frontend ALB
output "frontend_alb_id" {
  description = "ID of the frontend Application Load Balancer"
  value       = aws_lb.frontend_alb.id
}

output "frontend_alb_arn" {
  description = "ARN of the frontend Application Load Balancer"
  value       = aws_lb.frontend_alb.arn
}

output "frontend_alb_dns_name" {
  description = "DNS name of the frontend Application Load Balancer"
  value       = aws_lb.frontend_alb.dns_name
}

output "frontend_alb_zone_id" {
  description = "Zone ID of the frontend Application Load Balancer"
  value       = aws_lb.frontend_alb.zone_id
}

output "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  value       = aws_lb_target_group.frontend_tg.arn
}

# API ALB
output "api_alb_id" {
  description = "ID of the API Application Load Balancer"
  value       = aws_lb.api_alb.id
}

output "api_alb_arn" {
  description = "ARN of the API Application Load Balancer"
  value       = aws_lb.api_alb.arn
}

output "api_alb_dns_name" {
  description = "DNS name of the API Application Load Balancer"
  value       = aws_lb.api_alb.dns_name
}

output "api_alb_zone_id" {
  description = "Zone ID of the API Application Load Balancer"
  value       = aws_lb.api_alb.zone_id
}

output "api_target_group_arn" {
  description = "ARN of the API target group"
  value       = aws_lb_target_group.api_tg.arn
}

# ---------------------------------------------------------------------------------------------------------------------
# KUBERNETES SPECIFIC OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "kubernetes_subnet_ids" {
  description = "List of subnet IDs suitable for Kubernetes deployment (private subnets)"
  value       = aws_subnet.private[*].id
}

output "kubernetes_subnet_cidrs" {
  description = "List of subnet CIDR blocks suitable for Kubernetes deployment"
  value       = aws_subnet.private[*].cidr_block
}

output "kubernetes_cluster_name" {
  description = "Name to use for Kubernetes cluster tagging"
  value       = var.environment
}

# ---------------------------------------------------------------------------------------------------------------------
# NETWORK FLOW LOGS OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------
output "vpc_flow_log_id" {
  description = "ID of the VPC Flow Log"
  value       = aws_flow_log.vpc_flow_logs.id
}

output "vpc_flow_log_destination" {
  description = "Destination ARN of the VPC Flow Log"
  value       = var.flow_log_destination_arn
}