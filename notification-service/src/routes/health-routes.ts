/**
 * Health check routes for the Notification Service
 * 
 * These routes provide endpoints for monitoring the health and status of the service.
 * They are used by Kubernetes for liveness and readiness probes, as well as by monitoring
 * systems to track service health and dependencies.
 */

import { Router } from 'express';
import { config } from '../config';
import { logger } from '../config/logger';
import { redisClient } from '../config/redis';
import { rabbitMQConnection } from '../config/rabbitmq';

const router = Router();

/**
 * Health check status enum
 */
enum HealthStatus {
  UP = 'UP',
  DOWN = 'DOWN',
  DEGRADED = 'DEGRADED'
}

/**
 * Standard health check response format
 */
interface HealthResponse {
  status: HealthStatus;
  version: string;
  timestamp: string;
  service: string;
  details?: {
    [key: string]: {
      status: HealthStatus;
      details?: any;
      error?: string;
    };
  };
}

/**
 * Basic health check endpoint (liveness probe)
 * 
 * This endpoint provides a simple health check that returns 200 OK if the service
 * is running. It is used by Kubernetes for liveness probes to determine if the
 * container should be restarted.
 * 
 * @route GET /health
 * @returns {HealthResponse} 200 - Basic health status
 */
router.get('/', async (req, res) => {
  const healthResponse: HealthResponse = {
    status: HealthStatus.UP,
    version: config.version,
    timestamp: new Date().toISOString(),
    service: config.serviceName
  };

  logger.info('Health check performed', { result: 'success' });
  return res.status(200).json(healthResponse);
});

/**
 * Detailed health check endpoint (readiness probe)
 * 
 * This endpoint provides a comprehensive health check that verifies connectivity
 * to all dependencies (RabbitMQ, Redis). It is used by Kubernetes for readiness
 * probes to determine if the service should receive traffic.
 * 
 * @route GET /health/detailed
 * @returns {HealthResponse} 200 - Detailed health status with dependency checks
 */
router.get('/detailed', async (req, res) => {
  const details: HealthResponse['details'] = {};
  let overallStatus = HealthStatus.UP;

  // Check RabbitMQ connection
  try {
    const rabbitMQStatus = rabbitMQConnection.isConnected() 
      ? HealthStatus.UP 
      : HealthStatus.DOWN;
    
    details.rabbitmq = {
      status: rabbitMQStatus,
      details: {
        connected: rabbitMQConnection.isConnected(),
        queue: config.rabbitmq.queue
      }
    };

    if (rabbitMQStatus === HealthStatus.DOWN) {
      overallStatus = HealthStatus.DEGRADED;
    }
  } catch (error) {
    details.rabbitmq = {
      status: HealthStatus.DOWN,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
    overallStatus = HealthStatus.DEGRADED;
    logger.error('RabbitMQ health check failed', { error });
  }

  // Check Redis connection
  try {
    const pingResult = await redisClient.ping();
    const redisStatus = pingResult === 'PONG' ? HealthStatus.UP : HealthStatus.DOWN;
    
    details.redis = {
      status: redisStatus,
      details: {
        connected: pingResult === 'PONG',
        host: config.redis.host
      }
    };

    if (redisStatus === HealthStatus.DOWN) {
      overallStatus = HealthStatus.DEGRADED;
    }
  } catch (error) {
    details.redis = {
      status: HealthStatus.DOWN,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
    overallStatus = HealthStatus.DEGRADED;
    logger.error('Redis health check failed', { error });
  }

  // Add service metrics
  details.metrics = {
    status: HealthStatus.UP,
    details: {
      memory: process.memoryUsage(),
      uptime: process.uptime(),
      webhookDeliveryRate: await getWebhookDeliveryRate()
    }
  };

  const healthResponse: HealthResponse = {
    status: overallStatus,
    version: config.version,
    timestamp: new Date().toISOString(),
    service: config.serviceName,
    details
  };

  // Log health check results
  logger.info('Detailed health check performed', { 
    status: overallStatus,
    dependencies: {
      rabbitmq: details.rabbitmq?.status,
      redis: details.redis?.status
    }
  });

  // Return appropriate status code based on health
  const statusCode = overallStatus === HealthStatus.UP ? 200 : 503;
  return res.status(statusCode).json(healthResponse);
});

/**
 * Get webhook delivery rate from Redis
 * 
 * This function retrieves the current webhook delivery rate from Redis cache.
 * It's used to provide metrics in the detailed health check.
 * 
 * @returns {Promise<number>} The current webhook delivery rate
 */
async function getWebhookDeliveryRate(): Promise<number> {
  try {
    const deliveryCount = await redisClient.get('metrics:webhook:delivery:count');
    const errorCount = await redisClient.get('metrics:webhook:error:count');
    
    if (!deliveryCount) return 100; // Default to 100% if no data
    
    const totalCount = parseInt(deliveryCount, 10);
    const totalErrors = errorCount ? parseInt(errorCount, 10) : 0;
    
    if (totalCount === 0) return 100; // Avoid division by zero
    
    const successRate = ((totalCount - totalErrors) / totalCount) * 100;
    return Math.round(successRate * 100) / 100; // Round to 2 decimal places
  } catch (error) {
    logger.warn('Failed to retrieve webhook delivery rate', { error });
    return 100; // Default to 100% on error
  }
}

export default router;