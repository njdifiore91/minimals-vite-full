# Redis Cache Monitoring Configuration
# This file sets up comprehensive monitoring and alerting for the Redis cluster
# using CloudWatch or equivalent services based on the deployment environment.

locals {
  # Alert thresholds based on technical specifications
  memory_usage_warning_threshold  = 70  # Percentage
  memory_usage_critical_threshold = 85  # Percentage
  eviction_rate_threshold         = 100 # Evictions per second
  connection_count_threshold      = 90  # Percentage of max connections
  
  # TTL settings from technical specifications
  data_ttl_minutes    = 15  # 15 minutes TTL for application data
  session_ttl_hours   = 24  # 24 hours TTL for user sessions
  
  # Dashboard configuration
  dashboard_name = var.environment != "" ? "redis-${var.environment}-dashboard" : "redis-dashboard"
  
  # Monitoring provider - defaults to cloudwatch but can be overridden
  monitoring_provider = var.monitoring_provider != "" ? var.monitoring_provider : "cloudwatch"
}

# CloudWatch Monitoring Resources
resource "aws_cloudwatch_metric_alarm" "redis_memory_usage" {
  count               = local.monitoring_provider == "cloudwatch" ? 1 : 0
  alarm_name          = "${var.cluster_name}-memory-usage-high"
  alarm_description   = "Redis cluster memory usage exceeds ${local.memory_usage_critical_threshold}%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Average"
  threshold           = local.memory_usage_critical_threshold
  treat_missing_data  = "missing"
  
  dimensions = {
    CacheClusterId = var.cluster_id
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
  
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-memory-usage-high"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "redis_memory_usage_warning" {
  count               = local.monitoring_provider == "cloudwatch" ? 1 : 0
  alarm_name          = "${var.cluster_name}-memory-usage-warning"
  alarm_description   = "Redis cluster memory usage exceeds ${local.memory_usage_warning_threshold}%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Average"
  threshold           = local.memory_usage_warning_threshold
  treat_missing_data  = "missing"
  
  dimensions = {
    CacheClusterId = var.cluster_id
  }
  
  alarm_actions = var.warning_alarm_actions
  ok_actions    = var.ok_actions
  
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-memory-usage-warning"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  count               = local.monitoring_provider == "cloudwatch" ? 1 : 0
  alarm_name          = "${var.cluster_name}-evictions-high"
  alarm_description   = "Redis cluster eviction rate exceeds ${local.eviction_rate_threshold} per second"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Sum"
  threshold           = local.eviction_rate_threshold * 60  # Convert to per minute for the 60s period
  treat_missing_data  = "missing"
  
  dimensions = {
    CacheClusterId = var.cluster_id
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
  
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-evictions-high"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu_usage" {
  count               = local.monitoring_provider == "cloudwatch" ? 1 : 0
  alarm_name          = "${var.cluster_name}-cpu-usage-high"
  alarm_description   = "Redis cluster CPU usage exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "EngineCPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "missing"
  
  dimensions = {
    CacheClusterId = var.cluster_id
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
  
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-cpu-usage-high"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  count               = local.monitoring_provider == "cloudwatch" ? 1 : 0
  alarm_name          = "${var.cluster_name}-connections-high"
  alarm_description   = "Redis cluster connection count exceeds ${local.connection_count_threshold}% of maximum"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Average"
  threshold           = var.max_connections * (local.connection_count_threshold / 100.0)
  treat_missing_data  = "missing"
  
  dimensions = {
    CacheClusterId = var.cluster_id
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
  
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-connections-high"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "redis_replication_lag" {
  count               = local.monitoring_provider == "cloudwatch" && var.enable_replication ? 1 : 0
  alarm_name          = "${var.cluster_name}-replication-lag-high"
  alarm_description   = "Redis cluster replication lag exceeds 10 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ReplicationLag"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Average"
  threshold           = 10
  treat_missing_data  = "missing"
  
  dimensions = {
    CacheClusterId = var.cluster_id
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
  
  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-replication-lag-high"
    }
  )
}

# CloudWatch Dashboard for Redis metrics
resource "aws_cloudwatch_dashboard" "redis_dashboard" {
  count          = local.monitoring_provider == "cloudwatch" ? 1 : 0
  dashboard_name = local.dashboard_name
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
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "CacheClusterId", var.cluster_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Memory Usage Percentage"
          period  = 60
          stat    = "Average"
          annotations = {
            horizontal = [
              {
                value = local.memory_usage_warning_threshold
                label = "Warning Threshold"
                color = "#ff9900"
              },
              {
                value = local.memory_usage_critical_threshold
                label = "Critical Threshold"
                color = "#ff0000"
              }
            ]
          }
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
            ["AWS/ElastiCache", "Evictions", "CacheClusterId", var.cluster_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Eviction Rate"
          period  = 60
          stat    = "Sum"
          annotations = {
            horizontal = [
              {
                value = local.eviction_rate_threshold * 60
                label = "Threshold"
                color = "#ff0000"
              }
            ]
          }
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
            ["AWS/ElastiCache", "EngineCPUUtilization", "CacheClusterId", var.cluster_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "CPU Utilization"
          period  = 60
          stat    = "Average"
          annotations = {
            horizontal = [
              {
                value = 80
                label = "Threshold"
                color = "#ff0000"
              }
            ]
          }
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
            ["AWS/ElastiCache", "CurrConnections", "CacheClusterId", var.cluster_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Current Connections"
          period  = 60
          stat    = "Average"
          annotations = {
            horizontal = [
              {
                value = var.max_connections * (local.connection_count_threshold / 100.0)
                label = "Threshold"
                color = "#ff0000"
              }
            ]
          }
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
            ["AWS/ElastiCache", "CacheHits", "CacheClusterId", var.cluster_id],
            ["AWS/ElastiCache", "CacheMisses", "CacheClusterId", var.cluster_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Cache Hits/Misses"
          period  = 60
          stat    = "Sum"
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
            ["AWS/ElastiCache", "NetworkBytesIn", "CacheClusterId", var.cluster_id],
            ["AWS/ElastiCache", "NetworkBytesOut", "CacheClusterId", var.cluster_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Network Traffic"
          period  = 60
          stat    = "Sum"
        }
      }
    ]
  })
}

# Prometheus Redis Exporter Configuration
resource "kubernetes_deployment" "redis_exporter" {
  count = local.monitoring_provider == "prometheus" ? 1 : 0
  
  metadata {
    name      = "${var.cluster_name}-redis-exporter"
    namespace = var.monitoring_namespace
    labels = {
      app = "${var.cluster_name}-redis-exporter"
    }
  }
  
  spec {
    replicas = 1
    
    selector {
      match_labels = {
        app = "${var.cluster_name}-redis-exporter"
      }
    }
    
    template {
      metadata {
        labels = {
          app = "${var.cluster_name}-redis-exporter"
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9121"
        }
      }
      
      spec {
        container {
          name  = "redis-exporter"
          image = "oliver006/redis_exporter:v1.43.1"
          
          env {
            name  = "REDIS_ADDR"
            value = "redis://${var.redis_host}:${var.redis_port}"
          }
          
          dynamic "env" {
            for_each = var.redis_password != "" ? [1] : []
            content {
              name = "REDIS_PASSWORD"
              value_from {
                secret_key_ref {
                  name = var.redis_password_secret_name
                  key  = var.redis_password_secret_key
                }
              }
            }
          }
          
          port {
            container_port = 9121
            name           = "http"
          }
          
          resources {
            limits = {
              cpu    = "100m"
              memory = "128Mi"
            }
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
          }
          
          liveness_probe {
            http_get {
              path = "/"
              port = 9121
            }
            initial_delay_seconds = 30
            timeout_seconds       = 5
            period_seconds        = 10
          }
          
          readiness_probe {
            http_get {
              path = "/"
              port = 9121
            }
            initial_delay_seconds = 10
            timeout_seconds       = 5
            period_seconds        = 10
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "redis_exporter" {
  count = local.monitoring_provider == "prometheus" ? 1 : 0
  
  metadata {
    name      = "${var.cluster_name}-redis-exporter"
    namespace = var.monitoring_namespace
    labels = {
      app = "${var.cluster_name}-redis-exporter"
    }
  }
  
  spec {
    selector = {
      app = "${var.cluster_name}-redis-exporter"
    }
    
    port {
      port        = 9121
      target_port = 9121
      name        = "http"
    }
  }
}

# Prometheus ServiceMonitor for Redis Exporter (if using Prometheus Operator)
resource "kubernetes_manifest" "redis_service_monitor" {
  count = local.monitoring_provider == "prometheus" && var.enable_service_monitor ? 1 : 0
  
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    
    metadata = {
      name      = "${var.cluster_name}-redis-exporter"
      namespace = var.monitoring_namespace
      labels = {
        release = var.prometheus_release_name
      }
    }
    
    spec = {
      selector = {
        matchLabels = {
          app = "${var.cluster_name}-redis-exporter"
        }
      }
      endpoints = [
        {
          port     = "http"
          interval = "30s"
        }
      ]
    }
  }
}

# Prometheus Alert Rules for Redis
resource "kubernetes_manifest" "redis_prometheus_rules" {
  count = local.monitoring_provider == "prometheus" && var.enable_prometheus_rules ? 1 : 0
  
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "PrometheusRule"
    
    metadata = {
      name      = "${var.cluster_name}-redis-rules"
      namespace = var.monitoring_namespace
      labels = {
        release = var.prometheus_release_name
      }
    }
    
    spec = {
      groups = [
        {
          name = "redis.rules"
          rules = [
            {
              alert = "RedisDown"
              expr  = "redis_up == 0"
              for   = "1m"
              labels = {
                severity = "critical"
              }
              annotations = {
                summary     = "Redis instance {{ $labels.instance }} is down"
                description = "Redis instance {{ $labels.instance }} has been down for more than 1 minute."
              }
            },
            {
              alert = "RedisMemoryHigh"
              expr  = "redis_memory_used_bytes / redis_memory_max_bytes * 100 > ${local.memory_usage_critical_threshold}"
              for   = "5m"
              labels = {
                severity = "critical"
              }
              annotations = {
                summary     = "Redis memory usage is high"
                description = "Redis instance {{ $labels.instance }} memory usage is above ${local.memory_usage_critical_threshold}% (current value: {{ $value }}%)."
              }
            },
            {
              alert = "RedisMemoryWarning"
              expr  = "redis_memory_used_bytes / redis_memory_max_bytes * 100 > ${local.memory_usage_warning_threshold}"
              for   = "5m"
              labels = {
                severity = "warning"
              }
              annotations = {
                summary     = "Redis memory usage warning"
                description = "Redis instance {{ $labels.instance }} memory usage is above ${local.memory_usage_warning_threshold}% (current value: {{ $value }}%)."
              }
            },
            {
              alert = "RedisHighEvictionRate"
              expr  = "rate(redis_evicted_keys_total[1m]) > ${local.eviction_rate_threshold / 60.0}"
              for   = "5m"
              labels = {
                severity = "warning"
              }
              annotations = {
                summary     = "Redis high eviction rate"
                description = "Redis instance {{ $labels.instance }} has a high eviction rate (current value: {{ $value }} keys/sec)."
              }
            },
            {
              alert = "RedisHighConnectionCount"
              expr  = "redis_connected_clients / redis_config_maxclients * 100 > ${local.connection_count_threshold}"
              for   = "5m"
              labels = {
                severity = "warning"
              }
              annotations = {
                summary     = "Redis high connection count"
                description = "Redis instance {{ $labels.instance }} has a high number of connections (current value: {{ $value }}% of max)."
              }
            }
          ]
        }
      ]
    }
  }
}

# Variables for the module
variable "cluster_name" {
  description = "Name of the Redis cluster"
  type        = string
}

variable "cluster_id" {
  description = "ID of the Redis cluster for CloudWatch metrics"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name (e.g., production, staging, development)"
  type        = string
  default     = ""
}

variable "monitoring_provider" {
  description = "Monitoring provider to use (cloudwatch or prometheus)"
  type        = string
  default     = "cloudwatch"
}

variable "aws_region" {
  description = "AWS region for CloudWatch resources"
  type        = string
  default     = "us-east-1"
}

variable "alarm_actions" {
  description = "List of ARNs to notify when alarm transitions to ALARM state"
  type        = list(string)
  default     = []
}

variable "warning_alarm_actions" {
  description = "List of ARNs to notify when warning alarm transitions to ALARM state"
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "List of ARNs to notify when alarm transitions to OK state"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "max_connections" {
  description = "Maximum number of connections allowed to Redis"
  type        = number
  default     = 1000
}

variable "enable_replication" {
  description = "Whether Redis replication is enabled"
  type        = bool
  default     = false
}

variable "monitoring_namespace" {
  description = "Kubernetes namespace for monitoring resources"
  type        = string
  default     = "monitoring"
}

variable "redis_host" {
  description = "Redis host address for Prometheus exporter"
  type        = string
  default     = "localhost"
}

variable "redis_port" {
  description = "Redis port for Prometheus exporter"
  type        = number
  default     = 6379
}

variable "redis_password" {
  description = "Redis password for Prometheus exporter (leave empty if no password)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "redis_password_secret_name" {
  description = "Name of the Kubernetes secret containing the Redis password"
  type        = string
  default     = "redis-credentials"
}

variable "redis_password_secret_key" {
  description = "Key in the Kubernetes secret containing the Redis password"
  type        = string
  default     = "redis-password"
}

variable "enable_service_monitor" {
  description = "Whether to create a ServiceMonitor for Prometheus Operator"
  type        = bool
  default     = true
}

variable "enable_prometheus_rules" {
  description = "Whether to create PrometheusRules for alerting"
  type        = bool
  default     = true
}

variable "prometheus_release_name" {
  description = "Name of the Prometheus release for ServiceMonitor and PrometheusRule labels"
  type        = string
  default     = "prometheus"
}