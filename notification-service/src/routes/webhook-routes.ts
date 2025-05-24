import express, { Request, Response, NextFunction, Router } from 'express';
import { body, param, query, validationResult } from 'express-validator';
import { WebhookService } from '../services';
import { authMiddleware } from '../middleware/auth-middleware';
import { IWebhookConfig, WebhookMethod, WebhookStatus } from '../types/webhook';

/**
 * Webhook Routes - Handles all webhook configuration endpoints
 * 
 * These routes enable external systems to register and manage webhook endpoints
 * for receiving notifications from the MCA Application Processing System.
 * 
 * Security: All routes are protected by JWT authentication and role-based access control.
 * Operations Staff can view webhooks, while System Admin role is required for create/update/delete.
 */
const router: Router = express.Router();

// Inject the webhook service
const webhookService = new WebhookService();

/**
 * Validation middleware for webhook configuration
 * Validates the request body for webhook creation and updates
 */
const validateWebhookConfig = [
  body('name')
    .isString()
    .trim()
    .notEmpty()
    .withMessage('Webhook name is required')
    .isLength({ min: 3, max: 100 })
    .withMessage('Webhook name must be between 3 and 100 characters'),
  
  body('url')
    .isURL({ protocols: ['http', 'https'], require_protocol: true })
    .withMessage('Valid webhook URL with protocol (http/https) is required'),
  
  body('method')
    .isIn(Object.values(WebhookMethod))
    .withMessage(`Method must be one of: ${Object.values(WebhookMethod).join(', ')}`),
  
  body('status')
    .optional()
    .isIn(Object.values(WebhookStatus))
    .withMessage(`Status must be one of: ${Object.values(WebhookStatus).join(', ')}`),
  
  body('description')
    .optional()
    .isString()
    .trim()
    .isLength({ max: 500 })
    .withMessage('Description must not exceed 500 characters'),
  
  body('headers')
    .optional()
    .isObject()
    .withMessage('Headers must be an object'),
  
  body('secretKey')
    .isString()
    .trim()
    .notEmpty()
    .withMessage('Secret key is required for HMAC-SHA256 signature generation')
    .isLength({ min: 16 })
    .withMessage('Secret key must be at least 16 characters long'),
  
  body('retryPolicy')
    .optional()
    .isObject()
    .withMessage('Retry policy must be an object'),
  
  body('retryPolicy.maxRetries')
    .optional()
    .isInt({ min: 0, max: 10 })
    .withMessage('Max retries must be between 0 and 10'),
  
  body('retryPolicy.initialInterval')
    .optional()
    .isInt({ min: 1000, max: 60000 })
    .withMessage('Initial interval must be between 1000 and 60000 milliseconds'),
  
  body('retryPolicy.backoffMultiplier')
    .optional()
    .isFloat({ min: 1.0, max: 5.0 })
    .withMessage('Backoff multiplier must be between 1.0 and 5.0'),
  
  body('eventTypes')
    .isArray({ min: 1 })
    .withMessage('At least one event type must be specified'),
  
  body('eventTypes.*')
    .isString()
    .trim()
    .notEmpty()
    .withMessage('Event type must be a non-empty string'),
  
  // Validation result handling middleware
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Validation failed', 
        errors: errors.array() 
      });
    }
    next();
  }
];

/**
 * @route   GET /webhooks
 * @desc    Get all webhook configurations with optional filtering
 * @access  Operations Staff, System Admin
 */
router.get(
  '/',
  authMiddleware(['Operations Staff', 'System Admin']),
  [
    query('status')
      .optional()
      .isIn(Object.values(WebhookStatus))
      .withMessage(`Status must be one of: ${Object.values(WebhookStatus).join(', ')}`),
    
    query('eventType')
      .optional()
      .isString()
      .trim(),
    
    query('page')
      .optional()
      .isInt({ min: 1 })
      .withMessage('Page must be a positive integer'),
    
    query('limit')
      .optional()
      .isInt({ min: 1, max: 100 })
      .withMessage('Limit must be between 1 and 100'),
    
    // Validation result handling middleware
    (req: Request, res: Response, next: NextFunction) => {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Validation failed', 
          errors: errors.array() 
        });
      }
      next();
    }
  ],
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { status, eventType, page = 1, limit = 20 } = req.query;
      
      const filters: Record<string, any> = {};
      if (status) filters.status = status;
      if (eventType) filters.eventTypes = eventType;
      
      const webhooks = await webhookService.getWebhooks(filters, {
        page: Number(page),
        limit: Number(limit)
      });
      
      res.status(200).json({
        status: 'success',
        data: webhooks.items,
        pagination: {
          total: webhooks.total,
          page: webhooks.page,
          limit: webhooks.limit,
          pages: Math.ceil(webhooks.total / webhooks.limit)
        }
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @route   GET /webhooks/:id
 * @desc    Get a specific webhook configuration by ID
 * @access  Operations Staff, System Admin
 */
router.get(
  '/:id',
  authMiddleware(['Operations Staff', 'System Admin']),
  [
    param('id')
      .isUUID()
      .withMessage('Valid webhook ID is required'),
    
    // Validation result handling middleware
    (req: Request, res: Response, next: NextFunction) => {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Validation failed', 
          errors: errors.array() 
        });
      }
      next();
    }
  ],
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { id } = req.params;
      const webhook = await webhookService.getWebhookById(id);
      
      if (!webhook) {
        return res.status(404).json({
          status: 'error',
          message: `Webhook with ID ${id} not found`
        });
      }
      
      // Mask the secret key for security
      const responseWebhook = {
        ...webhook,
        secretKey: webhook.secretKey ? '••••••••' : null
      };
      
      res.status(200).json({
        status: 'success',
        data: responseWebhook
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @route   POST /webhooks
 * @desc    Create a new webhook configuration
 * @access  System Admin only
 */
router.post(
  '/',
  authMiddleware(['System Admin']),
  validateWebhookConfig,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const webhookConfig: IWebhookConfig = {
        name: req.body.name,
        url: req.body.url,
        method: req.body.method,
        status: req.body.status || WebhookStatus.ACTIVE,
        description: req.body.description,
        headers: req.body.headers || {},
        secretKey: req.body.secretKey,
        retryPolicy: req.body.retryPolicy || {
          maxRetries: 3,
          initialInterval: 5000, // 5 seconds
          backoffMultiplier: 2.0
        },
        eventTypes: req.body.eventTypes,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      
      const createdWebhook = await webhookService.createWebhook(webhookConfig);
      
      // Mask the secret key in the response
      const responseWebhook = {
        ...createdWebhook,
        secretKey: '••••••••'
      };
      
      res.status(201).json({
        status: 'success',
        message: 'Webhook configuration created successfully',
        data: responseWebhook
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @route   PUT /webhooks/:id
 * @desc    Update an existing webhook configuration
 * @access  System Admin only
 */
router.put(
  '/:id',
  authMiddleware(['System Admin']),
  [
    param('id')
      .isUUID()
      .withMessage('Valid webhook ID is required'),
    ...validateWebhookConfig
  ],
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { id } = req.params;
      
      // Check if webhook exists
      const existingWebhook = await webhookService.getWebhookById(id);
      if (!existingWebhook) {
        return res.status(404).json({
          status: 'error',
          message: `Webhook with ID ${id} not found`
        });
      }
      
      const webhookConfig: IWebhookConfig = {
        ...existingWebhook,
        name: req.body.name,
        url: req.body.url,
        method: req.body.method,
        status: req.body.status || existingWebhook.status,
        description: req.body.description,
        headers: req.body.headers || existingWebhook.headers,
        secretKey: req.body.secretKey,
        retryPolicy: req.body.retryPolicy || existingWebhook.retryPolicy,
        eventTypes: req.body.eventTypes,
        updatedAt: new Date()
      };
      
      const updatedWebhook = await webhookService.updateWebhook(id, webhookConfig);
      
      // Mask the secret key in the response
      const responseWebhook = {
        ...updatedWebhook,
        secretKey: '••••••••'
      };
      
      res.status(200).json({
        status: 'success',
        message: 'Webhook configuration updated successfully',
        data: responseWebhook
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @route   DELETE /webhooks/:id
 * @desc    Delete a webhook configuration
 * @access  System Admin only
 */
router.delete(
  '/:id',
  authMiddleware(['System Admin']),
  [
    param('id')
      .isUUID()
      .withMessage('Valid webhook ID is required'),
    
    // Validation result handling middleware
    (req: Request, res: Response, next: NextFunction) => {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Validation failed', 
          errors: errors.array() 
        });
      }
      next();
    }
  ],
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { id } = req.params;
      
      // Check if webhook exists
      const existingWebhook = await webhookService.getWebhookById(id);
      if (!existingWebhook) {
        return res.status(404).json({
          status: 'error',
          message: `Webhook with ID ${id} not found`
        });
      }
      
      await webhookService.deleteWebhook(id);
      
      res.status(200).json({
        status: 'success',
        message: 'Webhook configuration deleted successfully'
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * @route   POST /webhooks/:id/test
 * @desc    Test a webhook by sending a test payload
 * @access  System Admin only
 */
router.post(
  '/:id/test',
  authMiddleware(['System Admin']),
  [
    param('id')
      .isUUID()
      .withMessage('Valid webhook ID is required'),
    
    // Validation result handling middleware
    (req: Request, res: Response, next: NextFunction) => {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Validation failed', 
          errors: errors.array() 
        });
      }
      next();
    }
  ],
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { id } = req.params;
      
      // Check if webhook exists
      const existingWebhook = await webhookService.getWebhookById(id);
      if (!existingWebhook) {
        return res.status(404).json({
          status: 'error',
          message: `Webhook with ID ${id} not found`
        });
      }
      
      // Create a test payload
      const testPayload = {
        event: 'test_event',
        timestamp: new Date().toISOString(),
        data: {
          message: 'This is a test notification from the MCA Application Processing System',
          webhookId: id
        }
      };
      
      // Send the test payload
      const deliveryResult = await webhookService.testWebhook(id, testPayload);
      
      res.status(200).json({
        status: 'success',
        message: 'Test webhook sent successfully',
        data: {
          deliveryResult,
          testPayload
        }
      });
    } catch (error) {
      next(error);
    }
  }
);

export default router;