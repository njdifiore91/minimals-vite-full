# Prometheus and Grafana Monitoring Stack for MCA Application Processing System
# This file provisions a self-hosted Prometheus and Grafana monitoring stack on Kubernetes
# when selected as the monitoring solution.

# Kubernetes provider configuration - uses the kubernetes provider that should be configured in the root module
data "kubernetes_namespace" "monitoring" {
  count = var.create_namespace ? 0 : 1
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_namespace" "monitoring" {
  count = var.create_namespace ? 1 : 0
  metadata {
    name = var.namespace
    labels = merge({
      name = var.namespace
      "kubernetes.io/metadata.name" = var.namespace
    }, var.namespace_labels)
  }
}

locals {
  namespace = var.create_namespace ? kubernetes_namespace.monitoring[0].metadata[0].name : data.kubernetes_namespace.monitoring[0].metadata[0].name
  
  # Common labels to apply to all resources
  common_labels = {
    "app.kubernetes.io/managed-by" = "terraform"
    "app.kubernetes.io/part-of"    = "mca-monitoring"
  }
  
  # Storage configuration
  prometheus_storage = {
    enabled      = var.prometheus_storage_enabled
    storageClass = var.prometheus_storage_class
    size         = var.prometheus_storage_size
    retention    = var.prometheus_retention_period
  }
  
  grafana_storage = {
    enabled      = var.grafana_storage_enabled
    storageClass = var.grafana_storage_class
    size         = var.grafana_storage_size
  }
  
  # Service monitor selectors
  service_monitor_selector = {
    matchLabels = {
      "prometheus.io/scrape" = "true"
    }
  }
}

# Prometheus Operator Helm Chart
# This deploys the kube-prometheus-stack which includes:
# - Prometheus Operator
# - Prometheus Server
# - Alertmanager
# - Grafana
# - Node Exporter
# - Kube State Metrics
resource "helm_release" "prometheus" {
  name       = var.prometheus_release_name
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.prometheus_chart_version
  namespace  = local.namespace
  
  timeout    = 600
  
  values = [
    yamlencode({
      fullnameOverride = var.prometheus_release_name
      
      # Global settings
      global = {
        rbac = {
          create     = true
          pspEnabled = false
        }
        evaluation_interval = "30s"
        scrape_interval     = "30s"
      }
      
      # Prometheus Operator configuration
      prometheusOperator = {
        enabled = true
        createCustomResource = true
        manageCrds = true
        image = {
          repository = "quay.io/prometheus-operator/prometheus-operator"
          tag        = var.prometheus_operator_version
          pullPolicy = "IfNotPresent"
        }
        resources = var.prometheus_operator_resources
        securityContext = {
          runAsNonRoot = true
          runAsUser    = 65534
          fsGroup      = 65534
        }
      }
      
      # Prometheus Server configuration
      prometheus = {
        enabled = true
        serviceMonitorSelector = local.service_monitor_selector
        podMonitorSelector = local.service_monitor_selector
        
        prometheusSpec = {
          image = {
            repository = "quay.io/prometheus/prometheus"
            tag        = var.prometheus_version
          }
          retention     = local.prometheus_storage.retention
          scrapeInterval = "30s"
          evaluationInterval = "30s"
          
          # Storage configuration
          storageSpec = local.prometheus_storage.enabled ? {
            volumeClaimTemplate = {
              spec = {
                storageClassName = local.prometheus_storage.storageClass
                accessModes      = ["ReadWriteOnce"]
                resources = {
                  requests = {
                    storage = local.prometheus_storage.size
                  }
                }
              }
            }
          } : null
          
          # Resource configuration
          resources = var.prometheus_resources
          
          # Security configuration
          securityContext = {
            runAsNonRoot = true
            runAsUser    = 65534
            fsGroup      = 65534
          }
          
          # External labels for Alertmanager
          externalLabels = {
            cluster = var.cluster_name
            environment = var.environment
          }
          
          # Additional scrape configs for custom exporters
          additionalScrapeConfigs = var.additional_scrape_configs
        }
      }
      
      # Alertmanager configuration
      alertmanager = {
        enabled = true
        config = {
          global = {
            resolve_timeout = "5m"
          }
          route = {
            group_by        = ["alertname", "job"]
            group_wait      = "30s"
            group_interval  = "5m"
            repeat_interval = "12h"
            receiver        = "null"
            routes          = []
          }
          receivers = [
            {
              name = "null"
            }
          ]
        }
        
        alertmanagerSpec = {
          image = {
            repository = "quay.io/prometheus/alertmanager"
            tag        = var.alertmanager_version
          }
          
          # Storage configuration
          storage = {
            volumeClaimTemplate = {
              spec = {
                storageClassName = local.prometheus_storage.storageClass
                accessModes      = ["ReadWriteOnce"]
                resources = {
                  requests = {
                    storage = "5Gi"
                  }
                }
              }
            }
          }
          
          # Resource configuration
          resources = var.alertmanager_resources
          
          # Security configuration
          securityContext = {
            runAsNonRoot = true
            runAsUser    = 65534
            fsGroup      = 65534
          }
        }
      }
      
      # Grafana configuration
      grafana = {
        enabled = true
        image = {
          repository = "grafana/grafana"
          tag        = var.grafana_version
        }
        
        # Admin credentials
        adminPassword = var.grafana_admin_password
        
        # Persistence configuration
        persistence = {
          enabled          = local.grafana_storage.enabled
          storageClassName = local.grafana_storage.storageClass
          size             = local.grafana_storage.size
        }
        
        # Resource configuration
        resources = var.grafana_resources
        
        # Security configuration
        securityContext = {
          runAsNonRoot = true
          runAsUser    = 472
          fsGroup      = 472
        }
        
        # Service configuration
        service = {
          type = var.grafana_service_type
          port = 80
        }
        
        # Ingress configuration
        ingress = {
          enabled = var.grafana_ingress_enabled
          annotations = var.grafana_ingress_annotations
          hosts = var.grafana_ingress_hosts
          tls = var.grafana_ingress_tls
        }
        
        # Datasources configuration
        datasources = {
          "datasources.yaml" = {
            apiVersion = 1
            datasources = [
              {
                name      = "Prometheus"
                type      = "prometheus"
                url       = "http://prometheus-server"
                access    = "proxy"
                isDefault = true
              }
            ]
          }
        }
        
        # Dashboards configuration
        dashboardProviders = {
          "dashboardproviders.yaml" = {
            apiVersion = 1
            providers = [
              {
                name = "default"
                orgId = 1
                folder = ""
                type = "file"
                disableDeletion = false
                editable = true
                options = {
                  path = "/var/lib/grafana/dashboards/default"
                }
              }
            ]
          }
        }
        
        # Default dashboards
        dashboards = {
          default = {
            # Node Exporter dashboard
            node-exporter = {
              gnetId = 1860
              revision = 22
              datasource = "Prometheus"
            }
            # Kubernetes cluster monitoring dashboard
            kubernetes-cluster = {
              gnetId = 7249
              revision = 1
              datasource = "Prometheus"
            }
            # PostgreSQL dashboard
            postgresql = {
              gnetId = 9628
              revision = 7
              datasource = "Prometheus"
            }
            # RabbitMQ dashboard
            rabbitmq = {
              gnetId = 10991
              revision = 9
              datasource = "Prometheus"
            }
            # Redis dashboard
            redis = {
              gnetId = 763
              revision = 4
              datasource = "Prometheus"
            }
            # Custom MCA Application dashboard
            mca-application = {
              file = file("${path.module}/dashboards/mca-application.json")
            }
          }
        }
        
        # Grafana plugins
        plugins = [
          "grafana-piechart-panel",
          "grafana-worldmap-panel",
          "grafana-clock-panel"
        ]
        
        # Additional configuration
        grafana_ini = {
          server = {
            root_url = var.grafana_root_url
          }
          auth = {
            disable_login_form = var.grafana_disable_login_form
          }
          "auth.anonymous" = {
            enabled = var.grafana_anonymous_enabled
          }
          analytics = {
            check_for_updates = false
          }
        }
      }
      
      # Node Exporter configuration
      nodeExporter = {
        enabled = true
        serviceMonitor = {
          relabelings = [
            {
              action = "replace"
              regex = "(.*)"
              replacement = "$1"
              sourceLabels = ["__meta_kubernetes_pod_node_name"]
              targetLabel = "instance"
            }
          ]
        }
      }
      
      # Kube State Metrics configuration
      kubeStateMetrics = {
        enabled = true
      }
    })
  ]
  
  # Depends on namespace
  depends_on = [
    kubernetes_namespace.monitoring
  ]
}

# PostgreSQL Exporter
# This deploys a PostgreSQL exporter to collect metrics from PostgreSQL databases
resource "helm_release" "postgres_exporter" {
  count      = var.postgres_exporter_enabled ? 1 : 0
  name       = "postgres-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-postgres-exporter"
  version    = var.postgres_exporter_version
  namespace  = local.namespace
  
  values = [
    yamlencode({
      # PostgreSQL connection settings
      config = {
        datasource = {
          host            = var.postgres_host
          port            = var.postgres_port
          user            = var.postgres_user
          passwordSecret  = {
            name = "postgres-exporter"
            key  = "password"
          }
          database        = var.postgres_database
          sslmode         = "require"
        }
        queries = file("${path.module}/queries/postgres-queries.yaml")
      }
      
      # Service monitor for Prometheus
      serviceMonitor = {
        enabled = true
        labels = local.service_monitor_selector.matchLabels
        interval = "30s"
        scrapeTimeout = "10s"
      }
      
      # Resource configuration
      resources = var.postgres_exporter_resources
      
      # Security configuration
      securityContext = {
        runAsNonRoot = true
        runAsUser    = 65534
        fsGroup      = 65534
      }
    })
  ]
  
  # Create secret for PostgreSQL password
  set_sensitive {
    name  = "config.datasource.password"
    value = var.postgres_password
  }
  
  # Depends on Prometheus operator
  depends_on = [
    helm_release.prometheus
  ]
}

# RabbitMQ Exporter
# This deploys a RabbitMQ exporter to collect metrics from RabbitMQ
resource "helm_release" "rabbitmq_exporter" {
  count      = var.rabbitmq_exporter_enabled ? 1 : 0
  name       = "rabbitmq-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-rabbitmq-exporter"
  version    = var.rabbitmq_exporter_version
  namespace  = local.namespace
  
  values = [
    yamlencode({
      # RabbitMQ connection settings
      rabbitmq = {
        url = "http://${var.rabbitmq_host}:${var.rabbitmq_port}"
        user = var.rabbitmq_user
        passwordSecret = {
          name = "rabbitmq-exporter"
          key  = "password"
        }
      }
      
      # Service monitor for Prometheus
      serviceMonitor = {
        enabled = true
        labels = local.service_monitor_selector.matchLabels
        interval = "30s"
        scrapeTimeout = "10s"
      }
      
      # Resource configuration
      resources = var.rabbitmq_exporter_resources
      
      # Security configuration
      securityContext = {
        runAsNonRoot = true
        runAsUser    = 65534
        fsGroup      = 65534
      }
    })
  ]
  
  # Create secret for RabbitMQ password
  set_sensitive {
    name  = "rabbitmq.password"
    value = var.rabbitmq_password
  }
  
  # Depends on Prometheus operator
  depends_on = [
    helm_release.prometheus
  ]
}

# Redis Exporter
# This deploys a Redis exporter to collect metrics from Redis
resource "helm_release" "redis_exporter" {
  count      = var.redis_exporter_enabled ? 1 : 0
  name       = "redis-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-redis-exporter"
  version    = var.redis_exporter_version
  namespace  = local.namespace
  
  values = [
    yamlencode({
      # Redis connection settings
      redisAddress = "redis://${var.redis_host}:${var.redis_port}"
      
      # Authentication settings
      auth = {
        enabled = var.redis_password != ""
        secret = {
          name = "redis-exporter"
          key  = "password"
        }
      }
      
      # Service monitor for Prometheus
      serviceMonitor = {
        enabled = true
        labels = local.service_monitor_selector.matchLabels
        interval = "30s"
        scrapeTimeout = "10s"
      }
      
      # Resource configuration
      resources = var.redis_exporter_resources
      
      # Security configuration
      securityContext = {
        runAsNonRoot = true
        runAsUser    = 65534
        fsGroup      = 65534
      }
    })
  ]
  
  # Create secret for Redis password if needed
  dynamic "set_sensitive" {
    for_each = var.redis_password != "" ? [1] : []
    content {
      name  = "auth.redisPassword"
      value = var.redis_password
    }
  }
  
  # Depends on Prometheus operator
  depends_on = [
    helm_release.prometheus
  ]
}

# Service Monitors for MCA Application Services
# These resources define how Prometheus should scrape metrics from the MCA application services

# Email Service Monitor
resource "kubernetes_manifest" "email_service_monitor" {
  count = var.email_service_monitor_enabled ? 1 : 0
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "email-service-monitor"
      namespace = local.namespace
      labels    = merge(local.common_labels, local.service_monitor_selector.matchLabels)
    }
    spec = {
      selector = {
        matchLabels = {
          app = "email-service"
        }
      }
      endpoints = [
        {
          port       = "metrics"
          interval   = "30s"
          path       = "/metrics"
          honorLabels = true
        }
      ]
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}

# Document Service Monitor
resource "kubernetes_manifest" "document_service_monitor" {
  count = var.document_service_monitor_enabled ? 1 : 0
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "document-service-monitor"
      namespace = local.namespace
      labels    = merge(local.common_labels, local.service_monitor_selector.matchLabels)
    }
    spec = {
      selector = {
        matchLabels = {
          app = "document-service"
        }
      }
      endpoints = [
        {
          port       = "metrics"
          interval   = "30s"
          path       = "/metrics"
          honorLabels = true
        }
      ]
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}

# OCR Service Monitor
resource "kubernetes_manifest" "ocr_service_monitor" {
  count = var.ocr_service_monitor_enabled ? 1 : 0
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "ocr-service-monitor"
      namespace = local.namespace
      labels    = merge(local.common_labels, local.service_monitor_selector.matchLabels)
    }
    spec = {
      selector = {
        matchLabels = {
          app = "ocr-service"
        }
      }
      endpoints = [
        {
          port       = "metrics"
          interval   = "30s"
          path       = "/metrics"
          honorLabels = true
        }
      ]
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}

# Data Service Monitor
resource "kubernetes_manifest" "data_service_monitor" {
  count = var.data_service_monitor_enabled ? 1 : 0
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "data-service-monitor"
      namespace = local.namespace
      labels    = merge(local.common_labels, local.service_monitor_selector.matchLabels)
    }
    spec = {
      selector = {
        matchLabels = {
          app = "data-service"
        }
      }
      endpoints = [
        {
          port       = "metrics"
          interval   = "30s"
          path       = "/actuator/prometheus"
          honorLabels = true
        }
      ]
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}

# Notification Service Monitor
resource "kubernetes_manifest" "notification_service_monitor" {
  count = var.notification_service_monitor_enabled ? 1 : 0
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "notification-service-monitor"
      namespace = local.namespace
      labels    = merge(local.common_labels, local.service_monitor_selector.matchLabels)
    }
    spec = {
      selector = {
        matchLabels = {
          app = "notification-service"
        }
      }
      endpoints = [
        {
          port       = "metrics"
          interval   = "30s"
          path       = "/metrics"
          honorLabels = true
        }
      ]
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}

# API Gateway Service Monitor
resource "kubernetes_manifest" "api_gateway_service_monitor" {
  count = var.api_gateway_service_monitor_enabled ? 1 : 0
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "api-gateway-monitor"
      namespace = local.namespace
      labels    = merge(local.common_labels, local.service_monitor_selector.matchLabels)
    }
    spec = {
      selector = {
        matchLabels = {
          app = "api-gateway"
        }
      }
      endpoints = [
        {
          port       = "metrics"
          interval   = "30s"
          path       = "/metrics"
          honorLabels = true
        }
      ]
      namespaceSelector = {
        matchNames = [var.app_namespace]
      }
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}

# S3 Metrics Configuration
# For S3 metrics, we rely on CloudWatch metrics exported to Prometheus
# This is handled through the CloudWatch exporter if AWS is used as the cloud provider
resource "helm_release" "cloudwatch_exporter" {
  count      = var.cloudwatch_exporter_enabled ? 1 : 0
  name       = "cloudwatch-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-cloudwatch-exporter"
  version    = var.cloudwatch_exporter_version
  namespace  = local.namespace
  
  values = [
    yamlencode({
      # AWS credentials
      aws = {
        role = var.cloudwatch_exporter_role
        region = var.aws_region
      }
      
      # CloudWatch metrics configuration
      config = {
        region = var.aws_region
        period_seconds = 300
        metrics = [
          {
            aws_namespace = "AWS/S3"
            aws_metric_name = "BucketSizeBytes"
            aws_dimensions = ["BucketName", "StorageType"]
            aws_statistics = ["Average"]
          },
          {
            aws_namespace = "AWS/S3"
            aws_metric_name = "NumberOfObjects"
            aws_dimensions = ["BucketName", "StorageType"]
            aws_statistics = ["Average"]
          },
          {
            aws_namespace = "AWS/S3"
            aws_metric_name = "AllRequests"
            aws_dimensions = ["BucketName"]
            aws_statistics = ["Sum"]
          },
          {
            aws_namespace = "AWS/S3"
            aws_metric_name = "4xxErrors"
            aws_dimensions = ["BucketName"]
            aws_statistics = ["Sum"]
          },
          {
            aws_namespace = "AWS/S3"
            aws_metric_name = "5xxErrors"
            aws_dimensions = ["BucketName"]
            aws_statistics = ["Sum"]
          }
        ]
      }
      
      # Service monitor for Prometheus
      serviceMonitor = {
        enabled = true
        labels = local.service_monitor_selector.matchLabels
        interval = "5m"
        scrapeTimeout = "30s"
      }
      
      # Resource configuration
      resources = var.cloudwatch_exporter_resources
      
      # Security configuration
      securityContext = {
        runAsNonRoot = true
        runAsUser    = 65534
        fsGroup      = 65534
      }
    })
  ]
  
  # Depends on Prometheus operator
  depends_on = [
    helm_release.prometheus
  ]
}

# Custom Prometheus Rules for MCA Application
resource "kubernetes_manifest" "mca_prometheus_rules" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "PrometheusRule"
    metadata = {
      name      = "mca-application-rules"
      namespace = local.namespace
      labels    = merge(local.common_labels, {
        "prometheus.io/scrape" = "true"
        "role" = "alert-rules"
      })
    }
    spec = {
      groups = [
        {
          name = "mca.application.processing"
          rules = [
            {
              alert = "MCAApplicationProcessingTime"
              expr = "histogram_quantile(0.95, sum(rate(application_processing_time_seconds_bucket[5m])) by (le)) > ${var.sla_processing_time_threshold}"
              for = "5m"
              labels = {
                severity = "warning"
                team     = "operations"
              }
              annotations = {
                summary = "MCA Application processing time exceeds SLA"
                description = "95th percentile of application processing time is above ${var.sla_processing_time_threshold} seconds for the last 5 minutes."
              }
            },
            {
              alert = "MCAOCRAccuracyLow"
              expr = "avg(ocr_extraction_accuracy) < ${var.ocr_accuracy_threshold}"
              for = "15m"
              labels = {
                severity = "warning"
                team     = "data-science"
              }
              annotations = {
                summary = "OCR extraction accuracy below threshold"
                description = "Average OCR extraction accuracy is below ${var.ocr_accuracy_threshold}% for the last 15 minutes."
              }
            },
            {
              alert = "MCAQueueDepthHigh"
              expr = "sum(rabbitmq_queue_messages{queue=~"document-processing|data-extraction|notification"}) by (queue) > ${var.queue_depth_threshold}"
              for = "10m"
              labels = {
                severity = "warning"
                team     = "engineering"
              }
              annotations = {
                summary = "RabbitMQ queue depth is high"
                description = "Queue {{ $labels.queue }} has more than ${var.queue_depth_threshold} messages for the last 10 minutes."
              }
            },
            {
              alert = "MCAAPIResponseTimeSlow"
              expr = "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{handler=~"/api/v1/.*"}[5m])) by (handler, le)) > ${var.api_response_time_threshold}"
              for = "5m"
              labels = {
                severity = "warning"
                team     = "engineering"
              }
              annotations = {
                summary = "API response time is slow"
                description = "95th percentile of API response time for {{ $labels.handler }} is above ${var.api_response_time_threshold} seconds for the last 5 minutes."
              }
            }
          ]
        },
        {
          name = "mca.infrastructure"
          rules = [
            {
              alert = "MCADatabaseConnectionPoolSaturation"
              expr = "max(hikaricp_connections_active / hikaricp_connections_max) by (pool) > 0.8"
              for = "5m"
              labels = {
                severity = "warning"
                team     = "infrastructure"
              }
              annotations = {
                summary = "Database connection pool nearing saturation"
                description = "Connection pool {{ $labels.pool }} is more than 80% utilized for the last 5 minutes."
              }
            },
            {
              alert = "MCARedisMemoryHigh"
              expr = "redis_memory_used_bytes / redis_memory_max_bytes > 0.8"
              for = "5m"
              labels = {
                severity = "warning"
                team     = "infrastructure"
              }
              annotations = {
                summary = "Redis memory usage is high"
                description = "Redis memory usage is above 80% for the last 5 minutes."
              }
            },
            {
              alert = "MCANodeResourcesExhausted"
              expr = "(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.1 or (node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"}) < 0.1"
              for = "5m"
              labels = {
                severity = "critical"
                team     = "infrastructure"
              }
              annotations = {
                summary = "Node resources are exhausted"
                description = "Node {{ $labels.instance }} has less than 10% memory or disk space available for the last 5 minutes."
              }
            }
          ]
        }
      ]
    }
  }
  
  depends_on = [
    helm_release.prometheus
  ]
}