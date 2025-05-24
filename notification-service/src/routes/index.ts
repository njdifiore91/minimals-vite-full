/**
 * Notification Service Routes Index
 * 
 * This barrel file exports all route modules from the Notification Service.
 * It simplifies importing routes throughout the application by providing a
 * single entry point and ensures consistent route usage.
 * 
 * Routes exported:
 * - webhookRoutes: Webhook configuration and management endpoints
 * - healthRoutes: Health check endpoints for Kubernetes probes
 * - statusRoutes: Notification status and history endpoints
 */

import webhookRoutes from './webhook-routes';
import healthRoutes from './health-routes';
import statusRoutes from './status-routes';

/**
 * Export all routes for use in the Express application
 */
export {
  webhookRoutes,
  healthRoutes,
  statusRoutes
};

/**
 * Register all routes with an Express application
 * 
 * This function provides a unified API for registering all routes with an
 * Express application. It ensures consistent path prefixes and middleware
 * application across all route modules.
 * 
 * @param app Express application instance
 */
export const registerRoutes = (app: any) => {
  // Register webhook routes
  app.use('/webhooks', webhookRoutes);
  
  // Register health check routes
  app.use('/health', healthRoutes);
  
  // Register notification status routes
  app.use('/notifications', statusRoutes);
  
  // Log registered routes
  console.log('All routes registered successfully');
};

/**
 * Default export for backward compatibility
 */
export default {
  webhookRoutes,
  healthRoutes,
  statusRoutes,
  registerRoutes
};