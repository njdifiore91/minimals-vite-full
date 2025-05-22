# RabbitMQ Monitoring Configuration
# This file sets up comprehensive monitoring and alerting for the RabbitMQ cluster
# using CloudWatch metrics, dashboards, alarms, and log groups.

# Local variables for monitoring configuration
locals {
  # Namespace for RabbitMQ metrics
  rabbitmq_namespace = "RabbitMQ"
  
  # Common dimensions for RabbitMQ metrics
  common_dimensions = {
    Environment = var.environment
    Service     = "RabbitMQ"
    Cluster     = var.cluster_name
  }
  
  # Alert thresholds
  thresholds = {
    # Queue depth thresholds
    queue_depth_warning  = 1000
    queue_depth_critical = 5000
    
    # Message rate thresholds (messages per second)
    message_rate_warning  = 500
    message_rate_critical = 1000
    
    # CPU utilization thresholds (percentage)
    cpu_warning  = 70
    cpu_critical = 90
    
    # Memory utilization thresholds (percentage)
    memory_warning  = 70
    memory_critical = 85
    
    # Disk space thresholds (percentage)
    disk_warning  = 70
    disk_critical = 85
  }
  
  # Evaluation periods for alarms
  evaluation_periods = {
    short  = 2  # 2 periods (for quick response)
    medium = 3  # 3 periods (balanced)
    long   = 5  # 5 periods (to avoid false positives)
  }
  
  # Period for metrics (in seconds)
  metric_periods = {
    short  = 60   # 1 minute
    medium = 300  # 5 minutes
    long   = 900  # 15 minutes
  }
  
  # Queue names to monitor specifically
  monitored_queues = [
    "document-processing",
    "data-extraction",
    "notification"
  ]
}

#---------------------------------------------------------------
# Variables
#---------------------------------------------------------------

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "cluster_name" {
  description = "Name of the RabbitMQ cluster"
  type        = string
}

variable "rabbitmq_asg_name" {
  description = "Name of the Auto Scaling Group for RabbitMQ nodes"
  type        = string
}

variable "rabbitmq_endpoint" {
  description = "Endpoint for the RabbitMQ cluster"
  type        = string
}

variable "min_node_count" {
  description = "Minimum number of nodes required for the RabbitMQ cluster"
  type        = number
  default     = 3
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for alarm notifications"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

#---------------------------------------------------------------
# CloudWatch Log Groups for RabbitMQ
#---------------------------------------------------------------

# Log group for RabbitMQ application logs
resource "aws_cloudwatch_log_group" "rabbitmq_application_logs" {
  name              = "/mca/rabbitmq/${var.environment}/application"
  retention_in_days = var.environment == "production" ? 90 : 30
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Application Logs"
    Environment = var.environment
  })
}

# Log group for RabbitMQ error logs
resource "aws_cloudwatch_log_group" "rabbitmq_error_logs" {
  name              = "/mca/rabbitmq/${var.environment}/error"
  retention_in_days = var.environment == "production" ? 90 : 30
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Error Logs"
    Environment = var.environment
  })
}

#---------------------------------------------------------------
# CloudWatch Metrics and Alarms for RabbitMQ
#---------------------------------------------------------------

# Metric filter to extract queue depth from logs
resource "aws_cloudwatch_log_metric_filter" "queue_depth" {
  for_each = toset(local.monitored_queues)
  
  name           = "${each.value}-queue-depth"
  pattern        = "{ $.queue = \"${each.value}\" && $.messages_ready = * }"
  log_group_name = aws_cloudwatch_log_group.rabbitmq_application_logs.name
  
  metric_transformation {
    name          = "${each.value}QueueDepth"
    namespace     = local.rabbitmq_namespace
    value         = "$.messages_ready"
    default_value = 0
    dimensions = {
      QueueName = each.value
    }
  }
}

# Metric filter to extract message rates from logs
resource "aws_cloudwatch_log_metric_filter" "message_rate" {
  for_each = toset(local.monitored_queues)
  
  name           = "${each.value}-message-rate"
  pattern        = "{ $.queue = \"${each.value}\" && $.messages_published_per_second = * }"
  log_group_name = aws_cloudwatch_log_group.rabbitmq_application_logs.name
  
  metric_transformation {
    name          = "${each.value}MessageRate"
    namespace     = local.rabbitmq_namespace
    value         = "$.messages_published_per_second"
    default_value = 0
    dimensions = {
      QueueName = each.value
    }
  }
}

# Metric filter to extract consumer count from logs
resource "aws_cloudwatch_log_metric_filter" "consumer_count" {
  for_each = toset(local.monitored_queues)
  
  name           = "${each.value}-consumer-count"
  pattern        = "{ $.queue = \"${each.value}\" && $.consumers = * }"
  log_group_name = aws_cloudwatch_log_group.rabbitmq_application_logs.name
  
  metric_transformation {
    name          = "${each.value}ConsumerCount"
    namespace     = local.rabbitmq_namespace
    value         = "$.consumers"
    default_value = 0
    dimensions = {
      QueueName = each.value
    }
  }
}

#---------------------------------------------------------------
# CloudWatch Alarms for RabbitMQ
#---------------------------------------------------------------

# Queue depth alarms
resource "aws_cloudwatch_metric_alarm" "queue_depth_warning" {
  for_each = toset(local.monitored_queues)
  
  alarm_name          = "${var.environment}-${each.value}-queue-depth-warning"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = local.evaluation_periods.medium
  metric_name         = "${each.value}QueueDepth"
  namespace           = local.rabbitmq_namespace
  period              = local.metric_periods.medium
  statistic           = "Maximum"
  threshold           = local.thresholds.queue_depth_warning
  alarm_description   = "This alarm triggers when the ${each.value} queue depth exceeds ${local.thresholds.queue_depth_warning} messages for ${local.evaluation_periods.medium * (local.metric_periods.medium / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    QueueName = each.value
  }
  
  tags = merge(var.tags, {
    Name        = "${each.value} Queue Depth Warning"
    Environment = var.environment
    Severity    = "Warning"
  })
}

resource "aws_cloudwatch_metric_alarm" "queue_depth_critical" {
  for_each = toset(local.monitored_queues)
  
  alarm_name          = "${var.environment}-${each.value}-queue-depth-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = local.evaluation_periods.short
  metric_name         = "${each.value}QueueDepth"
  namespace           = local.rabbitmq_namespace
  period              = local.metric_periods.short
  statistic           = "Maximum"
  threshold           = local.thresholds.queue_depth_critical
  alarm_description   = "This alarm triggers when the ${each.value} queue depth exceeds ${local.thresholds.queue_depth_critical} messages for ${local.evaluation_periods.short * (local.metric_periods.short / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    QueueName = each.value
  }
  
  tags = merge(var.tags, {
    Name        = "${each.value} Queue Depth Critical"
    Environment = var.environment
    Severity    = "Critical"
  })
}

# Consumer count alarms (alert when no consumers)
resource "aws_cloudwatch_metric_alarm" "no_consumers" {
  for_each = toset(local.monitored_queues)
  
  alarm_name          = "${var.environment}-${each.value}-no-consumers"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = local.evaluation_periods.medium
  metric_name         = "${each.value}ConsumerCount"
  namespace           = local.rabbitmq_namespace
  period              = local.metric_periods.medium
  statistic           = "Minimum"
  threshold           = 0
  alarm_description   = "This alarm triggers when the ${each.value} queue has no consumers for ${local.evaluation_periods.medium * (local.metric_periods.medium / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    QueueName = each.value
  }
  
  tags = merge(var.tags, {
    Name        = "${each.value} No Consumers"
    Environment = var.environment
    Severity    = "Critical"
  })
}

# Message rate alarms (high throughput)
resource "aws_cloudwatch_metric_alarm" "high_message_rate" {
  for_each = toset(local.monitored_queues)
  
  alarm_name          = "${var.environment}-${each.value}-high-message-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = local.evaluation_periods.medium
  metric_name         = "${each.value}MessageRate"
  namespace           = local.rabbitmq_namespace
  period              = local.metric_periods.medium
  statistic           = "Average"
  threshold           = local.thresholds.message_rate_warning
  alarm_description   = "This alarm triggers when the ${each.value} message rate exceeds ${local.thresholds.message_rate_warning} messages per second for ${local.evaluation_periods.medium * (local.metric_periods.medium / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    QueueName = each.value
  }
  
  tags = merge(var.tags, {
    Name        = "${each.value} High Message Rate"
    Environment = var.environment
    Severity    = "Warning"
  })
}

# System-level alarms

# CPU utilization alarm
resource "aws_cloudwatch_metric_alarm" "cpu_utilization_high" {
  alarm_name          = "${var.environment}-rabbitmq-cpu-utilization-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = local.evaluation_periods.medium
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = local.metric_periods.medium
  statistic           = "Average"
  threshold           = local.thresholds.cpu_warning
  alarm_description   = "This alarm triggers when the RabbitMQ cluster CPU utilization exceeds ${local.thresholds.cpu_warning}% for ${local.evaluation_periods.medium * (local.metric_periods.medium / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    AutoScalingGroupName = var.rabbitmq_asg_name
  }
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ CPU Utilization High"
    Environment = var.environment
    Severity    = "Warning"
  })
}

# Memory utilization alarm
resource "aws_cloudwatch_metric_alarm" "memory_utilization_high" {
  alarm_name          = "${var.environment}-rabbitmq-memory-utilization-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = local.evaluation_periods.medium
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/EC2"
  period              = local.metric_periods.medium
  statistic           = "Average"
  threshold           = local.thresholds.memory_warning
  alarm_description   = "This alarm triggers when the RabbitMQ cluster memory utilization exceeds ${local.thresholds.memory_warning}% for ${local.evaluation_periods.medium * (local.metric_periods.medium / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    AutoScalingGroupName = var.rabbitmq_asg_name
  }
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Memory Utilization High"
    Environment = var.environment
    Severity    = "Warning"
  })
}

# Disk space utilization alarm
resource "aws_cloudwatch_metric_alarm" "disk_space_utilization_high" {
  alarm_name          = "${var.environment}-rabbitmq-disk-space-utilization-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = local.evaluation_periods.medium
  metric_name         = "DiskSpaceUtilization"
  namespace           = "CWAgent"
  period              = local.metric_periods.medium
  statistic           = "Average"
  threshold           = local.thresholds.disk_warning
  alarm_description   = "This alarm triggers when the RabbitMQ cluster disk space utilization exceeds ${local.thresholds.disk_warning}% for ${local.evaluation_periods.medium * (local.metric_periods.medium / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    AutoScalingGroupName = var.rabbitmq_asg_name
    MountPath            = "/var/lib/rabbitmq"
  }
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Disk Space Utilization High"
    Environment = var.environment
    Severity    = "Warning"
  })
}

# Cluster health alarm (node count)
resource "aws_cloudwatch_metric_alarm" "cluster_node_count_low" {
  alarm_name          = "${var.environment}-rabbitmq-cluster-node-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = local.evaluation_periods.short
  metric_name         = "GroupInServiceInstances"
  namespace           = "AWS/AutoScaling"
  period              = local.metric_periods.short
  statistic           = "Minimum"
  threshold           = var.min_node_count
  alarm_description   = "This alarm triggers when the RabbitMQ cluster has fewer than ${var.min_node_count} nodes for ${local.evaluation_periods.short * (local.metric_periods.short / 60)} minutes"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    AutoScalingGroupName = var.rabbitmq_asg_name
  }
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Cluster Node Count Low"
    Environment = var.environment
    Severity    = "Critical"
  })
}

#---------------------------------------------------------------
# CloudWatch Dashboard for RabbitMQ
#---------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "rabbitmq_dashboard" {
  dashboard_name = "${var.environment}-rabbitmq-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      # Header with cluster information
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = <<-EOT
            # RabbitMQ Cluster Dashboard - ${upper(var.environment)}
            
            Cluster: ${var.cluster_name} | Environment: ${upper(var.environment)} | Region: ${data.aws_region.current.name}
          EOT
        }
      },
      
      # System metrics - CPU, Memory, Disk
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 8
        height = 6
        properties = {
          title     = "CPU Utilization"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", var.rabbitmq_asg_name]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Average"
          yAxis     = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                value = local.thresholds.cpu_warning
                label = "Warning"
                color = "#ff9900"
              },
              {
                value = local.thresholds.cpu_critical
                label = "Critical"
                color = "#ff0000"
              }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 2
        width  = 8
        height = 6
        properties = {
          title     = "Memory Utilization"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            ["AWS/EC2", "MemoryUtilization", "AutoScalingGroupName", var.rabbitmq_asg_name]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Average"
          yAxis     = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                value = local.thresholds.memory_warning
                label = "Warning"
                color = "#ff9900"
              },
              {
                value = local.thresholds.memory_critical
                label = "Critical"
                color = "#ff0000"
              }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 2
        width  = 8
        height = 6
        properties = {
          title     = "Disk Space Utilization"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            ["CWAgent", "DiskSpaceUtilization", "AutoScalingGroupName", var.rabbitmq_asg_name, "MountPath", "/var/lib/rabbitmq"]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Average"
          yAxis     = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                value = local.thresholds.disk_warning
                label = "Warning"
                color = "#ff9900"
              },
              {
                value = local.thresholds.disk_critical
                label = "Critical"
                color = "#ff0000"
              }
            ]
          }
        }
      },
      
      # Cluster health metrics
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 8
        height = 6
        properties = {
          title     = "Cluster Node Count"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            ["AWS/AutoScaling", "GroupInServiceInstances", "AutoScalingGroupName", var.rabbitmq_asg_name]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Minimum"
          yAxis     = {
            left = {
              min = 0
            }
          }
          annotations = {
            horizontal = [
              {
                value = var.min_node_count
                label = "Minimum Nodes"
                color = "#ff0000"
              }
            ]
          }
        }
      },
      
      # Queue metrics - for each monitored queue
      {
        type   = "metric"
        x      = 8
        y      = 8
        width  = 16
        height = 6
        properties = {
          title     = "Queue Depths"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            for queue in local.monitored_queues :
            [local.rabbitmq_namespace, "${queue}QueueDepth", "QueueName", queue]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Maximum"
          yAxis     = {
            left = {
              min = 0
            }
          }
          annotations = {
            horizontal = [
              {
                value = local.thresholds.queue_depth_warning
                label = "Warning"
                color = "#ff9900"
              },
              {
                value = local.thresholds.queue_depth_critical
                label = "Critical"
                color = "#ff0000"
              }
            ]
          }
        }
      },
      
      # Message rates
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 12
        height = 6
        properties = {
          title     = "Message Rates"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            for queue in local.monitored_queues :
            [local.rabbitmq_namespace, "${queue}MessageRate", "QueueName", queue]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Average"
          yAxis     = {
            left = {
              min = 0
            }
          }
          annotations = {
            horizontal = [
              {
                value = local.thresholds.message_rate_warning
                label = "Warning"
                color = "#ff9900"
              },
              {
                value = local.thresholds.message_rate_critical
                label = "Critical"
                color = "#ff0000"
              }
            ]
          }
        }
      },
      
      # Consumer counts
      {
        type   = "metric"
        x      = 12
        y      = 14
        width  = 12
        height = 6
        properties = {
          title     = "Consumer Counts"
          view      = "timeSeries"
          stacked   = false
          metrics   = [
            for queue in local.monitored_queues :
            [local.rabbitmq_namespace, "${queue}ConsumerCount", "QueueName", queue]
          ]
          region    = data.aws_region.current.name
          period    = 300
          stat      = "Minimum"
          yAxis     = {
            left = {
              min = 0
            }
          }
        }
      },
      
      # Error logs widget
      {
        type   = "log"
        x      = 0
        y      = 20
        width  = 24
        height = 6
        properties = {
          title     = "RabbitMQ Error Logs"
          query     = "SOURCE '${aws_cloudwatch_log_group.rabbitmq_error_logs.name}' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region    = data.aws_region.current.name
          view      = "table"
        }
      }
    ]
  })
}

#---------------------------------------------------------------
# Prometheus Exporter Configuration (for RabbitMQ monitoring)
#---------------------------------------------------------------

# User data script to install and configure Prometheus exporter for RabbitMQ
data "template_file" "prometheus_exporter_setup" {
  template = <<-EOT
    #!/bin/bash
    # Install RabbitMQ Prometheus exporter
    mkdir -p /opt/prometheus-exporters/rabbitmq_exporter
    cd /opt/prometheus-exporters/rabbitmq_exporter
    
    # Download and install the exporter
    curl -L -O https://github.com/rabbitmq/rabbitmq-prometheus/releases/latest/download/rabbitmq_prometheus-*.ez
    cp rabbitmq_prometheus-*.ez /usr/lib/rabbitmq/plugins/
    
    # Enable the plugin
    rabbitmq-plugins enable rabbitmq_prometheus
    
    # Configure the exporter
    cat > /etc/rabbitmq/conf.d/prometheus.conf << 'EOF'
    prometheus.return_per_object_metrics = false
    prometheus.path = /metrics
    prometheus.tcp.port = 15692
    EOF
    
    # Restart RabbitMQ to apply changes
    systemctl restart rabbitmq-server
    
    # Set up CloudWatch agent for custom metrics
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
    {
      "metrics": {
        "namespace": "${local.rabbitmq_namespace}",
        "append_dimensions": {
          "AutoScalingGroupName": "$${aws:AutoScalingGroupName}",
          "InstanceId": "$${aws:InstanceId}"
        },
        "metrics_collected": {
          "rabbitmq": {
            "metrics_collection_interval": 60,
            "endpoint": "http://localhost:15692/metrics",
            "metrics": [
              {"name": "rabbitmq_queue_messages", "rename": "QueueDepth", "dimensions": [["queue"]]},
              {"name": "rabbitmq_queue_messages_published_total", "rename": "MessagesPublishedTotal", "dimensions": [["queue"]]},
              {"name": "rabbitmq_queue_consumers", "rename": "ConsumerCount", "dimensions": [["queue"]]},
              {"name": "rabbitmq_process_open_fds", "rename": "OpenFileDescriptors"},
              {"name": "rabbitmq_process_open_tcp_sockets", "rename": "OpenTcpSockets"},
              {"name": "rabbitmq_process_open_tcp_connections", "rename": "OpenTcpConnections"},
              {"name": "rabbitmq_process_resident_memory_bytes", "rename": "ResidentMemory"},
              {"name": "rabbitmq_disk_space_available_bytes", "rename": "DiskSpaceAvailable"}
            ]
          },
          "disk": {
            "measurement": [
              "used_percent"
            ],
            "metrics_collection_interval": 60,
            "resources": [
              "/var/lib/rabbitmq"
            ],
            "dimensions": [
              ["MountPath"]
            ]
          },
          "mem": {
            "measurement": [
              "used_percent"
            ],
            "metrics_collection_interval": 60
          }
        }
      },
      "logs": {
        "logs_collected": {
          "files": {
            "collect_list": [
              {
                "file_path": "/var/log/rabbitmq/*.log",
                "log_group_name": "${aws_cloudwatch_log_group.rabbitmq_application_logs.name}",
                "log_stream_name": "{instance_id}-application",
                "timezone": "UTC"
              },
              {
                "file_path": "/var/log/rabbitmq/*_err.log",
                "log_group_name": "${aws_cloudwatch_log_group.rabbitmq_error_logs.name}",
                "log_stream_name": "{instance_id}-error",
                "timezone": "UTC"
              }
            ]
          }
        }
      }
    }
    EOF
    
    # Restart CloudWatch agent to apply changes
    systemctl restart amazon-cloudwatch-agent
  EOT
}

#---------------------------------------------------------------
# Health Checks for RabbitMQ Endpoints
#---------------------------------------------------------------

# Route53 health check for RabbitMQ management interface
resource "aws_route53_health_check" "rabbitmq_management" {
  fqdn              = var.rabbitmq_endpoint
  port              = 15672
  type              = "HTTP"
  resource_path     = "/api/healthchecks/node"
  failure_threshold = 3
  request_interval  = 30
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Management Interface Health Check"
    Environment = var.environment
  })
}

# Route53 health check for RabbitMQ Prometheus metrics endpoint
resource "aws_route53_health_check" "rabbitmq_prometheus" {
  fqdn              = var.rabbitmq_endpoint
  port              = 15692
  type              = "HTTP"
  resource_path     = "/metrics"
  failure_threshold = 3
  request_interval  = 30
  
  tags = merge(var.tags, {
    Name        = "RabbitMQ Prometheus Metrics Health Check"
    Environment = var.environment
  })
}

#---------------------------------------------------------------
# Data Sources
#---------------------------------------------------------------

# Get current AWS region
data "aws_region" "current" {}