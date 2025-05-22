# RabbitMQ Cluster Configuration for MCA Application Processing System
#
# This file defines the infrastructure for a highly available RabbitMQ cluster
# with 3 nodes distributed across multiple availability zones. It implements
# quorum-based consensus for queue replication and automatic failover.
#
# Key features:
# - 3-node cluster for high availability (minimum for quorum)
# - Cross-AZ deployment for resilience against zone failures
# - Automatic failover with leader election via Raft consensus
# - Message replication across nodes with quorum queues
# - Partition tolerance and recovery strategies
# - Monitoring and health check endpoints
#
# This implementation follows RabbitMQ best practices for high availability:
# - Uses quorum queues instead of classic mirrored queues for better reliability
# - Implements proper partition handling strategy
# - Configures cross-AZ deployment for resilience
# - Sets up monitoring and alerting for cluster health

# RabbitMQ cluster resource
resource "aws_mq_broker" "rabbitmq_cluster" {
  broker_name        = "${var.environment}-mca-rabbitmq-cluster"
  engine_type        = "RabbitMQ"
  engine_version     = "3.13.0"  # Latest version with quorum queue support
  host_instance_type = var.instance_type
  
  # Configure deployment across multiple availability zones
  deployment_mode    = "CLUSTER_MULTI_AZ"
  
  # Security settings
  security_groups    = [var.security_group_id]
  subnet_ids         = var.subnet_ids
  
  # Authentication
  authentication_strategy = "SIMPLE"
  
  # User configuration
  users {
    username = var.rabbitmq_admin_username
    password = var.rabbitmq_admin_password
    
    # Grant admin permissions to the main user
    console_access = true
  }

  # Configure maintenance window during off-peak hours
  maintenance_window_start_time {
    day_of_week = var.maintenance_day_of_week
    time_of_day = var.maintenance_time_of_day
    time_zone   = var.maintenance_time_zone
  }

  # Enable CloudWatch logs
  logs {
    general = true
    audit   = true
  }

  # Apply tags for resource management
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-mca-rabbitmq-cluster"
      Environment = var.environment
      Service     = "mca-messaging"
    }
  )

  # Advanced broker configuration
  configuration {
    id       = aws_mq_configuration.rabbitmq_config.id
    revision = aws_mq_configuration.rabbitmq_config.latest_revision
  }
}

# RabbitMQ configuration resource for advanced settings
resource "aws_mq_configuration" "rabbitmq_config" {
  name           = "${var.environment}-mca-rabbitmq-config"
  engine_type    = "RabbitMQ"
  engine_version = "3.13.0"
  
  # RabbitMQ configuration in JSON format
  data = jsonencode({
    # Configure quorum queues as the default queue type
    "rabbitmq.conf" = {
      # Default queue type set to quorum for high availability
      "default_queue_type" = "quorum"
      
      # Quorum queue settings for high availability
      "quorum_queue.max_in_memory_length" = 10000
      "quorum_queue.max_in_memory_bytes" = 104857600  # 100MB
      "quorum_queue.member_reconciliation.enabled" = true
      "quorum_queue.member_reconciliation.interval" = 60000  # 60 seconds
      "quorum_queue.member_reconciliation.target_size" = 3  # Maintain 3 replicas
      
      # Raft consensus settings for quorum queues
      "raft.segment_max_entries" = 4096
      "raft.wal_max_size_bytes" = 536870912  # 512MB
      "raft.wal_max_batch_size" = 4096
      "raft.snapshot_interval" = 5000  # Take snapshots every 5000 entries
      
      # Cluster partition handling strategy
      "cluster_partition_handling" = "pause_minority"
      
      # Cluster formation and peer discovery
      "cluster_formation.peer_discovery_backend" = "rabbit_peer_discovery_aws"
      "cluster_formation.aws.region" = var.aws_region
      "cluster_formation.aws.use_autoscaling_group" = true
      "cluster_formation.aws.instance_tags.Service" = "mca-messaging"
      "cluster_formation.aws.instance_tags.Environment" = var.environment
      
      # Heartbeat and connection timeout settings
      "heartbeat" = 60
      "vm_memory_high_watermark.relative" = 0.7
      "tcp_listen_options.backlog" = 4096
      "tcp_listen_options.nodelay" = true
      
      # Enable management plugins
      "management.load_definitions" = "/etc/rabbitmq/definitions.json"
      "management.disable_stats" = false
      "management.enable_queue_totals" = true
      
      # TLS/SSL settings
      "listeners.ssl.default" = 5671
      "ssl_options.cacertfile" = "/etc/rabbitmq/ca_certificate.pem"
      "ssl_options.certfile" = "/etc/rabbitmq/server_certificate.pem"
      "ssl_options.keyfile" = "/etc/rabbitmq/server_key.pem"
      "ssl_options.verify" = "verify_peer"
      "ssl_options.fail_if_no_peer_cert" = false
    }
  })
  
  # Apply tags for resource management
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-mca-rabbitmq-config"
      Environment = var.environment
      Service     = "mca-messaging"
    }
  )
}

# CloudWatch alarm for cluster health monitoring
resource "aws_cloudwatch_metric_alarm" "rabbitmq_health" {
  alarm_name          = "${var.environment}-mca-rabbitmq-health"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "RabbitMQClusterStatus"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "This alarm monitors RabbitMQ cluster health"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
}

# CloudWatch alarm for queue depth monitoring
resource "aws_cloudwatch_metric_alarm" "queue_depth" {
  count               = length(var.critical_queues)
  
  alarm_name          = "${var.environment}-mca-rabbitmq-queue-depth-${var.critical_queues[count.index]}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "QueueDepth"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.queue_depth_threshold
  alarm_description   = "This alarm monitors the depth of the ${var.critical_queues[count.index]} queue"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
    Queue  = var.critical_queues[count.index]
    VirtualHost = var.rabbitmq_vhost
  }
  
  alarm_actions = var.alarm_actions
  ok_actions    = var.ok_actions
}

# Route53 DNS record for the RabbitMQ cluster
resource "aws_route53_record" "rabbitmq_cluster" {
  count   = var.create_dns_record ? 1 : 0
  
  zone_id = var.dns_zone_id
  name    = "rabbitmq.${var.dns_domain}"
  type    = "CNAME"
  ttl     = 300
  records = [aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0]
}

# Health check for RabbitMQ cluster
resource "aws_route53_health_check" "rabbitmq" {
  count             = var.create_dns_record ? 1 : 0
  
  fqdn              = "rabbitmq.${var.dns_domain}"
  port              = 5671
  type              = "TCP"
  request_interval  = 30
  failure_threshold = 3
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-mca-rabbitmq-health-check"
      Environment = var.environment
      Service     = "mca-messaging"
    }
  )
}

# Auto recovery lambda function for RabbitMQ cluster
resource "aws_lambda_function" "rabbitmq_recovery" {
  function_name    = "${var.environment}-mca-rabbitmq-recovery"
  role             = aws_iam_role.rabbitmq_recovery.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  timeout          = 300
  memory_size      = 128
  
  filename         = "${path.module}/files/rabbitmq-recovery.zip"
  source_code_hash = filebase64sha256("${path.module}/files/rabbitmq-recovery.zip")
  
  environment {
    variables = {
      BROKER_ID = aws_mq_broker.rabbitmq_cluster.id
      REGION    = var.aws_region
    }
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-mca-rabbitmq-recovery"
      Environment = var.environment
      Service     = "mca-messaging"
    }
  )
}

# IAM role for RabbitMQ recovery lambda
resource "aws_iam_role" "rabbitmq_recovery" {
  name = "${var.environment}-mca-rabbitmq-recovery-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-mca-rabbitmq-recovery-role"
      Environment = var.environment
      Service     = "mca-messaging"
    }
  )
}

# IAM policy for RabbitMQ recovery lambda
resource "aws_iam_policy" "rabbitmq_recovery" {
  name        = "${var.environment}-mca-rabbitmq-recovery-policy"
  description = "Policy for RabbitMQ recovery lambda"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "mq:RebootBroker",
          "mq:DescribeBroker"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach IAM policy to IAM role for RabbitMQ recovery
resource "aws_iam_role_policy_attachment" "rabbitmq_recovery" {
  role       = aws_iam_role.rabbitmq_recovery.name
  policy_arn = aws_iam_policy.rabbitmq_recovery.arn
}

# CloudWatch event rule to trigger recovery lambda on alarm
resource "aws_cloudwatch_event_rule" "rabbitmq_alarm" {
  name        = "${var.environment}-mca-rabbitmq-alarm"
  description = "Trigger recovery lambda on RabbitMQ alarm"
  
  event_pattern = jsonencode({
    source      = ["aws.cloudwatch"],
    detail_type = ["CloudWatch Alarm State Change"],
    resources   = [aws_cloudwatch_metric_alarm.rabbitmq_health.arn],
    detail = {
      state = {
        value = ["ALARM"]
      }
    }
  })
}

# CloudWatch event target for recovery lambda
resource "aws_cloudwatch_event_target" "rabbitmq_recovery" {
  rule      = aws_cloudwatch_event_rule.rabbitmq_alarm.name
  target_id = "${var.environment}-mca-rabbitmq-recovery"
  arn       = aws_lambda_function.rabbitmq_recovery.arn
}

# CloudWatch dashboard for RabbitMQ monitoring
resource "aws_cloudwatch_dashboard" "rabbitmq" {
  dashboard_name = "${var.environment}-mca-rabbitmq-dashboard"
  
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
            ["AWS/MQ", "RabbitMQClusterStatus", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "RabbitMQ Cluster Status"
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
            ["AWS/MQ", "ConnectionCount", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "RabbitMQ Connection Count"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["AWS/MQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id, "Queue", "document-processing", "VirtualHost", var.rabbitmq_vhost],
            ["AWS/MQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id, "Queue", "data-extraction", "VirtualHost", var.rabbitmq_vhost],
            ["AWS/MQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id, "Queue", "notification", "VirtualHost", var.rabbitmq_vhost]
          ]
          period = 60
          stat   = "Maximum"
          region = var.aws_region
          title  = "Queue Depths"
        }
      }
    ]
  })
}