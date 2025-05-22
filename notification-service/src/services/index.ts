/**
 * Notification Service - Service Exports
 * 
 * This barrel file exports all notification service modules to provide a clean, unified API surface.
 * It simplifies importing services throughout the application and ensures consistent service usage patterns.
 * 
 * Note: Using named exports to support tree-shaking for optimized builds.
 */

// Core notification service for processing messages from RabbitMQ
export { NotificationService } from './notification-service';

// Webhook delivery service with HMAC-SHA256 signing and delivery confirmation
export { WebhookService } from './webhook-service';

// Retry mechanism for failed notification deliveries
export { RetryService } from './retry-service';

// Audit logging service for notification activities
export { AuditService } from './audit-service';

// Multi-channel message formatting and delivery service
export { MessageService } from './message-service';