/**
 * Routes Index
 * 
 * This barrel file exports all route modules from the Notification Service.
 * It simplifies importing routes throughout the application by providing a single entry point.
 * It ensures consistent route usage and enables proper route registration in the Express application.
 * 
 * @module routes
 */

import webhookRoutes from './webhook-routes';
import healthRoutes from './health-routes';
import statusRoutes from './status-routes';

export {
  webhookRoutes,
  healthRoutes,
  statusRoutes
};