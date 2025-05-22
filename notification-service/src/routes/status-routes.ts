/**
 * Notification Status Routes
 * 
 * This module defines Express routes for notification status and history in the Notification Service.
 * It implements endpoints for retrieving notification status, delivery history, and retry information.
 * These endpoints enable external systems to track notification delivery and troubleshoot delivery issues.
 * 
 * @module routes/status-routes
 */

import { Router } from 'express';
import { NotificationService } from '../services/notification-service';
import { AuditService } from '../services/audit-service';
import { RetryService } from '../services/retry-service';
import { authMiddleware } from '../middleware/auth-middleware';
import { validationMiddleware } from '../middleware/validation-middleware';
import { correlationMiddleware } from '../middleware/correlation-middleware';
import { logger } from '../utils/logger';

// Create a new router instance
const router = Router();

/**
 * @route GET /notifications
 * @desc Get a list of notifications with filtering options
 * @access Restricted - Operations Staff, System Admin
 * 
 * @param {string} [status] - Filter by notification status (PENDING, DELIVERED, FAILED, RETRYING)
 * @param {string} [type] - Filter by notification type (STATUS_UPDATE, ERROR, COMPLETION)
 * @param {string} [applicationId] - Filter by application ID
 * @param {string} [recipientId] - Filter by recipient ID
 * @param {string} [startDate] - Filter by start date (ISO 8601 format)
 * @param {string} [endDate] - Filter by end date (ISO 8601 format)
 * @param {number} [page=1] - Page number for pagination
 * @param {number} [limit=20] - Number of items per page (max 100)
 * @param {string} [sortBy=createdAt] - Field to sort by
 * @param {string} [sortOrder=desc] - Sort order (asc or desc)
 * 
 * @returns {Object} Response object
 * @returns {boolean} Response.success - Indicates if the request was successful
 * @returns {Array} Response.data - Array of notification objects
 * @returns {Object} Response.pagination - Pagination information
 * 
 * @example
 * // Request
 * GET /notifications?status=FAILED&type=STATUS_UPDATE&page=1&limit=20
 * 
 * // Response
 * {
 *   "success": true,
 *   "data": [
 *     {
 *       "id": "123e4567-e89b-12d3-a456-426614174000",
 *       "type": "STATUS_UPDATE",
 *       "status": "FAILED",
 *       "recipientId": "customer-123",
 *       "applicationId": "app-456",
 *       "payload": { ... },
 *       "createdAt": "2023-01-01T12:00:00Z",
 *       "updatedAt": "2023-01-01T12:05:00Z"
 *     },
 *     ...
 *   ],
 *   "pagination": {
 *     "total": 45,
 *     "page": 1,
 *     "limit": 20,
 *     "pages": 3
 *   }
 * }
 */
router.get(
  '/',
  correlationMiddleware(),
  authMiddleware(['Operations Staff', 'System Admin']),
  validationMiddleware({
    query: {
      type: 'object',
      properties: {
        status: { type: 'string', enum: ['PENDING', 'DELIVERED', 'FAILED', 'RETRYING'] },
        type: { type: 'string', enum: ['STATUS_UPDATE', 'ERROR', 'COMPLETION'] },
        applicationId: { type: 'string' },
        recipientId: { type: 'string' },
        startDate: { type: 'string', format: 'date-time' },
        endDate: { type: 'string', format: 'date-time' },
        page: { type: 'integer', minimum: 1, default: 1 },
        limit: { type: 'integer', minimum: 1, maximum: 100, default: 20 },
        sortBy: { 
          type: 'string', 
          enum: ['createdAt', 'updatedAt', 'status', 'type', 'recipientId', 'applicationId'], 
          default: 'createdAt' 
        },
        sortOrder: { type: 'string', enum: ['asc', 'desc'], default: 'desc' }
      },
      additionalProperties: false
    }
  }),
  async (req, res, next) => {
    const correlationId = req.headers['x-correlation-id'] as string;
    
    try {
      logger.info('Retrieving notifications list', { correlationId, query: req.query });
      
      const { 
        status, 
        type, 
        applicationId,
        recipientId,
        startDate, 
        endDate, 
        page = 1, 
        limit = 20,
        sortBy = 'createdAt',
        sortOrder = 'desc'
      } = req.query;

      // Build filter object
      const filter: any = {};
      if (status) filter.status = status;
      if (type) filter.type = type;
      if (applicationId) filter.applicationId = applicationId;
      if (recipientId) filter.recipientId = recipientId;
      
      // Add date range if provided
      if (startDate || endDate) {
        filter.createdAt = {};
        if (startDate) filter.createdAt.$gte = new Date(startDate as string);
        if (endDate) filter.createdAt.$lte = new Date(endDate as string);
      }

      // Get notifications with pagination and sorting
      const result = await NotificationService.getNotifications({
        filter,
        pagination: { page: Number(page), limit: Number(limit) },
        sort: { [sortBy as string]: sortOrder === 'asc' ? 1 : -1 }
      });

      logger.info('Successfully retrieved notifications list', { 
        correlationId, 
        count: result.notifications.length,
        total: result.total
      });

      // Return paginated results
      return res.status(200).json({
        success: true,
        data: result.notifications,
        pagination: {
          total: result.total,
          page: Number(page),
          limit: Number(limit),
          pages: Math.ceil(result.total / Number(limit))
        }
      });
    } catch (error) {
      logger.error('Error retrieving notifications list', { correlationId, error });
      next(error);
    }
  }
);

/**
 * @route GET /notifications/:id
 * @desc Get a specific notification by ID
 * @access Restricted - Operations Staff, System Admin
 * 
 * @param {string} id - Notification ID (UUID format)
 * 
 * @returns {Object} Response object
 * @returns {boolean} Response.success - Indicates if the request was successful
 * @returns {Object} Response.data - Notification object
 * 
 * @example
 * // Request
 * GET /notifications/123e4567-e89b-12d3-a456-426614174000
 * 
 * // Response
 * {
 *   "success": true,
 *   "data": {
 *     "id": "123e4567-e89b-12d3-a456-426614174000",
 *     "type": "STATUS_UPDATE",
 *     "status": "DELIVERED",
 *     "recipientId": "customer-123",
 *     "applicationId": "app-456",
 *     "payload": {
 *       "applicationStatus": "APPROVED",
 *       "message": "Your application has been approved"
 *     },
 *     "metadata": {
 *       "channel": "WEBHOOK",
 *       "priority": "HIGH"
 *     },
 *     "createdAt": "2023-01-01T12:00:00Z",
 *     "updatedAt": "2023-01-01T12:05:00Z",
 *     "deliveredAt": "2023-01-01T12:05:00Z"
 *   }
 * }
 */
router.get(
  '/:id',
  correlationMiddleware(),
  authMiddleware(['Operations Staff', 'System Admin']),
  validationMiddleware({
    params: {
      type: 'object',
      required: ['id'],
      properties: {
        id: { type: 'string', format: 'uuid' }
      }
    }
  }),
  async (req, res, next) => {
    const correlationId = req.headers['x-correlation-id'] as string;
    const { id } = req.params;
    
    try {
      logger.info('Retrieving notification by ID', { correlationId, notificationId: id });
      
      // Get notification by ID
      const notification = await NotificationService.getNotificationById(id);
      
      if (!notification) {
        logger.warn('Notification not found', { correlationId, notificationId: id });
        return res.status(404).json({
          success: false,
          error: {
            code: 'NOTIFICATION_NOT_FOUND',
            message: `Notification with ID ${id} not found`
          }
        });
      }
      
      logger.info('Successfully retrieved notification', { correlationId, notificationId: id });
      return res.status(200).json({
        success: true,
        data: notification
      });
    } catch (error) {
      logger.error('Error retrieving notification', { correlationId, notificationId: id, error });
      next(error);
    }
  }
);

/**
 * @route GET /notifications/:id/history
 * @desc Get delivery history for a specific notification
 * @access Restricted - Operations Staff, System Admin
 * 
 * @param {string} id - Notification ID (UUID format)
 * @param {number} [page=1] - Page number for pagination
 * @param {number} [limit=20] - Number of items per page (max 100)
 * 
 * @returns {Object} Response object
 * @returns {boolean} Response.success - Indicates if the request was successful
 * @returns {Array} Response.data - Array of history entries
 * @returns {Object} Response.pagination - Pagination information
 * 
 * @example
 * // Request
 * GET /notifications/123e4567-e89b-12d3-a456-426614174000/history
 * 
 * // Response
 * {
 *   "success": true,
 *   "data": [
 *     {
 *       "id": "history-123",
 *       "notificationId": "123e4567-e89b-12d3-a456-426614174000",
 *       "status": "PENDING",
 *       "timestamp": "2023-01-01T12:00:00Z",
 *       "details": "Notification queued for delivery"
 *     },
 *     {
 *       "id": "history-124",
 *       "notificationId": "123e4567-e89b-12d3-a456-426614174000",
 *       "status": "DELIVERED",
 *       "timestamp": "2023-01-01T12:05:00Z",
 *       "details": "Delivered to webhook endpoint",
 *       "responseCode": 200,
 *       "responseBody": "{\"received\":true}"
 *     }
 *   ],
 *   "pagination": {
 *     "total": 2,
 *     "page": 1,
 *     "limit": 20,
 *     "pages": 1
 *   }
 * }
 */
router.get(
  '/:id/history',
  correlationMiddleware(),
  authMiddleware(['Operations Staff', 'System Admin']),
  validationMiddleware({
    params: {
      type: 'object',
      required: ['id'],
      properties: {
        id: { type: 'string', format: 'uuid' }
      }
    },
    query: {
      type: 'object',
      properties: {
        page: { type: 'integer', minimum: 1, default: 1 },
        limit: { type: 'integer', minimum: 1, maximum: 100, default: 20 }
      },
      additionalProperties: false
    }
  }),
  async (req, res, next) => {
    const correlationId = req.headers['x-correlation-id'] as string;
    const { id } = req.params;
    const { page = 1, limit = 20 } = req.query;
    
    try {
      logger.info('Retrieving notification history', { 
        correlationId, 
        notificationId: id,
        page,
        limit
      });
      
      // First check if notification exists
      const notification = await NotificationService.getNotificationById(id);
      
      if (!notification) {
        logger.warn('Notification not found when retrieving history', { correlationId, notificationId: id });
        return res.status(404).json({
          success: false,
          error: {
            code: 'NOTIFICATION_NOT_FOUND',
            message: `Notification with ID ${id} not found`
          }
        });
      }
      
      // Get delivery history with pagination
      const result = await AuditService.getNotificationHistory(id, {
        page: Number(page),
        limit: Number(limit)
      });
      
      logger.info('Successfully retrieved notification history', { 
        correlationId, 
        notificationId: id,
        count: result.history.length,
        total: result.total
      });
      
      return res.status(200).json({
        success: true,
        data: result.history,
        pagination: {
          total: result.total,
          page: Number(page),
          limit: Number(limit),
          pages: Math.ceil(result.total / Number(limit))
        }
      });
    } catch (error) {
      logger.error('Error retrieving notification history', { 
        correlationId, 
        notificationId: id, 
        error 
      });
      next(error);
    }
  }
);

/**
 * @route GET /notifications/:id/retries
 * @desc Get retry information for a failed notification
 * @access Restricted - Operations Staff, System Admin
 * 
 * @param {string} id - Notification ID (UUID format)
 * 
 * @returns {Object} Response object
 * @returns {boolean} Response.success - Indicates if the request was successful
 * @returns {Object} Response.data - Retry information
 * 
 * @example
 * // Request
 * GET /notifications/123e4567-e89b-12d3-a456-426614174000/retries
 * 
 * // Response
 * {
 *   "success": true,
 *   "data": {
 *     "notificationId": "123e4567-e89b-12d3-a456-426614174000",
 *     "status": "RETRYING",
 *     "attempts": 2,
 *     "maxAttempts": 5,
 *     "nextRetry": "2023-01-01T13:00:00Z",
 *     "lastAttempt": "2023-01-01T12:30:00Z",
 *     "lastError": "Connection timeout",
 *     "retryHistory": [
 *       {
 *         "attempt": 1,
 *         "timestamp": "2023-01-01T12:15:00Z",
 *         "error": "Connection refused",
 *         "responseCode": 503
 *       },
 *       {
 *         "attempt": 2,
 *         "timestamp": "2023-01-01T12:30:00Z",
 *         "error": "Connection timeout",
 *         "responseCode": 504
 *       }
 *     ]
 *   }
 * }
 */
router.get(
  '/:id/retries',
  correlationMiddleware(),
  authMiddleware(['Operations Staff', 'System Admin']),
  validationMiddleware({
    params: {
      type: 'object',
      required: ['id'],
      properties: {
        id: { type: 'string', format: 'uuid' }
      }
    }
  }),
  async (req, res, next) => {
    const correlationId = req.headers['x-correlation-id'] as string;
    const { id } = req.params;
    
    try {
      logger.info('Retrieving notification retry information', { correlationId, notificationId: id });
      
      // First check if notification exists
      const notification = await NotificationService.getNotificationById(id);
      
      if (!notification) {
        logger.warn('Notification not found when retrieving retry information', { 
          correlationId, 
          notificationId: id 
        });
        return res.status(404).json({
          success: false,
          error: {
            code: 'NOTIFICATION_NOT_FOUND',
            message: `Notification with ID ${id} not found`
          }
        });
      }
      
      // Only failed or retrying notifications have retry information
      if (notification.status !== 'FAILED' && notification.status !== 'RETRYING') {
        logger.warn('Notification is not in a failed or retrying state', { 
          correlationId, 
          notificationId: id,
          status: notification.status 
        });
        return res.status(400).json({
          success: false,
          error: {
            code: 'INVALID_NOTIFICATION_STATUS',
            message: `Retry information is only available for failed or retrying notifications. Current status: ${notification.status}`
          }
        });
      }
      
      // Get retry information
      const retryInfo = await RetryService.getRetryInformation(id);
      
      if (!retryInfo) {
        logger.warn('No retry information found', { correlationId, notificationId: id });
        return res.status(404).json({
          success: false,
          error: {
            code: 'RETRY_INFO_NOT_FOUND',
            message: `No retry information found for notification with ID ${id}`
          }
        });
      }
      
      logger.info('Successfully retrieved retry information', { correlationId, notificationId: id });
      return res.status(200).json({
        success: true,
        data: retryInfo
      });
    } catch (error) {
      logger.error('Error retrieving retry information', { correlationId, notificationId: id, error });
      next(error);
    }
  }
);

/**
 * @route POST /notifications/:id/retry
 * @desc Manually trigger a retry for a failed notification
 * @access Restricted - System Admin
 * 
 * @param {string} id - Notification ID (UUID format)
 * 
 * @returns {Object} Response object
 * @returns {boolean} Response.success - Indicates if the request was successful
 * @returns {Object} Response.data - Updated notification status
 * 
 * @example
 * // Request
 * POST /notifications/123e4567-e89b-12d3-a456-426614174000/retry
 * 
 * // Response
 * {
 *   "success": true,
 *   "data": {
 *     "notificationId": "123e4567-e89b-12d3-a456-426614174000",
 *     "status": "RETRYING",
 *     "message": "Manual retry initiated",
 *     "timestamp": "2023-01-01T14:00:00Z"
 *   }
 * }
 */
router.post(
  '/:id/retry',
  correlationMiddleware(),
  authMiddleware(['System Admin']), // Only System Admin can manually trigger retries
  validationMiddleware({
    params: {
      type: 'object',
      required: ['id'],
      properties: {
        id: { type: 'string', format: 'uuid' }
      }
    }
  }),
  async (req, res, next) => {
    const correlationId = req.headers['x-correlation-id'] as string;
    const { id } = req.params;
    
    try {
      logger.info('Manual retry requested', { correlationId, notificationId: id, userId: req.user.id });
      
      // First check if notification exists
      const notification = await NotificationService.getNotificationById(id);
      
      if (!notification) {
        logger.warn('Notification not found when attempting manual retry', { 
          correlationId, 
          notificationId: id 
        });
        return res.status(404).json({
          success: false,
          error: {
            code: 'NOTIFICATION_NOT_FOUND',
            message: `Notification with ID ${id} not found`
          }
        });
      }
      
      // Only failed notifications can be retried manually
      if (notification.status !== 'FAILED') {
        logger.warn('Cannot retry notification that is not in FAILED state', { 
          correlationId, 
          notificationId: id,
          status: notification.status 
        });
        return res.status(400).json({
          success: false,
          error: {
            code: 'INVALID_NOTIFICATION_STATUS',
            message: `Only failed notifications can be retried manually. Current status: ${notification.status}`
          }
        });
      }
      
      // Trigger manual retry
      const result = await RetryService.manualRetry(id, {
        userId: req.user.id,
        userName: req.user.name,
        correlationId
      });
      
      logger.info('Manual retry initiated successfully', { 
        correlationId, 
        notificationId: id,
        userId: req.user.id 
      });
      
      return res.status(200).json({
        success: true,
        data: result
      });
    } catch (error) {
      logger.error('Error initiating manual retry', { correlationId, notificationId: id, error });
      next(error);
    }
  }
);

export default router;