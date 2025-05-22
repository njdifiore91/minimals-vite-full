# Prometheus Terraform Configuration for MCA Application Processing System
# This file provisions a self-hosted Prometheus and Grafana monitoring stack on Kubernetes
# when selected as the monitoring solution.

# Only deploy Prometheus resources if monitoring_type is "prometheus"
locals {
  prometheus_enabled = var.monitoring_type == "prometheus"
  
  # Common labels for all resources
  common_labels = {
    app         = "mca-monitoring"
    environment = var.environment
    managed_by  = "terraform"
  }
  
  # Default storage sizes based on environment
  prometheus_storage_size = {
    development = "10Gi"
    staging     = "20Gi"
    production  = "50Gi"
  }
  
  grafana_storage_size = {
    development = "5Gi"
    staging     = "10Gi"
    production  = "20Gi"
  }
  
  # Retention configuration based on environment
  prometheus_retention = {
    development = "7d"
    staging     = "15d"
    production  = "30d"
  }
}

# Deploy Prometheus Operator using Helm
resource "helm_release" "prometheus_operator" {
  count      = local.prometheus_enabled ? 1 : 0
  name       = "prometheus-operator"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.prometheus_operator_version
  namespace  = var.monitoring_namespace
  
  create_namespace = true
  
  # Wait for CRDs to be applied before creating resources that use them
  wait = true
  
  values = [
    <<-EOT
    # Global configuration
    global:
      evaluation_interval: "30s"
      scrape_interval: "30s"
      scrape_timeout: "10s"
      external_labels:
        environment: ${var.environment}
        cluster: ${var.cluster_name}
    
    # Prometheus server configuration
    prometheus:
      prometheusSpec:
        replicas: ${var.environment == "production" ? 2 : 1}
        retention: ${lookup(local.prometheus_retention, var.environment, "15d")}
        serviceMonitorSelector:
          matchLabels:
            app: "mca-monitoring"
        podMonitorSelector:
          matchLabels:
            app: "mca-monitoring"
        ruleSelector:
          matchLabels:
            app: "mca-monitoring"
        storageSpec:
          volumeClaimTemplate:
            spec:
              storageClassName: ${var.storage_class_name}
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: ${lookup(local.prometheus_storage_size, var.environment, "20Gi")}
        resources:
          requests:
            cpu: ${var.environment == "production" ? "500m" : "200m"}
            memory: ${var.environment == "production" ? "2Gi" : "1Gi"}
          limits:
            cpu: ${var.environment == "production" ? "1000m" : "500m"}
            memory: ${var.environment == "production" ? "4Gi" : "2Gi"}
        securityContext:
          fsGroup: 65534
          runAsGroup: 65534
          runAsNonRoot: true
          runAsUser: 65534
        additionalScrapeConfigs:
          - job_name: 's3-exporter'
            static_configs:
              - targets: ['s3-exporter:9340']
    
    # Grafana configuration
    grafana:
      enabled: true
      adminPassword: ${var.grafana_admin_password}
      persistence:
        enabled: true
        storageClassName: ${var.storage_class_name}
        size: ${lookup(local.grafana_storage_size, var.environment, "10Gi")}
      resources:
        requests:
          cpu: ${var.environment == "production" ? "200m" : "100m"}
          memory: ${var.environment == "production" ? "256Mi" : "128Mi"}
        limits:
          cpu: ${var.environment == "production" ? "500m" : "200m"}
          memory: ${var.environment == "production" ? "512Mi" : "256Mi"}
      plugins:
        - grafana-piechart-panel
        - grafana-worldmap-panel
        - grafana-clock-panel
      dashboardProviders:
        dashboardproviders.yaml:
          apiVersion: 1
          providers:
            - name: 'mca-dashboards'
              orgId: 1
              folder: 'MCA Application'
              type: file
              disableDeletion: false
              editable: true
              options:
                path: /var/lib/grafana/dashboards/mca
      dashboardsConfigMaps:
        mca-dashboards: "${var.grafana_dashboards_configmap}"
      sidecar:
        dashboards:
          enabled: true
          label: grafana_dashboard
          searchNamespace: ALL
      ingress:
        enabled: ${var.grafana_ingress_enabled}
        annotations:
          kubernetes.io/ingress.class: ${var.ingress_class}
          cert-manager.io/cluster-issuer: ${var.cert_issuer}
        hosts:
          - ${var.grafana_hostname}
        tls:
          - secretName: grafana-tls
            hosts:
              - ${var.grafana_hostname}
    
    # Alert manager configuration
    alertmanager:
      enabled: true
      alertmanagerSpec:
        replicas: ${var.environment == "production" ? 2 : 1}
        storage:
          volumeClaimTemplate:
            spec:
              storageClassName: ${var.storage_class_name}
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: ${var.environment == "production" ? "10Gi" : "5Gi"}
        resources:
          requests:
            cpu: ${var.environment == "production" ? "100m" : "50m"}
            memory: ${var.environment == "production" ? "256Mi" : "128Mi"}
          limits:
            cpu: ${var.environment == "production" ? "200m" : "100m"}
            memory: ${var.environment == "production" ? "512Mi" : "256Mi"}
    
    # Node exporter configuration
    nodeExporter:
      enabled: true
      serviceMonitor:
        relabelings:
          - action: replace
            regex: (.*)
            replacement: $1
            sourceLabels:
              - __meta_kubernetes_pod_node_name
            targetLabel: instance
    
    # kube-state-metrics configuration
    kubeStateMetrics:
      enabled: true
    
    # Prometheus Operator configuration
    prometheusOperator:
      enabled: true
      manageCrds: true
      createCustomResource: true
      resources:
        requests:
          cpu: ${var.environment == "production" ? "100m" : "50m"}
          memory: ${var.environment == "production" ? "256Mi" : "128Mi"}
        limits:
          cpu: ${var.environment == "production" ? "200m" : "100m"}
          memory: ${var.environment == "production" ? "512Mi" : "256Mi"}
    EOT
  ]
  
  # Add common labels to all resources
  set {
    name  = "commonLabels.app"
    value = local.common_labels.app
  }
  
  set {
    name  = "commonLabels.environment"
    value = local.common_labels.environment
  }
  
  set {
    name  = "commonLabels.managed_by"
    value = local.common_labels.managed_by
  }
}

# Deploy PostgreSQL exporter for database metrics
resource "helm_release" "postgres_exporter" {
  count      = local.prometheus_enabled ? 1 : 0
  name       = "postgres-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-postgres-exporter"
  version    = var.postgres_exporter_version
  namespace  = var.monitoring_namespace
  
  depends_on = [helm_release.prometheus_operator]
  
  values = [
    <<-EOT
    config:
      datasource:
        host: ${var.postgres_host}
        user: ${var.postgres_exporter_user}
        password: ${var.postgres_exporter_password}
        port: ${var.postgres_port}
        database: ${var.postgres_database}
        sslmode: ${var.postgres_ssl_mode}
      queries:
        pg_replication:
          query: "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as lag"
          metrics:
            - lag:
                usage: "GAUGE"
                description: "Replication lag behind master in seconds"
    
    serviceMonitor:
      enabled: true
      labels:
        app: "mca-monitoring"
    
    resources:
      requests:
        cpu: ${var.environment == "production" ? "100m" : "50m"}
        memory: ${var.environment == "production" ? "128Mi" : "64Mi"}
      limits:
        cpu: ${var.environment == "production" ? "200m" : "100m"}
        memory: ${var.environment == "production" ? "256Mi" : "128Mi"}
    EOT
  ]
}

# Deploy RabbitMQ exporter for message queue metrics
resource "helm_release" "rabbitmq_exporter" {
  count      = local.prometheus_enabled ? 1 : 0
  name       = "rabbitmq-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-rabbitmq-exporter"
  version    = var.rabbitmq_exporter_version
  namespace  = var.monitoring_namespace
  
  depends_on = [helm_release.prometheus_operator]
  
  values = [
    <<-EOT
    rabbitmq:
      url: ${var.rabbitmq_url}
      user: ${var.rabbitmq_exporter_user}
      password: ${var.rabbitmq_exporter_password}
    
    serviceMonitor:
      enabled: true
      labels:
        app: "mca-monitoring"
    
    resources:
      requests:
        cpu: ${var.environment == "production" ? "100m" : "50m"}
        memory: ${var.environment == "production" ? "128Mi" : "64Mi"}
      limits:
        cpu: ${var.environment == "production" ? "200m" : "100m"}
        memory: ${var.environment == "production" ? "256Mi" : "128Mi"}
    EOT
  ]
}

# Deploy Redis exporter for cache metrics
resource "helm_release" "redis_exporter" {
  count      = local.prometheus_enabled ? 1 : 0
  name       = "redis-exporter"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus-redis-exporter"
  version    = var.redis_exporter_version
  namespace  = var.monitoring_namespace
  
  depends_on = [helm_release.prometheus_operator]
  
  values = [
    <<-EOT
    redisAddress: ${var.redis_url}
    
    serviceMonitor:
      enabled: true
      labels:
        app: "mca-monitoring"
    
    resources:
      requests:
        cpu: ${var.environment == "production" ? "100m" : "50m"}
        memory: ${var.environment == "production" ? "128Mi" : "64Mi"}
      limits:
        cpu: ${var.environment == "production" ? "200m" : "100m"}
        memory: ${var.environment == "production" ? "256Mi" : "128Mi"}
    EOT
  ]
}

# Deploy S3 exporter for object storage metrics
resource "kubernetes_deployment" "s3_exporter" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "s3-exporter"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "s3-exporter" })
  }
  
  spec {
    replicas = 1
    
    selector {
      match_labels = merge(local.common_labels, { component = "s3-exporter" })
    }
    
    template {
      metadata {
        labels = merge(local.common_labels, { component = "s3-exporter" })
      }
      
      spec {
        container {
          name  = "s3-exporter"
          image = "${var.s3_exporter_image}:${var.s3_exporter_version}"
          
          env {
            name  = "AWS_ACCESS_KEY_ID"
            value_from {
              secret_key_ref {
                name = var.s3_credentials_secret
                key  = "access_key"
              }
            }
          }
          
          env {
            name  = "AWS_SECRET_ACCESS_KEY"
            value_from {
              secret_key_ref {
                name = var.s3_credentials_secret
                key  = "secret_key"
              }
            }
          }
          
          env {
            name  = "S3_ENDPOINT"
            value = var.s3_endpoint
          }
          
          env {
            name  = "S3_BUCKETS"
            value = join(",", var.s3_buckets)
          }
          
          port {
            container_port = 9340
            name           = "metrics"
          }
          
          resources {
            requests = {
              cpu    = var.environment == "production" ? "100m" : "50m"
              memory = var.environment == "production" ? "128Mi" : "64Mi"
            }
            limits = {
              cpu    = var.environment == "production" ? "200m" : "100m"
              memory = var.environment == "production" ? "256Mi" : "128Mi"
            }
          }
          
          liveness_probe {
            http_get {
              path = "/metrics"
              port = "metrics"
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }
          
          readiness_probe {
            http_get {
              path = "/metrics"
              port = "metrics"
            }
            initial_delay_seconds = 15
            period_seconds        = 5
          }
        }
      }
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}

resource "kubernetes_service" "s3_exporter" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "s3-exporter"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "s3-exporter" })
  }
  
  spec {
    selector = merge(local.common_labels, { component = "s3-exporter" })
    
    port {
      port        = 9340
      target_port = 9340
      name        = "metrics"
    }
  }
  
  depends_on = [kubernetes_deployment.s3_exporter]
}

resource "kubernetes_service_monitor" "s3_exporter" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "s3-exporter"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "s3-exporter" })
  }
  
  spec {
    selector {
      match_labels = merge(local.common_labels, { component = "s3-exporter" })
    }
    
    endpoint {
      port     = "metrics"
      interval = "30s"
    }
  }
  
  depends_on = [kubernetes_service.s3_exporter, helm_release.prometheus_operator]
}

# Create ServiceMonitor resources for MCA microservices
resource "kubernetes_service_monitor" "email_service" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "email-service"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "email-service" })
  }
  
  spec {
    selector {
      match_labels = {
        app = "email-service"
      }
    }
    
    namespace_selector {
      match_names = [var.app_namespace]
    }
    
    endpoint {
      port     = "metrics"
      path     = "/metrics"
      interval = "30s"
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}

resource "kubernetes_service_monitor" "document_service" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "document-service"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "document-service" })
  }
  
  spec {
    selector {
      match_labels = {
        app = "document-service"
      }
    }
    
    namespace_selector {
      match_names = [var.app_namespace]
    }
    
    endpoint {
      port     = "metrics"
      path     = "/metrics"
      interval = "30s"
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}

resource "kubernetes_service_monitor" "ocr_service" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "ocr-service"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "ocr-service" })
  }
  
  spec {
    selector {
      match_labels = {
        app = "ocr-service"
      }
    }
    
    namespace_selector {
      match_names = [var.app_namespace]
    }
    
    endpoint {
      port     = "metrics"
      path     = "/metrics"
      interval = "30s"
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}

resource "kubernetes_service_monitor" "data_service" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "data-service"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "data-service" })
  }
  
  spec {
    selector {
      match_labels = {
        app = "data-service"
      }
    }
    
    namespace_selector {
      match_names = [var.app_namespace]
    }
    
    endpoint {
      port     = "metrics"
      path     = "/actuator/prometheus"
      interval = "30s"
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}

resource "kubernetes_service_monitor" "notification_service" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "notification-service"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "notification-service" })
  }
  
  spec {
    selector {
      match_labels = {
        app = "notification-service"
      }
    }
    
    namespace_selector {
      match_names = [var.app_namespace]
    }
    
    endpoint {
      port     = "metrics"
      path     = "/metrics"
      interval = "30s"
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}

resource "kubernetes_service_monitor" "api_gateway" {
  count = local.prometheus_enabled ? 1 : 0
  
  metadata {
    name      = "api-gateway"
    namespace = var.monitoring_namespace
    labels    = merge(local.common_labels, { component = "api-gateway" })
  }
  
  spec {
    selector {
      match_labels = {
        app = "api-gateway"
      }
    }
    
    namespace_selector {
      match_names = [var.app_namespace]
    }
    
    endpoint {
      port     = "metrics"
      path     = "/metrics"
      interval = "30s"
    }
  }
  
  depends_on = [helm_release.prometheus_operator]
}