# PostgreSQL Database Monitoring Configuration
# This file configures comprehensive monitoring and alerting for PostgreSQL databases
# using CloudWatch and Datadog integration for the MCA Application Processing System

#--------------------------------------------------------------
# Enhanced RDS Monitoring Configuration
#--------------------------------------------------------------

# IAM role for enhanced RDS monitoring with 15-second metrics collection
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name_prefix        = "rds-enhanced-monitoring-"
  assume_role_policy = data.aws_iam_policy_document.rds_enhanced_monitoring.json

  tags = merge(
    var.tags,
    {
      Name = "${var.prefix}-rds-monitoring-role"
    }
  )
}

# IAM policy document for the enhanced monitoring role
data "aws_iam_policy_document" "rds_enhanced_monitoring" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

# Attach the AWS managed policy for RDS enhanced monitoring
resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Enable performance insights for query analysis
locals {
  performance_insights_retention_period = 7 # 7 days retention
  monitoring_interval                   = 15 # 15 seconds interval for enhanced monitoring
  monitoring_role_arn                   = aws_iam_role.rds_enhanced_monitoring.arn
  enable_enhanced_monitoring            = true
  enable_performance_insights           = true
}

# Configure CloudWatch Logs for RDS logs collection
resource "aws_cloudwatch_log_group" "postgresql_logs" {
  name              = "/aws/rds/cluster/${var.db_cluster_identifier}/postgresql"
  retention_in_days = 30
  
  tags = var.tags
}

# Configure CloudWatch Logs for RDS audit logs
resource "aws_cloudwatch_log_group" "postgresql_audit_logs" {
  name              = "/aws/rds/cluster/${var.db_cluster_identifier}/audit"
  retention_in_days = 90 # Longer retention for audit logs
  
  tags = var.tags
}

#--------------------------------------------------------------
# CloudWatch Alarms for Database Monitoring
#--------------------------------------------------------------

# CPU Utilization Alarm - Critical
resource "aws_cloudwatch_metric_alarm" "database_cpu_critical" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.prefix}-db-cpu-utilization-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Critical alert when database CPU exceeds 85% for 3 minutes"
  alarm_actions       = var.critical_alarm_actions
  ok_actions          = var.ok_alarm_actions
  
  dimensions = {
    DBClusterIdentifier = var.db_cluster_identifier
  }
  
  tags = var.tags
}

# CPU Utilization Alarm - Warning
resource "aws_cloudwatch_metric_alarm" "database_cpu_warning" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.prefix}-db-cpu-utilization-warning"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 70
  alarm_description   = "Warning alert when database CPU exceeds 70% for 5 minutes"
  alarm_actions       = var.warning_alarm_actions
  ok_actions          = var.ok_alarm_actions
  
  dimensions = {
    DBClusterIdentifier = var.db_cluster_identifier
  }
  
  tags = var.tags
}

# Memory Utilization Alarm - Critical
resource "aws_cloudwatch_metric_alarm" "database_memory_critical" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.prefix}-db-freeable-memory-critical"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 1073741824 # 1 GB in bytes
  alarm_description   = "Critical alert when database freeable memory is less than 1GB for 3 minutes"
  alarm_actions       = var.critical_alarm_actions
  ok_actions          = var.ok_alarm_actions
  
  dimensions = {
    DBClusterIdentifier = var.db_cluster_identifier
  }
  
  tags = var.tags
}

# Database Connections - Critical
resource "aws_cloudwatch_metric_alarm" "database_connections_critical" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.prefix}-db-connections-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.max_connections * 0.9 # 90% of max connections
  alarm_description   = "Critical alert when database connections exceed 90% of maximum for 3 minutes"
  alarm_actions       = var.critical_alarm_actions
  ok_actions          = var.ok_alarm_actions
  
  dimensions = {
    DBClusterIdentifier = var.db_cluster_identifier
  }
  
  tags = var.tags
}

# Disk Queue Depth - Critical
resource "aws_cloudwatch_metric_alarm" "database_disk_queue_critical" {
  count               = var.create_cloudwatch_alarms ? 1 : 0
  alarm_name          = "${var.prefix}-db-disk-queue-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DiskQueueDepth"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 10
  alarm_description   = "Critical alert when database disk queue depth exceeds 10 for 3 minutes"
  alarm_actions       = var.critical_alarm_actions
  ok_actions          = var.ok_alarm_actions
  
  dimensions = {
    DBClusterIdentifier = var.db_cluster_identifier
  }
  
  tags = var.tags
}

# Replica Lag - Critical (for read replicas)
resource "aws_cloudwatch_metric_alarm" "database_replica_lag_critical" {
  count               = var.create_cloudwatch_alarms && var.is_read_replica ? 1 : 0
  alarm_name          = "${var.prefix}-db-replica-lag-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 120 # 2 minutes
  alarm_description   = "Critical alert when database replica lag exceeds 2 minutes for 3 minutes"
  alarm_actions       = var.critical_alarm_actions
  ok_actions          = var.ok_alarm_actions
  
  dimensions = {
    DBInstanceIdentifier = var.db_instance_identifier
  }
  
  tags = var.tags
}

#--------------------------------------------------------------
# CloudWatch Dashboard for Database Monitoring
#--------------------------------------------------------------

# Create a CloudWatch dashboard for database metrics
resource "aws_cloudwatch_dashboard" "database_dashboard" {
  count          = var.create_cloudwatch_dashboard ? 1 : 0
  dashboard_name = "${var.prefix}-database-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBClusterIdentifier", var.db_cluster_identifier]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "CPU Utilization"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "FreeableMemory", "DBClusterIdentifier", var.db_cluster_identifier]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Freeable Memory"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "DatabaseConnections", "DBClusterIdentifier", var.db_cluster_identifier]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Database Connections"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "ReadIOPS", "DBClusterIdentifier", var.db_cluster_identifier],
            ["AWS/RDS", "WriteIOPS", "DBClusterIdentifier", var.db_cluster_identifier]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "IOPS"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "ReadLatency", "DBClusterIdentifier", var.db_cluster_identifier],
            ["AWS/RDS", "WriteLatency", "DBClusterIdentifier", var.db_cluster_identifier]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Latency"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "DiskQueueDepth", "DBClusterIdentifier", var.db_cluster_identifier]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Disk Queue Depth"
          view   = "timeSeries"
          stacked = false
        }
      }
    ]
  })
}

#--------------------------------------------------------------
# Datadog Integration for PostgreSQL Monitoring
#--------------------------------------------------------------

# Datadog provider configuration (if enabled)
locals {
  enable_datadog_integration = var.enable_datadog_integration
}

# Datadog API and App key configuration
provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
  api_url = var.datadog_api_url
}

# Datadog PostgreSQL integration monitor for high CPU
resource "datadog_monitor" "postgres_high_cpu" {
  count   = var.enable_datadog_integration ? 1 : 0
  name    = "${var.prefix} - PostgreSQL High CPU Utilization"
  type    = "metric alert"
  message = "PostgreSQL database CPU utilization is high ({{value}}%) on {{host.name}}. \n\nPlease investigate potential query performance issues or resource constraints.\n\n@pagerduty-${var.environment}-db-team"
  query   = "avg(last_5m):avg:aws.rds.cpuutilization{dbclusteridentifier:${var.db_cluster_identifier}} > 85"
  
  monitor_thresholds {
    critical = 85
    warning  = 75
  }
  
  notify_no_data    = false
  renotify_interval = 60
  
  tags = [
    "service:database",
    "env:${var.environment}",
    "db_cluster:${var.db_cluster_identifier}",
    "managed-by:terraform"
  ]
}

# Datadog PostgreSQL integration monitor for connection count
resource "datadog_monitor" "postgres_connection_count" {
  count   = var.enable_datadog_integration ? 1 : 0
  name    = "${var.prefix} - PostgreSQL High Connection Count"
  type    = "metric alert"
  message = "PostgreSQL database connection count is high ({{value}}) on {{host.name}}. \n\nPlease investigate connection leaks or increase max_connections if needed.\n\n@pagerduty-${var.environment}-db-team"
  query   = "avg(last_5m):avg:aws.rds.database_connections{dbclusteridentifier:${var.db_cluster_identifier}} > ${var.max_connections * 0.9}"
  
  monitor_thresholds {
    critical = var.max_connections * 0.9
    warning  = var.max_connections * 0.8
  }
  
  notify_no_data    = false
  renotify_interval = 60
  
  tags = [
    "service:database",
    "env:${var.environment}",
    "db_cluster:${var.db_cluster_identifier}",
    "managed-by:terraform"
  ]
}

# Datadog PostgreSQL integration monitor for replica lag
resource "datadog_monitor" "postgres_replica_lag" {
  count   = var.enable_datadog_integration && var.is_read_replica ? 1 : 0
  name    = "${var.prefix} - PostgreSQL Replica Lag"
  type    = "metric alert"
  message = "PostgreSQL read replica lag is high ({{value}}s) on {{host.name}}. \n\nPlease investigate replication issues.\n\n@pagerduty-${var.environment}-db-team"
  query   = "avg(last_5m):avg:aws.rds.replica_lag{dbinstanceidentifier:${var.db_instance_identifier}} > 120"
  
  monitor_thresholds {
    critical = 120
    warning  = 60
  }
  
  notify_no_data    = false
  renotify_interval = 60
  
  tags = [
    "service:database",
    "env:${var.environment}",
    "db_instance:${var.db_instance_identifier}",
    "managed-by:terraform"
  ]
}

# Datadog PostgreSQL integration dashboard
resource "datadog_dashboard" "postgres_dashboard" {
  count       = var.enable_datadog_integration ? 1 : 0
  title       = "${var.prefix} - PostgreSQL Performance Dashboard"
  description = "Comprehensive dashboard for monitoring PostgreSQL database performance metrics"
  layout_type = "ordered"
  
  widget {
    group_definition {
      title       = "PostgreSQL Performance Metrics"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "CPU Utilization"
          request {
            q            = "avg:aws.rds.cpuutilization{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
          yaxis {
            max = "100"
            min = "0"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Memory Usage"
          request {
            q            = "avg:aws.rds.freeable_memory{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Database Connections"
          request {
            q            = "avg:aws.rds.database_connections{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Read/Write IOPS"
          request {
            q            = "avg:aws.rds.read_iops{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
          request {
            q            = "avg:aws.rds.write_iops{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Read/Write Latency"
          request {
            q            = "avg:aws.rds.read_latency{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
          request {
            q            = "avg:aws.rds.write_latency{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "PostgreSQL Application Metrics"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Transaction Rate"
          request {
            q            = "avg:postgresql.transactions.tps{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Query Execution Time"
          request {
            q            = "avg:postgresql.queries.execution_time{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Active Queries"
          request {
            q            = "avg:postgresql.queries.active{dbclusteridentifier:${var.db_cluster_identifier}}"
            display_type = "line"
          }
        }
      }
    }
  }
}