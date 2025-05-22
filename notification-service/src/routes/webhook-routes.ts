/**
 * Webhook Routes
 * 
 * This module defines Express routes for webhook configuration and management in the Notification Service.
 * It implements endpoints for creating, retrieving, updating, and deleting webhook configurations.
 * It enables external systems to register and manage webhook endpoints for receiving notifications.
 */

import { Router } from 'express';
import { WebhookService } from '../services';
import { IWebhookConfig, WebhookStatus } from '../types';
import { authMiddleware } from '../middleware/auth-middleware';
import { validationMiddleware } from '../middleware/validation-middleware';
import { logger } from '../config/logger';

const router = Router();

// Webhook configuration validation schema
const webhookConfigSchema = {
  type: 'object',
  required: ['url', 'method', 'events'],
  properties: {
    url: { type: 'string', format: 'uri' },
    method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] },
    events: { type: 'array', items: { type: 'string' }, minItems: 1 },
    description: { type: 'string' },
    headers: {
      type: 'object',
      additionalProperties: { type: 'string' }
    },
    secret: { type: 'string', minLength: 16 },
    status: { type: 'string', enum: ['ACTIVE', 'INACTIVE'] },
    retryPolicy: {
      type: 'object',
      properties: {
        maxRetries: { type: 'integer', minimum: 0 },
        initialInterval: { type: 'integer', minimum: 100 },
        multiplier: { type: 'number', minimum: 1 },
        maxInterval: { type: 'integer', minimum: 1000 }
      }
    }
  }
};

/**
 * @route GET /webhooks
 * @desc Get all webhook configurations
 * @access Private - Operations Staff, System Admin
 */
router.get(
  '/',
  authMiddleware(['Operations Staff', 'System Admin']),
  async (req, res, next) => {
    try {
      const { page = 1, limit = 10, status } = req.query;
      
      const filters: Record<string, any> = {};
      if (status) {
        filters.status = status;
      }

      const webhooks = await WebhookService.getWebhooks({
        page: Number(page),
        limit: Number(limit),
        filters
      });

      logger.info('Webhooks retrieved successfully', { count: webhooks.data.length });
      
      return res.status(200).json({
        success: true,
        data: webhooks.data,
        pagination: {
          total: webhooks.total,
          page: Number(page),
          limit: Number(limit),
          pages: Math.ceil(webhooks.total / Number(limit))
        }
      });
    } catch (error) {
      logger.error('Error retrieving webhooks', { error });
      next(error);
    }
  }
);

/**
 * @route GET /webhooks/:id
 * @desc Get a specific webhook configuration by ID
 * @access Private - Operations Staff, System Admin
 */
router.get(
  '/:id',
  authMiddleware(['Operations Staff', 'System Admin']),
  async (req, res, next) => {
    try {
      const { id } = req.params;
      const webhook = await WebhookService.getWebhookById(id);

      if (!webhook) {
        return res.status(404).json({
          success: false,
          message: `Webhook with ID ${id} not found`
        });
      }

      logger.info('Webhook retrieved successfully', { id });
      
      return res.status(200).json({
        success: true,
        data: webhook
      });
    } catch (error) {
      logger.error('Error retrieving webhook', { error, id: req.params.id });
      next(error);
    }
  }
);

/**
 * @route POST /webhooks
 * @desc Create a new webhook configuration
 * @access Private - System Admin only
 */
router.post(
  '/',
  authMiddleware(['System Admin']),
  validationMiddleware(webhookConfigSchema),
  async (req, res, next) => {
    try {
      const webhookConfig: IWebhookConfig = {
        ...req.body,
        status: req.body.status || WebhookStatus.ACTIVE,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      const newWebhook = await WebhookService.createWebhook(webhookConfig);

      logger.info('Webhook created successfully', { id: newWebhook.id });
      
      return res.status(201).json({
        success: true,
        data: newWebhook,
        message: 'Webhook configuration created successfully'
      });
    } catch (error) {
      logger.error('Error creating webhook', { error });
      next(error);
    }
  }
);

/**
 * @route PUT /webhooks/:id
 * @desc Update an existing webhook configuration
 * @access Private - System Admin only
 */
router.put(
  '/:id',
  authMiddleware(['System Admin']),
  validationMiddleware(webhookConfigSchema),
  async (req, res, next) => {
    try {
      const { id } = req.params;
      const existingWebhook = await WebhookService.getWebhookById(id);

      if (!existingWebhook) {
        return res.status(404).json({
          success: false,
          message: `Webhook with ID ${id} not found`
        });
      }

      const webhookConfig: IWebhookConfig = {
        ...existingWebhook,
        ...req.body,
        updatedAt: new Date()
      };

      const updatedWebhook = await WebhookService.updateWebhook(id, webhookConfig);

      logger.info('Webhook updated successfully', { id });
      
      return res.status(200).json({
        success: true,
        data: updatedWebhook,
        message: 'Webhook configuration updated successfully'
      });
    } catch (error) {
      logger.error('Error updating webhook', { error, id: req.params.id });
      next(error);
    }
  }
);

/**
 * @route DELETE /webhooks/:id
 * @desc Delete a webhook configuration
 * @access Private - System Admin only
 */
router.delete(
  '/:id',
  authMiddleware(['System Admin']),
  async (req, res, next) => {
    try {
      const { id } = req.params;
      const existingWebhook = await WebhookService.getWebhookById(id);

      if (!existingWebhook) {
        return res.status(404).json({
          success: false,
          message: `Webhook with ID ${id} not found`
        });
      }

      await WebhookService.deleteWebhook(id);

      logger.info('Webhook deleted successfully', { id });
      
      return res.status(200).json({
        success: true,
        message: 'Webhook configuration deleted successfully'
      });
    } catch (error) {
      logger.error('Error deleting webhook', { error, id: req.params.id });
      next(error);
    }
  }
);

/**
 * @route POST /webhooks/:id/test
 * @desc Test a webhook by sending a test payload
 * @access Private - System Admin only
 */
router.post(
  '/:id/test',
  authMiddleware(['System Admin']),
  async (req, res, next) => {
    try {
      const { id } = req.params;
      const existingWebhook = await WebhookService.getWebhookById(id);

      if (!existingWebhook) {
        return res.status(404).json({
          success: false,
          message: `Webhook with ID ${id} not found`
        });
      }

      // Create a test payload
      const testPayload = {
        event: 'webhook.test',
        timestamp: new Date().toISOString(),
        data: {
          message: 'This is a test webhook notification',
          webhookId: id
        }
      };

      const deliveryResult = await WebhookService.deliverWebhook(existingWebhook, testPayload);

      logger.info('Webhook test completed', { id, success: deliveryResult.success });
      
      return res.status(200).json({
        success: true,
        data: deliveryResult,
        message: deliveryResult.success 
          ? 'Webhook test completed successfully' 
          : 'Webhook test failed, see details for more information'
      });
    } catch (error) {
      logger.error('Error testing webhook', { error, id: req.params.id });
      next(error);
    }
  }
);

/**
 * @route GET /webhooks/:id/deliveries
 * @desc Get delivery history for a specific webhook
 * @access Private - Operations Staff, System Admin
 */
router.get(
  '/:id/deliveries',
  authMiddleware(['Operations Staff', 'System Admin']),
  async (req, res, next) => {
    try {
      const { id } = req.params;
      const { page = 1, limit = 10, status } = req.query;
      
      const existingWebhook = await WebhookService.getWebhookById(id);

      if (!existingWebhook) {
        return res.status(404).json({
          success: false,
          message: `Webhook with ID ${id} not found`
        });
      }

      const filters: Record<string, any> = {};
      if (status) {
        filters.status = status;
      }

      const deliveries = await WebhookService.getWebhookDeliveries(id, {
        page: Number(page),
        limit: Number(limit),
        filters
      });

      logger.info('Webhook deliveries retrieved successfully', { id, count: deliveries.data.length });
      
      return res.status(200).json({
        success: true,
        data: deliveries.data,
        pagination: {
          total: deliveries.total,
          page: Number(page),
          limit: Number(limit),
          pages: Math.ceil(deliveries.total / Number(limit))
        }
      });
    } catch (error) {
      logger.error('Error retrieving webhook deliveries', { error, id: req.params.id });
      next(error);
    }
  }
);

export default router;