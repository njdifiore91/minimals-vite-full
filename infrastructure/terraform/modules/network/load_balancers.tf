# Load Balancer configurations for MCA Application Processing System
# This file defines Application Load Balancers, listeners, target groups, and health checks
# for the frontend and backend services.

# Variables for the module
variable "environment" {
  description = "Deployment environment (e.g., development, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where resources will be created"
  type        = string
}

variable "public_subnets" {
  description = "List of public subnet IDs for the load balancers"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS listeners"
  type        = string
}

variable "access_logs_bucket" {
  description = "S3 bucket name for ALB access logs"
  type        = string
  default     = ""
}

variable "enable_access_logs" {
  description = "Enable access logs for the load balancers"
  type        = bool
  default     = true
}

variable "frontend_domain" {
  description = "Domain name for the frontend service"
  type        = string
}

variable "api_domain" {
  description = "Domain name for the API gateway"
  type        = string
}

variable "frontend_health_check_path" {
  description = "Health check path for frontend service"
  type        = string
  default     = "/"
}

variable "api_health_check_path" {
  description = "Health check path for API gateway"
  type        = string
  default     = "/status"
}

variable "frontend_health_check_interval" {
  description = "Health check interval for frontend service in seconds"
  type        = number
  default     = 30
}

variable "api_health_check_interval" {
  description = "Health check interval for API gateway in seconds"
  type        = number
  default     = 15
}

variable "frontend_health_check_timeout" {
  description = "Health check timeout for frontend service in seconds"
  type        = number
  default     = 5
}

variable "api_health_check_timeout" {
  description = "Health check timeout for API gateway in seconds"
  type        = number
  default     = 5
}

variable "frontend_health_check_healthy_threshold" {
  description = "Number of consecutive health check successes required for frontend service"
  type        = number
  default     = 2
}

variable "api_health_check_healthy_threshold" {
  description = "Number of consecutive health check successes required for API gateway"
  type        = number
  default     = 2
}

variable "frontend_health_check_unhealthy_threshold" {
  description = "Number of consecutive health check failures required for frontend service"
  type        = number
  default     = 2
}

variable "api_health_check_unhealthy_threshold" {
  description = "Number of consecutive health check failures required for API gateway"
  type        = number
  default     = 2
}

# Security group for frontend load balancer
resource "aws_security_group" "frontend_alb_sg" {
  name        = "${var.environment}-frontend-alb-sg"
  description = "Security group for frontend Application Load Balancer"
  vpc_id      = var.vpc_id

  # Allow HTTP from anywhere (will be redirected to HTTPS)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP traffic"
  }

  # Allow HTTPS from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS traffic"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.environment}-frontend-alb-sg"
    Environment = var.environment
    Terraform   = "true"
  }
}

# Security group for API gateway load balancer
resource "aws_security_group" "api_alb_sg" {
  name        = "${var.environment}-api-alb-sg"
  description = "Security group for API Gateway Application Load Balancer"
  vpc_id      = var.vpc_id

  # Allow HTTP from anywhere (will be redirected to HTTPS)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP traffic"
  }

  # Allow HTTPS from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS traffic"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.environment}-api-alb-sg"
    Environment = var.environment
    Terraform   = "true"
  }
}

# Frontend Application Load Balancer
resource "aws_lb" "frontend_alb" {
  name               = "${var.environment}-frontend-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.frontend_alb_sg.id]
  subnets            = var.public_subnets
  idle_timeout       = 60
  ip_address_type    = "ipv4"

  # Enable access logs if specified
  dynamic "access_logs" {
    for_each = var.enable_access_logs && var.access_logs_bucket != "" ? [1] : []
    content {
      bucket  = var.access_logs_bucket
      prefix  = "${var.environment}-frontend-alb"
      enabled = true
    }
  }

  tags = {
    Name        = "${var.environment}-frontend-alb"
    Environment = var.environment
    Terraform   = "true"
  }
}

# API Gateway Application Load Balancer
resource "aws_lb" "api_alb" {
  name               = "${var.environment}-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.api_alb_sg.id]
  subnets            = var.public_subnets
  idle_timeout       = 60
  ip_address_type    = "ipv4"

  # Enable access logs if specified
  dynamic "access_logs" {
    for_each = var.enable_access_logs && var.access_logs_bucket != "" ? [1] : []
    content {
      bucket  = var.access_logs_bucket
      prefix  = "${var.environment}-api-alb"
      enabled = true
    }
  }

  tags = {
    Name        = "${var.environment}-api-alb"
    Environment = var.environment
    Terraform   = "true"
  }
}

# Target group for frontend service
resource "aws_lb_target_group" "frontend_tg" {
  name     = "${var.environment}-frontend-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    interval            = var.frontend_health_check_interval
    path                = var.frontend_health_check_path
    port                = "traffic-port"
    healthy_threshold   = var.frontend_health_check_healthy_threshold
    unhealthy_threshold = var.frontend_health_check_unhealthy_threshold
    timeout             = var.frontend_health_check_timeout
    protocol            = "HTTP"
    matcher             = "200-299"
  }

  tags = {
    Name        = "${var.environment}-frontend-tg"
    Environment = var.environment
    Terraform   = "true"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Target group for API gateway
resource "aws_lb_target_group" "api_tg" {
  name     = "${var.environment}-api-tg"
  port     = 8000 # Kong API Gateway default port
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    interval            = var.api_health_check_interval
    path                = var.api_health_check_path
    port                = "traffic-port"
    healthy_threshold   = var.api_health_check_healthy_threshold
    unhealthy_threshold = var.api_health_check_unhealthy_threshold
    timeout             = var.api_health_check_timeout
    protocol            = "HTTP"
    matcher             = "200-299"
  }

  tags = {
    Name        = "${var.environment}-api-tg"
    Environment = var.environment
    Terraform   = "true"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# HTTP listener for frontend ALB - redirects to HTTPS
resource "aws_lb_listener" "frontend_http" {
  load_balancer_arn = aws_lb.frontend_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS listener for frontend ALB
resource "aws_lb_listener" "frontend_https" {
  load_balancer_arn = aws_lb.frontend_alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # TLS 1.3 and 1.2 with strong ciphers
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend_tg.arn
  }
}

# HTTP listener for API ALB - redirects to HTTPS
resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS listener for API ALB
resource "aws_lb_listener" "api_https" {
  load_balancer_arn = aws_lb.api_alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # TLS 1.3 and 1.2 with strong ciphers
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_tg.arn
  }
}

# Outputs
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

output "frontend_security_group_id" {
  description = "ID of the frontend ALB security group"
  value       = aws_security_group.frontend_alb_sg.id
}

output "api_security_group_id" {
  description = "ID of the API ALB security group"
  value       = aws_security_group.api_alb_sg.id
}