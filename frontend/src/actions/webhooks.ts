import type { SWRConfiguration } from 'swr';
import useSWR from 'swr';
import { useMemo, useState } from 'react';

import axiosInstance, { API_ENDPOINTS, NormalizedError } from 'src/lib/axios';

// ----------------------------------------------------------------------

/**
 * Interface for webhook configuration data
 */
export interface IWebhookConfig {
  id: string;
  url: string;
  name: string;
  description?: string;
  events: string[];
  status: 'active' | 'inactive';
  createdAt: string;
  updatedAt: string;
  lastDeliveryStatus?: 'success' | 'failed' | 'pending' | null;
  lastDeliveryTime?: string | null;
}

/**
 * Interface for webhook test response
 */
export interface IWebhookTestResponse {
  success: boolean;
  statusCode?: number;
  responseTime?: number;
  responseBody?: string;
  error?: string;
  timestamp: string;
}

/**
 * Interface for webhook log entry
 */
export interface IWebhookLog {
  id: string;
  webhookId: string;
  event: string;
  requestPayload: string;
  responseStatus: number;
  responseBody?: string;
  error?: string;
  timestamp: string;
  duration: number;
}

/**
 * Interface for creating a new webhook configuration
 */
export interface ICreateWebhookConfig {
  url: string;
  name: string;
  description?: string;
  events: string[];
  status: 'active' | 'inactive';
}

/**
 * Interface for webhook test request
 */
export interface IWebhookTestRequest {
  webhookId: string;
  payload?: Record<string, any>;
}

// ----------------------------------------------------------------------

// SWR configuration options
const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};

// ----------------------------------------------------------------------

/**
 * Hook for retrieving the list of configured webhook endpoints
 * @param {Object} options - Optional parameters for filtering and pagination
 * @returns {Object} Webhook list data and loading states
 */
export function useGetWebhooks(options?: { status?: string; page?: number; limit?: number }) {
  const url = options
    ? [API_ENDPOINTS.webhooks.list, { params: options }]
    : API_ENDPOINTS.webhooks.list;

  const { data, error, isLoading, isValidating, mutate } = useSWR<{ webhooks: IWebhookConfig[] }>(url, undefined, swrOptions);

  const memoizedValue = useMemo(
    () => ({
      webhooks: data?.webhooks || [],
      webhooksLoading: isLoading,
      webhooksError: error as NormalizedError | undefined,
      webhooksValidating: isValidating,
      webhooksEmpty: !isLoading && !isValidating && !data?.webhooks.length,
      revalidateWebhooks: mutate,
    }),
    [data?.webhooks, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Hook for creating a new webhook configuration
 * @returns {Object} Functions and state for creating webhook configurations
 */
export function usePostWebhookConfig() {
  const { mutate } = useSWR<{ webhooks: IWebhookConfig[] }>(API_ENDPOINTS.webhooks.list);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<NormalizedError | null>(null);

  /**
   * Create a new webhook configuration
   * @param {ICreateWebhookConfig} config - The webhook configuration to create
   * @returns {Promise<IWebhookConfig>} The created webhook configuration
   */
  const createWebhook = async (config: ICreateWebhookConfig): Promise<IWebhookConfig> => {
    setIsSubmitting(true);
    setError(null);

    try {
      // Validate URL format before sending to server
      if (!isValidUrl(config.url)) {
        throw new Error('Invalid URL format');
      }

      const response = await axiosInstance.post<{ webhook: IWebhookConfig }>(
        API_ENDPOINTS.webhooks.create,
        config
      );

      // Revalidate the webhook list to include the new webhook
      await mutate();

      return response.data.webhook;
    } catch (err) {
      const normalizedError = err as NormalizedError;
      setError(normalizedError);
      throw normalizedError;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    createWebhook,
    isSubmitting,
    error,
  };
}

// ----------------------------------------------------------------------

/**
 * Hook for testing webhook delivery
 * @returns {Object} Functions and state for testing webhooks
 */
export function useTestWebhook() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<IWebhookTestResponse | null>(null);
  const [error, setError] = useState<NormalizedError | null>(null);

  /**
   * Send a test payload to a webhook endpoint
   * @param {IWebhookTestRequest} request - The test request configuration
   * @returns {Promise<IWebhookTestResponse>} The test response
   */
  const testWebhook = async (request: IWebhookTestRequest): Promise<IWebhookTestResponse> => {
    setIsSubmitting(true);
    setError(null);
    setTestResult(null);

    try {
      const response = await axiosInstance.post<{ result: IWebhookTestResponse }>(
        API_ENDPOINTS.webhooks.test,
        request
      );

      const result = response.data.result;
      setTestResult(result);
      return result;
    } catch (err) {
      const normalizedError = err as NormalizedError;
      setError(normalizedError);
      throw normalizedError;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    testWebhook,
    isSubmitting,
    testResult,
    error,
    clearTestResult: () => setTestResult(null),
  };
}

// ----------------------------------------------------------------------

/**
 * Hook for retrieving webhook delivery logs
 * @param {string} webhookId - ID of the webhook to retrieve logs for
 * @param {Object} options - Optional parameters for filtering and pagination
 * @returns {Object} Webhook logs data and loading states
 */
export function useWebhookLogs(
  webhookId: string,
  options?: { status?: number; startDate?: string; endDate?: string; page?: number; limit?: number }
) {
  const url = webhookId
    ? [API_ENDPOINTS.webhooks.logs, { params: { webhookId, ...options } }]
    : '';

  const { data, error, isLoading, isValidating, mutate } = useSWR<{ logs: IWebhookLog[] }>(url, undefined, swrOptions);

  const memoizedValue = useMemo(
    () => ({
      logs: data?.logs || [],
      logsLoading: isLoading,
      logsError: error as NormalizedError | undefined,
      logsValidating: isValidating,
      logsEmpty: !isLoading && !isValidating && !data?.logs.length,
      revalidateLogs: mutate,
    }),
    [data?.logs, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

// Helper function to validate URL format
function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch (e) {
    return false;
  }
}

