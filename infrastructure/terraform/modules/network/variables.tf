# Network Module Variables
# This file defines all input variables for the network module including VPC CIDR blocks,
# subnet configurations, availability zones, and environment settings.

#--------------------------------------------------------------
# VPC Configuration Variables
#--------------------------------------------------------------
variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "The vpc_cidr value must be a valid CIDR notation."
  }
}

variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
}

variable "enable_dns_hostnames" {
  description = "Enable DNS hostnames in the VPC"
  type        = bool
  default     = true
}

variable "enable_dns_support" {
  description = "Enable DNS support in the VPC"
  type        = bool
  default     = true
}

#--------------------------------------------------------------
# Subnet Configuration Variables
#--------------------------------------------------------------
variable "public_subnets" {
  description = "A list of public subnet CIDR blocks"
  type        = list(string)
  default     = []

  validation {
    condition     = length([for s in var.public_subnets : s if can(cidrnetmask(s))]) == length(var.public_subnets)
    error_message = "All public_subnets values must be valid CIDR notations."
  }
}

variable "private_subnets" {
  description = "A list of private subnet CIDR blocks"
  type        = list(string)
  default     = []

  validation {
    condition     = length([for s in var.private_subnets : s if can(cidrnetmask(s))]) == length(var.private_subnets)
    error_message = "All private_subnets values must be valid CIDR notations."
  }
}

variable "database_subnets" {
  description = "A list of database subnet CIDR blocks"
  type        = list(string)
  default     = []

  validation {
    condition     = length([for s in var.database_subnets : s if can(cidrnetmask(s))]) == length(var.database_subnets)
    error_message = "All database_subnets values must be valid CIDR notations."
  }
}

variable "create_database_subnet_group" {
  description = "Controls if database subnet group should be created"
  type        = bool
  default     = true
}

variable "database_subnet_group_name" {
  description = "Name of database subnet group"
  type        = string
  default     = null
}

variable "create_database_subnet_route_table" {
  description = "Controls if separate route table for database should be created"
  type        = bool
  default     = true
}

variable "create_database_internet_gateway_route" {
  description = "Controls if an internet gateway route for public database access should be created"
  type        = bool
  default     = false
}

variable "create_database_nat_gateway_route" {
  description = "Controls if a NAT gateway route should be created for private database subnets"
  type        = bool
  default     = true
}

#--------------------------------------------------------------
# Availability Zone Configuration
#--------------------------------------------------------------
variable "azs" {
  description = "A list of availability zones in the region"
  type        = list(string)
  default     = []
}

variable "single_nat_gateway" {
  description = "Should be true if you want to provision a single shared NAT Gateway across all of your private networks"
  type        = bool
  default     = false
}

variable "one_nat_gateway_per_az" {
  description = "Should be true if you want only one NAT Gateway per availability zone"
  type        = bool
  default     = true
}

variable "reuse_nat_ips" {
  description = "Should be true if you don't want EIPs to be created for your NAT Gateways and will instead pass them in via the 'external_nat_ip_ids' variable"
  type        = bool
  default     = false
}

variable "external_nat_ip_ids" {
  description = "List of EIP IDs to be assigned to the NAT Gateways (used in combination with reuse_nat_ips)"
  type        = list(string)
  default     = []
}

#--------------------------------------------------------------
# Network Security Configuration
#--------------------------------------------------------------
variable "enable_flow_log" {
  description = "Whether or not to enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_log_destination_type" {
  description = "Type of flow log destination. Can be s3 or cloud-watch-logs"
  type        = string
  default     = "cloud-watch-logs"
  validation {
    condition     = contains(["s3", "cloud-watch-logs"], var.flow_log_destination_type)
    error_message = "Flow log destination type must be either 's3' or 'cloud-watch-logs'."
  }
}

variable "flow_log_destination_arn" {
  description = "The ARN of the CloudWatch log group or S3 bucket where VPC Flow Logs will be pushed"
  type        = string
  default     = ""
}

variable "flow_log_traffic_type" {
  description = "The type of traffic to capture. Valid values: ACCEPT, REJECT, ALL"
  type        = string
  default     = "ALL"
  validation {
    condition     = contains(["ACCEPT", "REJECT", "ALL"], var.flow_log_traffic_type)
    error_message = "Flow log traffic type must be one of 'ACCEPT', 'REJECT', or 'ALL'."
  }
}

variable "flow_log_max_aggregation_interval" {
  description = "The maximum interval of time during which a flow of packets is captured and aggregated into a flow log record. Valid values: 60 seconds (1 minute) or 600 seconds (10 minutes)"
  type        = number
  default     = 600
  validation {
    condition     = contains([60, 600], var.flow_log_max_aggregation_interval)
    error_message = "Flow log max aggregation interval must be either 60 or 600 seconds."
  }
}

#--------------------------------------------------------------
# Network Segmentation and Security Groups
#--------------------------------------------------------------
variable "create_network_acls" {
  description = "Controls if network ACLs should be created"
  type        = bool
  default     = false
}

variable "public_dedicated_network_acl" {
  description = "Whether to use dedicated network ACL (not default) and custom rules for public subnets"
  type        = bool
  default     = false
}

variable "private_dedicated_network_acl" {
  description = "Whether to use dedicated network ACL (not default) and custom rules for private subnets"
  type        = bool
  default     = false
}

variable "database_dedicated_network_acl" {
  description = "Whether to use dedicated network ACL (not default) and custom rules for database subnets"
  type        = bool
  default     = false
}

variable "public_inbound_acl_rules" {
  description = "Public subnets inbound network ACLs"
  type        = list(map(string))
  default     = [
    {
      rule_number = 100
      rule_action = "allow"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_block  = "0.0.0.0/0"
    },
  ]
}

variable "public_outbound_acl_rules" {
  description = "Public subnets outbound network ACLs"
  type        = list(map(string))
  default     = [
    {
      rule_number = 100
      rule_action = "allow"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_block  = "0.0.0.0/0"
    },
  ]
}

variable "private_inbound_acl_rules" {
  description = "Private subnets inbound network ACLs"
  type        = list(map(string))
  default     = [
    {
      rule_number = 100
      rule_action = "allow"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_block  = "0.0.0.0/0"
    },
  ]
}

variable "private_outbound_acl_rules" {
  description = "Private subnets outbound network ACLs"
  type        = list(map(string))
  default     = [
    {
      rule_number = 100
      rule_action = "allow"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_block  = "0.0.0.0/0"
    },
  ]
}

variable "database_inbound_acl_rules" {
  description = "Database subnets inbound network ACLs"
  type        = list(map(string))
  default     = [
    {
      rule_number = 100
      rule_action = "allow"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_block  = "0.0.0.0/0"
    },
  ]
}

variable "database_outbound_acl_rules" {
  description = "Database subnets outbound network ACLs"
  type        = list(map(string))
  default     = [
    {
      rule_number = 100
      rule_action = "allow"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_block  = "0.0.0.0/0"
    },
  ]
}

#--------------------------------------------------------------
# Service Endpoints Configuration
#--------------------------------------------------------------
variable "enable_s3_endpoint" {
  description = "Should be true if you want to provision an S3 endpoint to the VPC"
  type        = bool
  default     = true
}

variable "enable_dynamodb_endpoint" {
  description = "Should be true if you want to provision a DynamoDB endpoint to the VPC"
  type        = bool
  default     = false
}

variable "enable_ssm_endpoint" {
  description = "Should be true if you want to provision an SSM endpoint to the VPC"
  type        = bool
  default     = false
}

variable "enable_ssmmessages_endpoint" {
  description = "Should be true if you want to provision an SSMMESSAGES endpoint to the VPC"
  type        = bool
  default     = false
}

variable "enable_ec2_endpoint" {
  description = "Should be true if you want to provision an EC2 endpoint to the VPC"
  type        = bool
  default     = false
}

variable "enable_ec2messages_endpoint" {
  description = "Should be true if you want to provision an EC2MESSAGES endpoint to the VPC"
  type        = bool
  default     = false
}

#--------------------------------------------------------------
# Environment and Tagging Variables
#--------------------------------------------------------------
variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of 'development', 'staging', or 'production'."
  }
}

variable "project" {
  description = "Project name for resource tagging"
  type        = string
  default     = "mca"
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "vpc_tags" {
  description = "Additional tags for the VPC"
  type        = map(string)
  default     = {}
}

variable "public_subnet_tags" {
  description = "Additional tags for the public subnets"
  type        = map(string)
  default     = {}
}

variable "private_subnet_tags" {
  description = "Additional tags for the private subnets"
  type        = map(string)
  default     = {}
}

variable "database_subnet_tags" {
  description = "Additional tags for the database subnets"
  type        = map(string)
  default     = {}
}

variable "public_route_table_tags" {
  description = "Additional tags for the public route tables"
  type        = map(string)
  default     = {}
}

variable "private_route_table_tags" {
  description = "Additional tags for the private route tables"
  type        = map(string)
  default     = {}
}

variable "database_route_table_tags" {
  description = "Additional tags for the database route tables"
  type        = map(string)
  default     = {}
}

variable "igw_tags" {
  description = "Additional tags for the internet gateway"
  type        = map(string)
  default     = {}
}

variable "nat_gateway_tags" {
  description = "Additional tags for the NAT gateways"
  type        = map(string)
  default     = {}
}

variable "nat_eip_tags" {
  description = "Additional tags for the NAT EIP"
  type        = map(string)
  default     = {}
}

#--------------------------------------------------------------
# TLS and Security Configuration
#--------------------------------------------------------------
variable "enable_tls_endpoints" {
  description = "Whether to enable TLS for VPC endpoints"
  type        = bool
  default     = true
}

variable "tls_security_policy" {
  description = "The security policy for TLS connections (e.g., TLS-1-2, TLS-1-0)"
  type        = string
  default     = "TLS-1-2"
  validation {
    condition     = contains(["TLS-1-0", "TLS-1-1", "TLS-1-2", "TLS-1-3"], var.tls_security_policy)
    error_message = "TLS security policy must be one of 'TLS-1-0', 'TLS-1-1', 'TLS-1-2', or 'TLS-1-3'."
  }
}

variable "enable_network_firewall" {
  description = "Whether to enable AWS Network Firewall"
  type        = bool
  default     = false
}

variable "network_firewall_policy" {
  description = "The ARN of the Network Firewall policy to use"
  type        = string
  default     = ""
}

#--------------------------------------------------------------
# Multi-Region Configuration
#--------------------------------------------------------------
variable "region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "enable_cross_region_vpc_peering" {
  description = "Whether to enable cross-region VPC peering"
  type        = bool
  default     = false
}

variable "peer_vpc_ids" {
  description = "List of VPC IDs to peer with in other regions"
  type        = list(string)
  default     = []
}

variable "peer_region_names" {
  description = "List of region names corresponding to peer_vpc_ids"
  type        = list(string)
  default     = []
}