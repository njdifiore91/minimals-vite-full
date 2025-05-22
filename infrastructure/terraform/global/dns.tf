# =============================================================================
# Global DNS Configuration for MCA Application Processing System
# =============================================================================
# This file defines the global DNS zones and records that are shared across all
# environments. It provisions the primary domain zones, global DNS records, and
# DNS delegation configurations needed for the application's domain structure.

# -----------------------------------------------------------------------------
# AWS Provider Configuration
# -----------------------------------------------------------------------------

provider "aws" {
  alias = "route53"
  # The actual provider configuration is inherited from the parent module
}

# -----------------------------------------------------------------------------
# Primary Domain Zone
# -----------------------------------------------------------------------------

# Primary domain zone for dollarfunding.com
resource "aws_route53_zone" "primary" {
  provider = aws.route53
  name     = "dollarfunding.com"
  
  comment = "Primary domain zone for Dollar Funding MCA Application Processing System"
  
  tags = {
    Name        = "dollarfunding.com"
    Environment = "global"
    Terraform   = "true"
    Service     = "dns"
  }
}

# -----------------------------------------------------------------------------
# Environment Subdomain Delegation
# -----------------------------------------------------------------------------

# Development environment subdomain delegation
resource "aws_route53_zone" "development" {
  provider = aws.route53
  name     = "dev.dollarfunding.com"
  
  comment = "Development environment subdomain for MCA Application Processing System"
  
  tags = {
    Name        = "dev.dollarfunding.com"
    Environment = "development"
    Terraform   = "true"
    Service     = "dns"
  }
}

# NS record for development subdomain delegation
resource "aws_route53_record" "development_ns" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "dev.dollarfunding.com"
  type     = "NS"
  ttl      = "300"
  
  records = aws_route53_zone.development.name_servers
}

# Staging environment subdomain delegation
resource "aws_route53_zone" "staging" {
  provider = aws.route53
  name     = "staging.dollarfunding.com"
  
  comment = "Staging environment subdomain for MCA Application Processing System"
  
  tags = {
    Name        = "staging.dollarfunding.com"
    Environment = "staging"
    Terraform   = "true"
    Service     = "dns"
  }
}

# NS record for staging subdomain delegation
resource "aws_route53_record" "staging_ns" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "staging.dollarfunding.com"
  type     = "NS"
  ttl      = "300"
  
  records = aws_route53_zone.staging.name_servers
}

# Production environment subdomain delegation
resource "aws_route53_zone" "production" {
  provider = aws.route53
  name     = "app.dollarfunding.com"
  
  comment = "Production environment subdomain for MCA Application Processing System"
  
  tags = {
    Name        = "app.dollarfunding.com"
    Environment = "production"
    Terraform   = "true"
    Service     = "dns"
  }
}

# NS record for production subdomain delegation
resource "aws_route53_record" "production_ns" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "app.dollarfunding.com"
  type     = "NS"
  ttl      = "300"
  
  records = aws_route53_zone.production.name_servers
}

# -----------------------------------------------------------------------------
# Global DNS Records for Shared Services
# -----------------------------------------------------------------------------

# Email service MX records
resource "aws_route53_record" "mx_records" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "dollarfunding.com"
  type     = "MX"
  ttl      = "3600"
  
  records = [
    "10 mail.dollarfunding.com",
    "20 backup-mail.dollarfunding.com"
  ]
}

# Submissions email for MCA applications
resource "aws_route53_record" "submissions_mx" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "submissions.dollarfunding.com"
  type     = "MX"
  ttl      = "3600"
  
  records = [
    "10 submissions-mail.dollarfunding.com"
  ]
}

# SPF record for email authentication
resource "aws_route53_record" "spf_record" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "dollarfunding.com"
  type     = "TXT"
  ttl      = "3600"
  
  records = [
    "v=spf1 include:_spf.dollarfunding.com ~all"
  ]
}

# DKIM record for email authentication
resource "aws_route53_record" "dkim_record" {
  provider = aws.route53
  zone_id  = aws_route53_zone.primary.zone_id
  name     = "dkim._domainkey.dollarfunding.com"
  type     = "TXT"
  ttl      = "3600"
  
  records = [
    "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCrLHiExVd55zd/IQ/J/mRwSRMAocV/hMB3jXwaHH36d9NaVynQFYV8NaWi69c1veUtRzGt7yAioXqLj7Z4TeEUoOLgrKsn8YnckGs9i3B3tVFB+Ch/4mPhXWiNfNdynHWBcPcbJ8kjEQ2U8y78dHZj1YeRXXVvWob2OaKynO8/lQIDAQAB;"
  ]
}

# -----------------------------------------------------------------------------
# Regional Failover Configuration
# -----------------------------------------------------------------------------

# Primary region health check for failover
resource "aws_route53_health_check" "primary_region" {
  provider          = aws.route53
  fqdn              = "health.app.dollarfunding.com"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30
  
  tags = {
    Name        = "primary-region-health-check"
    Environment = "global"
    Terraform   = "true"
    Service     = "dns"
  }
}

# Secondary region health check for failover
resource "aws_route53_health_check" "secondary_region" {
  provider          = aws.route53
  fqdn              = "health-dr.app.dollarfunding.com"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30
  
  tags = {
    Name        = "secondary-region-health-check"
    Environment = "global"
    Terraform   = "true"
    Service     = "dns"
  }
}

# -----------------------------------------------------------------------------
# SSL Certificate Validation Records
# -----------------------------------------------------------------------------

# This section defines a data source for ACM certificates that need DNS validation
# The actual certificate validation records will be created in environment-specific
# Terraform configurations using the zones defined in this file

# Output the zone IDs for use in other Terraform configurations
output "primary_zone_id" {
  description = "The ID of the primary DNS zone"
  value       = aws_route53_zone.primary.zone_id
}

output "development_zone_id" {
  description = "The ID of the development DNS zone"
  value       = aws_route53_zone.development.zone_id
}

output "staging_zone_id" {
  description = "The ID of the staging DNS zone"
  value       = aws_route53_zone.staging.zone_id
}

output "production_zone_id" {
  description = "The ID of the production DNS zone"
  value       = aws_route53_zone.production.zone_id
}