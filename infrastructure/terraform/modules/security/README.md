# Security Module

This Terraform module implements security infrastructure for the MCA Application Processing System. It provides resources for securing the application, including IAM roles, security groups, KMS keys, JWT keys, and WAF configurations.

## Features

- JWT key generation for authentication
- KMS key for data encryption (PII fields, etc.)
- Security groups for API Gateway, microservices, and database
- IAM roles for services with least-privilege permissions
- WAF Web ACL for API protection with rate limiting and IP whitelisting

## Usage

```hcl
module "security" {
  source = "../modules/security"

  environment = "production"
  vpc_id      = module.network.vpc_id
  
  # Optional: Configure IP whitelist for admin endpoints
  ip_whitelist = ["192.168.1.0/24", "10.0.0.1/32"]
  
  # Optional: Configure KMS key administrators
  kms_key_administrators = ["arn:aws:iam::123456789012:user/admin"]
  
  # Additional resource tags
  resource_tags = {
    CostCenter = "MCA-Processing"
    Owner      = "Security-Team"
  }
}
```

## Requirements

| Name | Version |
|------|--------|
| terraform | >= 1.12.0 |
| aws | >= 5.0.0 |
| tls | >= 4.0.0 |

## Providers

| Name | Version |
|------|--------|
| aws | >= 5.0.0 |
| tls | >= 4.0.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | Deployment environment (development, staging, production) | `string` | n/a | yes |
| vpc_id | ID of the VPC where security groups will be created | `string` | n/a | yes |
| aws_region | AWS region for all resources | `string` | `"us-east-1"` | no |
| resource_tags | Additional tags to apply to all resources | `map(string)` | `{}` | no |
| kms_key_administrators | List of IAM ARNs that can administer the KMS keys | `list(string)` | `[]` | no |
| jwt_issuer | Issuer claim for JWT tokens | `string` | `"dollarfunding-mca"` | no |
| jwt_audience | Audience claim for JWT tokens | `string` | `"mca-application-api"` | no |
| enable_waf | Enable AWS WAF for API Gateway protection | `bool` | `true` | no |
| ip_whitelist | List of IP addresses/ranges allowed to access admin endpoints | `list(string)` | `[]` | no |
| enable_field_encryption | Enable field-level encryption for PII data | `bool` | `true` | no |
| enable_malware_scanning | Enable malware scanning for document uploads | `bool` | `true` | no |

## Outputs

| Name | Description |
|------|-------------|
| jwt_public_key | Public key for JWT token verification |
| jwt_private_key | Private key for JWT token signing |
| kms_key_id | KMS key ID for data encryption |
| kms_key_arn | KMS key ARN for data encryption |
| api_security_group_id | Security group ID for API Gateway |
| service_security_group_id | Security group ID for microservices |
| database_security_group_id | Security group ID for database access |
| service_role_arns | Map of service names to their IAM role ARNs |
| security_settings | Security settings based on environment |
| waf_web_acl_arn | WAF Web ACL ARN for API protection |

## Security Considerations

- JWT tokens use RS256 asymmetric key signing for enhanced security
- KMS keys are used for field-level encryption of PII data
- Security groups implement the principle of least privilege
- WAF protects against common web exploits and DDoS attacks
- IP whitelisting restricts access to admin endpoints

## Notes

- This module assumes that a VPC has already been created
- The JWT keys module is a dependency that must be available
- For production environments, it's recommended to enable WAF and configure IP whitelisting