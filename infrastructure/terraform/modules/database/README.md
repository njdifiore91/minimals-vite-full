# PostgreSQL Database Monitoring Module

This Terraform module configures comprehensive monitoring and alerting for PostgreSQL databases using CloudWatch and Datadog integration for the MCA Application Processing System.

## Features

- Enhanced RDS monitoring with 15-second metrics collection
- Performance Insights configuration for query analysis
- CloudWatch Alarms for critical database metrics
- CloudWatch Dashboard for database performance visualization
- CloudWatch Logs configuration for PostgreSQL logs
- Datadog integration for advanced monitoring and alerting

## Usage

```hcl
module "database_monitoring" {
  source = "./modules/database"

  prefix                = "mca"
  db_cluster_identifier = "mca-postgres-cluster"
  aws_region            = "us-east-1"
  
  # CloudWatch Alarms configuration
  create_cloudwatch_alarms  = true
  create_cloudwatch_dashboard = true
  critical_alarm_actions    = ["arn:aws:sns:us-east-1:123456789012:critical-alarms"]
  warning_alarm_actions     = ["arn:aws:sns:us-east-1:123456789012:warning-alarms"]
  
  # Datadog integration (optional)
  enable_datadog_integration = true
  datadog_api_key           = var.datadog_api_key
  datadog_app_key           = var.datadog_app_key
  environment               = "production"
  
  tags = {
    Environment = "production"
    Project     = "MCA"
  }
}
```

## Requirements

| Name | Version |
|------|--------|
| terraform | >= 1.0.0 |
| aws | >= 4.0.0 |
| datadog | >= 3.20.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| prefix | Prefix to be used for resource naming | `string` | `"mca"` | no |
| tags | A map of tags to add to all resources | `map(string)` | `{}` | no |
| aws_region | AWS region where resources will be created | `string` | `"us-east-1"` | no |
| db_cluster_identifier | The identifier of the DB cluster | `string` | n/a | yes |
| db_instance_identifier | The identifier of the DB instance (for read replica monitoring) | `string` | `""` | no |
| is_read_replica | Whether the DB instance is a read replica | `bool` | `false` | no |
| max_connections | Maximum number of database connections allowed | `number` | `100` | no |
| create_cloudwatch_alarms | Whether to create CloudWatch alarms | `bool` | `true` | no |
| create_cloudwatch_dashboard | Whether to create CloudWatch dashboard | `bool` | `true` | no |
| critical_alarm_actions | List of ARNs to notify when a critical alarm transitions to ALARM state | `list(string)` | `[]` | no |
| warning_alarm_actions | List of ARNs to notify when a warning alarm transitions to ALARM state | `list(string)` | `[]` | no |
| ok_alarm_actions | List of ARNs to notify when an alarm transitions to OK state | `list(string)` | `[]` | no |
| enable_datadog_integration | Whether to enable Datadog integration | `bool` | `false` | no |
| datadog_api_key | Datadog API key | `string` | `""` | no |
| datadog_app_key | Datadog application key | `string` | `""` | no |
| datadog_api_url | Datadog API URL | `string` | `"https://api.datadoghq.com/"` | no |
| environment | Environment name (e.g., dev, staging, prod) | `string` | `"dev"` | no |

## Outputs

| Name | Description |
|------|-------------|
| monitoring_role_arn | ARN of the RDS enhanced monitoring IAM role |
| monitoring_role_name | Name of the RDS enhanced monitoring IAM role |
| cloudwatch_log_groups | Map of CloudWatch Log Groups created for RDS logs |
| cloudwatch_alarms | Map of CloudWatch Alarms created for RDS monitoring |
| cloudwatch_dashboard_name | Name of the CloudWatch Dashboard created for RDS monitoring |
| datadog_monitors | Map of Datadog Monitors created for RDS monitoring |
| datadog_dashboard_id | ID of the Datadog Dashboard created for RDS monitoring |
| monitoring_configuration | Monitoring configuration for RDS instances |

## Notes

- The module creates an IAM role for RDS enhanced monitoring
- CloudWatch alarms require SNS topics to be created separately
- Datadog integration requires valid API and application keys
- For read replica monitoring, set `is_read_replica = true` and provide `db_instance_identifier`