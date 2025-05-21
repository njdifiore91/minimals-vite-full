/**
 * Webhook Configuration Hooks for MCA Application Processing System
 * 
 * This file implements custom React hooks for webhook configuration using SWR.
 * It provides hooks for listing, creating, testing, and monitoring webhooks.
 * 
 * Key features:
 * - useGetWebhooks: Lists configured webhook endpoints with status information
 * - usePostWebhookConfig: Creates new webhook configurations with validation
 * - useTestWebhook: Sends test payloads with real-time delivery feedback
 * - useWebhookLogs: Retrieves delivery history with status codes and timestamps
 */

import { useMemo, useState } from 'react';
import useSWR, { SWRConfiguration, useSWRConfig } from 'swr';
import { webhookEndpoints } from '../lib/axios';

// =============================================================================
// Types
// =============================================================================

/**
 * Webhook HTTP method enum
 */
export enum WebhookMethod {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  PATCH = 'PATCH',
  DELETE = 'DELETE'
}

/**
 * Webhook status enum
 */
export enum WebhookStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE',
  FAILED = 'FAILED'
}

/**
 * Webhook configuration interface
 */
export interface IWebhookConfig {
  id: string;
  name: string;
  url: string;
  method: WebhookMethod;
  status: WebhookStatus;
  headers?: Record<string, string>;
  secret?: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  lastTestedAt?: string;
  lastDeliveryStatus?: string;
  events: string[];
}

/**
 * Webhook creation/update payload interface
 */
export interface IWebhookPayload {
  name: string;
  url: string;
  method: WebhookMethod;
  headers?: Record<string, string>;
  secret?: string;
  description?: string;
  events: string[];
  active?: boolean;
}

/**
 * Webhook test result interface
 */
export interface IWebhookTestResult {
  success: boolean;
  statusCode?: number;
  responseTime?: number;
  responseBody?: string;
  error?: string;
  timestamp: string;
}

/**
 * Webhook log entry interface
 */
export interface IWebhookLogEntry {
  id: string;
  webhookId: string;
  eventType: string;
  requestPayload: string;
  responseStatus: number;
  responseBody?: string;
  error?: string;
  timestamp: string;
  duration: number;
  retryCount: number;
  success: boolean;
}

/**
 * Webhook logs response interface
 */
export interface IWebhookLogsResponse {
  logs: IWebhookLogEntry[];
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

// =============================================================================
// SWR Configuration
// =============================================================================

/**
 * Default SWR options for webhook hooks
 * - Disable automatic revalidation on stale data
 * - Disable revalidation on focus
 * - Disable revalidation on reconnect
 */
const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook for retrieving webhook configurations
 * 
 * @param params Optional query parameters for filtering webhooks
 * @returns Webhook configurations with loading and error states
 */
export function useGetWebhooks(params?: Record<string, any>) {
  const { data, error, isLoading, isValidating, mutate } = useSWR<{ webhooks: IWebhookConfig[] }>(
    ['webhooks', params],
    async () => {
      const response = await webhookEndpoints.list(params);
      return response.data;
    },
    swrOptions
  );

  const memoizedValue = useMemo(
    () => ({
      webhooks: data?.webhooks || [],
      webhooksLoading: isLoading,
      webhooksError: error,
      webhooksValidating: isValidating,
      webhooksEmpty: !isLoading && !isValidating && !data?.webhooks.length,
      mutateWebhooks: mutate,
    }),
    [data?.webhooks, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

/**
 * Hook for retrieving a specific webhook configuration
 * 
 * @param webhookId ID of the webhook to retrieve
 * @returns Webhook configuration with loading and error states
 */
export function useGetWebhook(webhookId: string) {
  const { data, error, isLoading, isValidating, mutate } = useSWR<{ webhook: IWebhookConfig }>(
    webhookId ? `webhook-${webhookId}` : null,
    async () => {
      const response = await webhookEndpoints.getById(webhookId);
      return response.data;
    },
    swrOptions
  );

  const memoizedValue = useMemo(
    () => ({
      webhook: data?.webhook,
      webhookLoading: isLoading,
      webhookError: error,
      webhookValidating: isValidating,
      mutateWebhook: mutate,
    }),
    [data?.webhook, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

/**
 * Hook for creating or updating webhook configurations
 * 
 * @returns Functions for creating and updating webhooks with loading and error states
 */
export function usePostWebhookConfig() {
  const { mutate } = useSWRConfig();
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<any>(null);
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateError, setUpdateError] = useState<any>(null);

  /**
   * Creates a new webhook configuration
   * 
   * @param payload Webhook configuration payload
   * @returns Created webhook configuration
   */
  const createWebhook = async (payload: IWebhookPayload) => {
    setCreateLoading(true);
    setCreateError(null);
    
    try {
      const response = await webhookEndpoints.create(payload);
      
      // Invalidate webhooks cache to trigger a refetch
      await mutate((key) => typeof key === 'string' && key.startsWith('webhooks'));
      
      setCreateLoading(false);
      return response.data.webhook;
    } catch (error) {
      setCreateError(error);
      setCreateLoading(false);
      throw error;
    }
  };

  /**
   * Updates an existing webhook configuration
   * 
   * @param webhookId ID of the webhook to update
   * @param payload Webhook configuration payload
   * @returns Updated webhook configuration
   */
  const updateWebhook = async (webhookId: string, payload: IWebhookPayload) => {
    setUpdateLoading(true);
    setUpdateError(null);
    
    try {
      const response = await webhookEndpoints.update(webhookId, payload);
      
      // Invalidate specific webhook cache and webhooks list cache
      await mutate(`webhook-${webhookId}`);
      await mutate((key) => typeof key === 'string' && key.startsWith('webhooks'));
      
      setUpdateLoading(false);
      return response.data.webhook;
    } catch (error) {
      setUpdateError(error);
      setUpdateLoading(false);
      throw error;
    }
  };

  /**
   * Deletes a webhook configuration
   * 
   * @param webhookId ID of the webhook to delete
   * @returns Success status
   */
  const deleteWebhook = async (webhookId: string) => {
    try {
      const response = await webhookEndpoints.delete(webhookId);
      
      // Invalidate webhooks cache to trigger a refetch
      await mutate((key) => typeof key === 'string' && key.startsWith('webhooks'));
      
      return response.data.success;
    } catch (error) {
      throw error;
    }
  };

  return {
    createWebhook,
    updateWebhook,
    deleteWebhook,
    createLoading,
    createError,
    updateLoading,
    updateError,
  };
}

/**
 * Hook for testing webhook delivery
 * 
 * @param webhookId ID of the webhook to test
 * @returns Function for testing webhook with loading and error states
 */
export function useTestWebhook(webhookId: string) {
  const { mutate } = useSWRConfig();
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState<any>(null);
  const [testResult, setTestResult] = useState<IWebhookTestResult | null>(null);

  /**
   * Tests webhook delivery with a sample payload
   * 
   * @param eventType Type of event to simulate for the test
   * @returns Test result with delivery status
   */
  const testWebhook = async (eventType: string) => {
    setTestLoading(true);
    setTestError(null);
    setTestResult(null);
    
    try {
      const response = await webhookEndpoints.test(webhookId, eventType);
      
      // Update the test result
      setTestResult(response.data.result);
      
      // Invalidate specific webhook cache to update lastTestedAt and lastDeliveryStatus
      await mutate(`webhook-${webhookId}`);
      
      setTestLoading(false);
      return response.data.result;
    } catch (error) {
      setTestError(error);
      setTestLoading(false);
      throw error;
    }
  };

  return {
    testWebhook,
    testLoading,
    testError,
    testResult,
  };
}

/**
 * Hook for retrieving webhook delivery logs
 * 
 * @param webhookId ID of the webhook to get logs for
 * @param params Optional query parameters for pagination and filtering
 * @returns Webhook logs with loading and error states
 */
export function useWebhookLogs(webhookId: string, params?: Record<string, any>) {
  const { data, error, isLoading, isValidating, mutate } = useSWR<IWebhookLogsResponse>(
    webhookId ? [`webhook-logs-${webhookId}`, params] : null,
    async () => {
      const response = await webhookEndpoints.logs(webhookId, params);
      return response.data;
    },
    swrOptions
  );

  const memoizedValue = useMemo(
    () => ({
      logs: data?.logs || [],
      pagination: data?.pagination,
      logsLoading: isLoading,
      logsError: error,
      logsValidating: isValidating,
      logsEmpty: !isLoading && !isValidating && !data?.logs.length,
      mutateLogs: mutate,
    }),
    [data?.logs, data?.pagination, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}