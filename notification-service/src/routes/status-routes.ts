/**
 * Notification Status Routes
 * 
 * This module defines Express routes for retrieving notification status and history.
 * It enables external systems to track notification delivery and troubleshoot delivery issues.
 */

import { Router, Request, Response, NextFunction } from 'express';
import { NotificationService, AuditService } from '../services';
import { authMiddleware } from '../middleware/auth-middleware';
import { NotificationType, NotificationStatus } from '../types/notification';
import { logger } from '../config/logger';

const router = Router();

/**
 * @route   GET /notifications
 * @desc    Get a list of notifications with filtering options
 * @access  Private (Operations Staff, System Admin)
 */
router.get(
  '/',
  authMiddleware(['Operations Staff', 'System Admin']),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const {
        status,
        type,
        startDate,
        endDate,
        page = 1,
        limit = 20,
        sortBy = 'createdAt',
        sortOrder = 'desc'
      } = req.query;

      // Validate query parameters
      const validatedStatus = status ? validateStatus(status as string) : undefined;
      const validatedType = type ? validateType(type as string) : undefined;
      
      // Parse dates if provided
      const parsedStartDate = startDate ? new Date(startDate as string) : undefined;
      const parsedEndDate = endDate ? new Date(endDate as string) : undefined;
      
      // Validate date range if both dates are provided
      if (parsedStartDate && parsedEndDate && parsedStartDate > parsedEndDate) {
        return res.status(400).json({
          success: false,
          message: 'Start date must be before end date'
        });
      }

      // Validate pagination parameters
      const pageNum = Math.max(1, parseInt(page as string, 10));
      const limitNum = Math.min(100, Math.max(1, parseInt(limit as string, 10)));
      
      // Validate sorting parameters
      const allowedSortFields = ['createdAt', 'updatedAt', 'status', 'type', 'priority'];
      const validatedSortBy = allowedSortFields.includes(sortBy as string) 
        ? sortBy as string 
        : 'createdAt';
      
      const validatedSortOrder = ['asc', 'desc'].includes(sortOrder as string)
        ? sortOrder as string
        : 'desc';

      // Get notifications from service
      const notificationService = new NotificationService();
      const result = await notificationService.getNotifications({
        status: validatedStatus,
        type: validatedType,
        startDate: parsedStartDate,
        endDate: parsedEndDate,
        page: pageNum,
        limit: limitNum,
        sortBy: validatedSortBy,
        sortOrder: validatedSortOrder as 'asc' | 'desc'
      });

      logger.info(`Retrieved ${result.notifications.length} notifications`);
      
      return res.status(200).json({
        success: true,
        ...result
      });
    } catch (error) {
      logger.error('Error retrieving notifications:', error);
      next(error);
    }
  }
);

/**
 * @route   GET /notifications/:id
 * @desc    Get a specific notification by ID
 * @access  Private (Operations Staff, System Admin)
 */
router.get(
  '/:id',
  authMiddleware(['Operations Staff', 'System Admin']),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { id } = req.params;

      if (!id) {
        return res.status(400).json({
          success: false,
          message: 'Notification ID is required'
        });
      }

      const notificationService = new NotificationService();
      const notification = await notificationService.getNotificationById(id);

      if (!notification) {
        return res.status(404).json({
          success: false,
          message: 'Notification not found'
        });
      }

      logger.info(`Retrieved notification ${id}`);
      
      return res.status(200).json({
        success: true,
        notification
      });
    } catch (error) {
      logger.error(`Error retrieving notification ${req.params.id}:`, error);
      next(error);
    }
  }
);

/**
 * @route   GET /notifications/:id/history
 * @desc    Get delivery history for a specific notification
 * @access  Private (Operations Staff, System Admin)
 */
router.get(
  '/:id/history',
  authMiddleware(['Operations Staff', 'System Admin']),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { id } = req.params;

      if (!id) {
        return res.status(400).json({
          success: false,
          message: 'Notification ID is required'
        });
      }

      // First check if notification exists
      const notificationService = new NotificationService();
      const notification = await notificationService.getNotificationById(id);

      if (!notification) {
        return res.status(404).json({
          success: false,
          message: 'Notification not found'
        });
      }

      // Get delivery history from audit service
      const auditService = new AuditService();
      const history = await auditService.getNotificationHistory(id);

      logger.info(`Retrieved history for notification ${id} with ${history.length} entries`);
      
      return res.status(200).json({
        success: true,
        notification,
        history
      });
    } catch (error) {
      logger.error(`Error retrieving history for notification ${req.params.id}:`, error);
      next(error);
    }
  }
);

/**
 * Helper function to validate notification status
 */
function validateStatus(status: string): NotificationStatus | undefined {
  const validStatuses = Object.values(NotificationStatus);
  const upperStatus = status.toUpperCase() as NotificationStatus;
  
  return validStatuses.includes(upperStatus) ? upperStatus : undefined;
}

/**
 * Helper function to validate notification type
 */
function validateType(type: string): NotificationType | undefined {
  const validTypes = Object.values(NotificationType);
  const upperType = type.toUpperCase() as NotificationType;
  
  return validTypes.includes(upperType) ? upperType : undefined;
}

export default router;