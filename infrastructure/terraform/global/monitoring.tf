# Global Monitoring Infrastructure Configuration
# This file defines the global monitoring resources for the MCA Application Processing System
# It establishes centralized monitoring, logging, and alerting capabilities across all environments

terraform {
  required_providers {
    datadog = {
      source  = "datadog/datadog"
      version = "~> 3.20.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

# Datadog provider configuration with variables for API and APP keys
provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
}

# Variables for Datadog configuration
variable "datadog_api_key" {
  description = "Datadog API key for authentication"
  type        = string
  sensitive   = true
}

variable "datadog_app_key" {
  description = "Datadog APP key for authentication"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  default     = "global"
}

variable "notification_channels" {
  description = "Map of notification channels for different alert severities"
  type = object({
    critical = object({
      pagerduty_service_key = string
      slack_channel         = string
    })
    high = object({
      slack_channel = string
    })
    medium = object({
      slack_channel = string
    })
    low = object({
      jira_project = string
    })
  })
  sensitive = true
}

# Datadog organization settings
resource "datadog_organization_settings" "mca_org_settings" {
  name = "Dollar Funding MCA"
  settings {
    saml {
      enabled = true
    }
    saml_autocreate_users_domains {
      domains = ["dollarfunding.com"]
      enabled = true
    }
    saml_strict_mode {
      enabled = true
    }
  }
}

# Datadog log retention configuration
resource "datadog_logs_custom_pipeline" "mca_pipeline" {
  name        = "MCA Application Processing Pipeline"
  is_enabled  = true
  filter {
    query = "source:mca-*"
  }
  
  processor {
    grok_parser {
      name    = "parse_log_format"
      samples = ["[2023-04-01 12:34:56.789] [INFO] [service-name] - Message content"]
      source  = "message"
      grok {
        match_rules = "\\[%{TIMESTAMP_ISO8601:timestamp}\\] \\[%{WORD:level}\\] \\[%{WORD:service}\\] - %{GREEDYDATA:message_content}"
      }
    }
  }
  
  processor {
    status_remapper {
      name   = "Set log status based on level"
      sources = ["level"]
    }
  }
  
  processor {
    service_remapper {
      name   = "Extract service name"
      sources = ["service"]
    }
  }
}

# Log retention policies
resource "datadog_logs_archive" "mca_logs_archive" {
  name  = "MCA Logs Archive"
  query = "source:mca-*"
  
  s3_archive {
    bucket     = aws_s3_bucket.datadog_archives.bucket
    path       = "/logs"
    role_arn   = aws_iam_role.datadog_archive_role.arn
    account_id = data.aws_caller_identity.current.account_id
    region     = data.aws_region.current.name
  }
  
  # Define retention periods based on log type
  rehydration_tags = ["env:${var.environment}", "service:mca"]
  include_tags     = true
}

# AWS resources for log archiving
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_s3_bucket" "datadog_archives" {
  bucket = "mca-datadog-archives-${var.environment}"
  
  lifecycle_rule {
    id      = "log-retention"
    enabled = true
    
    # Standard logs - 90 days
    filter {
      prefix = "logs/standard/"
    }
    expiration {
      days = 90
    }
    
    # Error logs - 1 year
    filter {
      prefix = "logs/errors/"
    }
    expiration {
      days = 365
    }
    
    # Security logs - 7 years
    filter {
      prefix = "logs/security/"
    }
    expiration {
      days = 2555 # ~7 years
    }
  }
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_iam_role" "datadog_archive_role" {
  name = "datadog-archive-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "datadog.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "datadog_archive_policy" {
  name = "datadog-archive-policy-${var.environment}"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Effect = "Allow"
        Resource = "${aws_s3_bucket.datadog_archives.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "datadog_archive_attachment" {
  role       = aws_iam_role.datadog_archive_role.name
  policy_arn = aws_iam_policy.datadog_archive_policy.arn
}

# Datadog monitors for critical metrics
# 1. Application processing time monitor
resource "datadog_monitor" "application_processing_time" {
  name               = "[MCA] Application Processing Time Exceeded"
  type               = "metric alert"
  message            = "Application processing time has exceeded the 5-minute SLA threshold. Please investigate immediately. Notify: @pagerduty-critical @slack-${var.notification_channels.critical.slack_channel}"
  escalation_message = "Application processing time is still exceeding the SLA threshold! This is critical! Notify: @pagerduty-critical"
  
  query = "avg(last_5m):avg:mca.application.processing_time{*} by {service} > 300"
  
  monitor_thresholds {
    critical = 300 # 5 minutes in seconds
    warning  = 240 # 4 minutes in seconds
  }
  
  notify_no_data    = true
  no_data_timeframe = 10
  
  include_tags = true
  tags         = ["service:mca", "env:${var.environment}", "team:operations", "severity:critical"]
}

# 2. Error rate monitor
resource "datadog_monitor" "error_rate" {
  name               = "[MCA] High Error Rate Detected"
  type               = "metric alert"
  message            = "Error rate has exceeded 5% for the MCA application. Please investigate immediately. Notify: @pagerduty-critical @slack-${var.notification_channels.critical.slack_channel}"
  escalation_message = "Error rate is still above threshold! This is impacting users! Notify: @pagerduty-critical"
  
  query = "sum(last_5m):sum:mca.application.errors{*}.as_count() / sum:mca.application.requests{*}.as_count() * 100 > 5"
  
  monitor_thresholds {
    critical = 5.0 # 5% error rate
    warning  = 2.0 # 2% error rate
  }
  
  notify_no_data    = false
  include_tags      = true
  tags              = ["service:mca", "env:${var.environment}", "team:operations", "severity:critical"]
}

# 3. OCR accuracy monitor
resource "datadog_monitor" "ocr_accuracy" {
  name               = "[MCA] OCR Accuracy Below Threshold"
  type               = "metric alert"
  message            = "OCR accuracy has fallen below the 99% threshold. This may impact data extraction quality. Notify: @slack-${var.notification_channels.high.slack_channel}"
  escalation_message = "OCR accuracy is still below threshold and not improving! Notify: @pagerduty-critical"
  
  query = "avg(last_15m):avg:mca.ocr.accuracy{*} by {document_type} < 99"
  
  monitor_thresholds {
    critical = 99.0 # 99% accuracy
    warning  = 99.5 # 99.5% accuracy
  }
  
  notify_no_data    = true
  no_data_timeframe = 30
  
  include_tags = true
  tags         = ["service:ocr-service", "env:${var.environment}", "team:data-science", "severity:high"]
}

# 4. RabbitMQ queue depth monitor
resource "datadog_monitor" "rabbitmq_queue_depth" {
  name               = "[MCA] RabbitMQ Queue Depth High"
  type               = "metric alert"
  message            = "RabbitMQ queue depth is high, indicating potential processing backlog. Notify: @slack-${var.notification_channels.high.slack_channel}"
  escalation_message = "RabbitMQ queue depth is still high after 30 minutes! Notify: @pagerduty-critical"
  
  query = "avg(last_10m):avg:rabbitmq.queue.messages{*} by {queue} > 1000"
  
  monitor_thresholds {
    critical = 1000 # 1000 messages
    warning  = 500  # 500 messages
  }
  
  notify_no_data    = false
  include_tags      = true
  tags              = ["service:rabbitmq", "env:${var.environment}", "team:infrastructure", "severity:high"]
}

# 5. Database replication lag monitor
resource "datadog_monitor" "db_replication_lag" {
  name               = "[MCA] Database Replication Lag High"
  type               = "metric alert"
  message            = "PostgreSQL replication lag is high. This may impact read replica consistency. Notify: @slack-${var.notification_channels.high.slack_channel}"
  escalation_message = "PostgreSQL replication lag is still high after 15 minutes! Notify: @pagerduty-critical"
  
  query = "avg(last_5m):avg:postgresql.replication_delay{*} by {host} > 300"
  
  monitor_thresholds {
    critical = 300 # 5 minutes in seconds
    warning  = 60  # 1 minute in seconds
  }
  
  notify_no_data    = true
  no_data_timeframe = 20
  
  include_tags = true
  tags         = ["service:postgresql", "env:${var.environment}", "team:infrastructure", "severity:high"]
}

# 6. API response time monitor
resource "datadog_monitor" "api_response_time" {
  name               = "[MCA] API Response Time High"
  type               = "metric alert"
  message            = "API response time is high, affecting user experience. Notify: @slack-${var.notification_channels.medium.slack_channel}"
  escalation_message = "API response time is still high after 30 minutes! Notify: @slack-${var.notification_channels.high.slack_channel}"
  
  query = "avg(last_5m):avg:mca.api.response_time{*} by {endpoint} > 1000"
  
  monitor_thresholds {
    critical = 1000 # 1000ms
    warning  = 500  # 500ms
  }
  
  notify_no_data    = false
  include_tags      = true
  tags              = ["service:api-gateway", "env:${var.environment}", "team:backend", "severity:medium"]
}

# 7. System resource utilization monitor
resource "datadog_monitor" "system_resource_utilization" {
  name               = "[MCA] High System Resource Utilization"
  type               = "metric alert"
  message            = "System resource utilization is high. This may impact performance. Notify: @slack-${var.notification_channels.medium.slack_channel}"
  escalation_message = "System resource utilization is still high! Notify: @slack-${var.notification_channels.high.slack_channel}"
  
  query = "avg(last_15m):avg:system.cpu.user{*} by {host} + avg:system.cpu.system{*} by {host} > 80"
  
  monitor_thresholds {
    critical = 80.0 # 80% CPU utilization
    warning  = 70.0 # 70% CPU utilization
  }
  
  notify_no_data    = false
  include_tags      = true
  tags              = ["service:system", "env:${var.environment}", "team:infrastructure", "severity:medium"]
}

# Datadog dashboards for key performance indicators
resource "datadog_dashboard" "mca_executive_dashboard" {
  title        = "MCA Application Processing - Executive Dashboard"
  description  = "Executive overview of MCA application processing system performance and SLAs"
  layout_type  = "ordered"
  
  widget {
    group_definition {
      title       = "SLA Compliance"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Application Processing Time (SLA: 5 min)"
          request {
            q            = "avg:mca.application.processing_time{*}.rollup(avg, 60)"
            display_type = "line"
          }
          marker {
            display_type = "error dashed"
            value        = "y = 300"
            label        = "SLA Threshold (5 min)"
          }
        }
      }
      
      widget {
        query_value_definition {
          title = "Automation Rate (Target: 93%)"
          request {
            q            = "100 - (sum:mca.application.manual_processing{*}.as_count() / sum:mca.application.total{*}.as_count() * 100)"
            aggregator   = "avg"
            conditional_formats {
              comparator = ">="
              value      = 93
              palette    = "white_on_green"
            }
            conditional_formats {
              comparator = "<"
              value      = 93
              palette    = "white_on_red"
            }
          }
          precision = 1
          unit      = "%"
        }
      }
      
      widget {
        query_value_definition {
          title = "OCR Accuracy (Target: 99%)"
          request {
            q            = "avg:mca.ocr.accuracy{*}"
            aggregator   = "avg"
            conditional_formats {
              comparator = ">="
              value      = 99
              palette    = "white_on_green"
            }
            conditional_formats {
              comparator = "<"
              value      = 99
              palette    = "white_on_red"
            }
          }
          precision = 2
          unit      = "%"
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "System Health"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Error Rate"
          request {
            q            = "sum:mca.application.errors{*}.as_count() / sum:mca.application.requests{*}.as_count() * 100"
            display_type = "line"
          }
          marker {
            display_type = "error dashed"
            value        = "y = 5"
            label        = "Critical Threshold (5%)"
          }
          marker {
            display_type = "warning dashed"
            value        = "y = 2"
            label        = "Warning Threshold (2%)"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "API Response Time"
          request {
            q            = "avg:mca.api.response_time{*} by {endpoint}"
            display_type = "line"
          }
          marker {
            display_type = "error dashed"
            value        = "y = 1000"
            label        = "Critical Threshold (1000ms)"
          }
        }
      }
      
      widget {
        toplist_definition {
          title = "Top Services by Resource Usage"
          request {
            q = "top(avg:system.cpu.user{*} by {service}, 10, 'mean', 'desc')"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "Business Metrics"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Applications Processed (Daily)"
          request {
            q            = "sum:mca.application.completed{*}.rollup(sum, 86400)"
            display_type = "bars"
          }
        }
      }
      
      widget {
        query_value_definition {
          title = "Average Processing Time"
          request {
            q          = "avg:mca.application.processing_time{*}"
            aggregator = "avg"
          }
          precision = 0
          unit      = "s"
        }
      }
      
      widget {
        query_value_definition {
          title = "Applications Pending"
          request {
            q          = "sum:mca.application.pending{*}"
            aggregator = "sum"
          }
        }
      }
    }
  }
  
  template_variable {
    name    = "env"
    prefix  = "env"
    default = "*"
  }
  
  template_variable {
    name    = "service"
    prefix  = "service"
    default = "*"
  }
}

resource "datadog_dashboard" "mca_operations_dashboard" {
  title        = "MCA Application Processing - Operations Dashboard"
  description  = "Detailed operational metrics for the MCA application processing system"
  layout_type  = "ordered"
  
  widget {
    group_definition {
      title       = "Email Processing Pipeline"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Emails Received"
          request {
            q            = "sum:mca.email.received{*}.as_count()"
            display_type = "bars"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Document Extraction Rate"
          request {
            q            = "sum:mca.email.documents_extracted{*}.as_count() / sum:mca.email.received{*}.as_count() * 100"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Email Processing Errors"
          request {
            q            = "sum:mca.email.errors{*} by {error_type}.as_count()"
            display_type = "bars"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "Document Processing"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Documents Classified by Type"
          request {
            q            = "sum:mca.document.classified{*} by {document_type}.as_count()"
            display_type = "bars"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "OCR Processing Time"
          request {
            q            = "avg:mca.ocr.processing_time{*} by {document_type}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "OCR Accuracy by Document Type"
          request {
            q            = "avg:mca.ocr.accuracy{*} by {document_type}"
            display_type = "line"
          }
          marker {
            display_type = "error dashed"
            value        = "y = 99"
            label        = "Minimum Accuracy (99%)"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "Application Processing"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Applications by Status"
          request {
            q            = "sum:mca.application.count{*} by {status}.as_count()"
            display_type = "area"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Manual Review Rate"
          request {
            q            = "sum:mca.application.manual_review{*}.as_count() / sum:mca.application.total{*}.as_count() * 100"
            display_type = "line"
          }
          marker {
            display_type = "error dashed"
            value        = "y = 7"
            label        = "Target (7% max)"
          }
        }
      }
      
      widget {
        toplist_definition {
          title = "Top Reasons for Manual Review"
          request {
            q = "top(sum:mca.application.manual_review{*} by {reason}.as_count(), 10, 'sum', 'desc')"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "Infrastructure Health"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "RabbitMQ Queue Depth"
          request {
            q            = "avg:rabbitmq.queue.messages{*} by {queue}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Database Replication Lag"
          request {
            q            = "avg:postgresql.replication_delay{*} by {host}"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Redis Cache Hit Rate"
          request {
            q            = "avg:redis.stats.keyspace_hits{*} / (avg:redis.stats.keyspace_hits{*} + avg:redis.stats.keyspace_misses{*}) * 100"
            display_type = "line"
          }
        }
      }
    }
  }
  
  template_variable {
    name    = "env"
    prefix  = "env"
    default = "*"
  }
  
  template_variable {
    name    = "service"
    prefix  = "service"
    default = "*"
  }
}

# Datadog Synthetic Tests for critical endpoints
resource "datadog_synthetics_test" "api_health_check" {
  name      = "MCA API Health Check"
  type      = "api"
  subtype   = "http"
  status    = "live"
  message   = "API health check failed. Please investigate immediately."
  locations = ["aws:us-east-1", "aws:us-west-2"]
  
  request_definition {
    method = "GET"
    url    = "https://api.dollarfunding.com/health"
    timeout = 30
  }
  
  assertion {
    type     = "statusCode"
    operator = "is"
    target   = "200"
  }
  
  assertion {
    type     = "responseTime"
    operator = "lessThan"
    target   = "1000"
  }
  
  options_list {
    tick_every = 60
    
    retry {
      count    = 2
      interval = 300
    }
    
    monitor_options {
      renotify_interval = 120
    }
  }
  
  tags = ["service:api-gateway", "env:${var.environment}", "team:operations", "critical:true"]
}

# Output the dashboard URLs for reference
output "executive_dashboard_url" {
  description = "URL to the MCA Executive Dashboard in Datadog"
  value       = "https://app.datadoghq.com/dashboard/${datadog_dashboard.mca_executive_dashboard.id}"
}

output "operations_dashboard_url" {
  description = "URL to the MCA Operations Dashboard in Datadog"
  value       = "https://app.datadoghq.com/dashboard/${datadog_dashboard.mca_operations_dashboard.id}"
}