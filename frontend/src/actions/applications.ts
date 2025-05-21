/**
 * MCA Application Action Hooks
 * 
 * This file implements custom React hooks for MCA application data fetching and manipulation
 * using SWR. These hooks standardize data access patterns, handle loading/error states,
 * and ensure consistent caching across the application.
 */

import { useMemo, useCallback, useState } from 'react';
import useSWR, { mutate, useSWRConfig, type SWRConfiguration, type SWRResponse } from 'swr';
import { applicationEndpoints, type NormalizedError } from '../lib/axios';
import type {
  IApplicationItem,
  IApplicationFilters,
  IApplicationStatus,
  IBulkActionParams,
} from '../types/application';

// ----------------------------------------------------------------------

/**
 * SWR configuration options for application data
 * - Disables automatic revalidation on stale data, focus, and reconnect
 * - Configures error retry behavior
 */
const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
  errorRetryCount: 3,
  errorRetryInterval: 5000,
};

// ----------------------------------------------------------------------

/**
 * Pagination parameters for application list
 */
export interface IPaginationParams {
  page: number;
  limit: number;
}

/**
 * Response structure for paginated application list
 */
interface ApplicationsListResponse {
  applications: IApplicationItem[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

/**
 * Hook for fetching paginated list of MCA applications with filtering options
 * 
 * @param pagination - Pagination parameters (page, limit)
 * @param filters - Optional filters (status, date range, merchant name)
 * @returns Memoized object with applications data and loading states
 */
export function useGetApplications(
  pagination: IPaginationParams,
  filters?: Partial<IApplicationFilters>
) {
  // Construct query parameters
  const params = {
    page: pagination.page,
    limit: pagination.limit,
    status: filters?.status || '',
    startDate: filters?.dateRange?.startDate ? filters.dateRange.startDate.toISOString() : '',
    endDate: filters?.dateRange?.endDate ? filters.dateRange.endDate.toISOString() : '',
    merchantName: filters?.merchantName || '',
  };

  // Fetch data using SWR
  const { data, error, isLoading, isValidating, mutate } = useSWR<
    ApplicationsListResponse,
    NormalizedError
  >(
    ['applications', params],
    () => applicationEndpoints.list(params).then(response => response.data),
    swrOptions
  );

  // Memoize the return value to prevent unnecessary re-renders
  const memoizedValue = useMemo(
    () => ({
      applications: data?.applications || [],
      pagination: {
        total: data?.total || 0,
        page: data?.page || pagination.page,
        limit: data?.limit || pagination.limit,
        totalPages: data?.totalPages || 0,
      },
      applicationsLoading: isLoading,
      applicationsError: error,
      applicationsValidating: isValidating,
      applicationsEmpty: !isLoading && !isValidating && !data?.applications.length,
      refetch: mutate,
    }),
    [data, error, isLoading, isValidating, mutate, pagination.limit, pagination.page]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Response structure for detailed application data
 */
interface ApplicationDetailResponse {
  application: IApplicationItem;
}

/**
 * Hook for retrieving detailed application data with related metadata
 * 
 * @param applicationId - ID of the application to retrieve
 * @returns Memoized object with application data and loading states
 */
export function useGetApplicationById(applicationId: string) {
  // Only fetch if we have an applicationId
  const shouldFetch = Boolean(applicationId);

  // Fetch data using SWR
  const { data, error, isLoading, isValidating, mutate } = useSWR<
    ApplicationDetailResponse,
    NormalizedError
  >(
    shouldFetch ? ['application', applicationId] : null,
    () => applicationEndpoints.getById(applicationId).then(response => response.data),
    swrOptions
  );

  // Memoize the return value to prevent unnecessary re-renders
  const memoizedValue = useMemo(
    () => ({
      application: data?.application,
      applicationLoading: isLoading,
      applicationError: error,
      applicationValidating: isValidating,
      refetch: mutate,
    }),
    [data?.application, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Hook for optimistic updates to application status with backend synchronization
 * 
 * @returns Object with update function and loading state
 */
export function useUpdateApplicationStatus() {
  // Track loading state
  const [isUpdating, setIsUpdating] = useState(false);
  
  // Get SWR config including cache
  const { cache } = useSWRConfig();
  
  // Update function with optimistic UI updates
  const updateStatus = useCallback(
    async (applicationId: string, newStatus: IApplicationStatus) => {
      if (!applicationId) return false;
      
      // Start loading
      setIsUpdating(true);
      
      // Get the current cache key
      const cacheKey = ['application', applicationId];
      
      // Initialize listCacheKeys outside the try block
      let listCacheKeys: any[] = [];
      
      try {
        // Get current data from cache
        const currentData = cache.get(cacheKey)?.data as ApplicationDetailResponse | undefined;
        
        // Get list cache keys
        listCacheKeys = Array.from(cache.keys()).filter(key => 
          typeof key === 'string' && key.startsWith('applications')
        );
        
        if (currentData) {
          // Optimistically update the cache
          mutate(
            cacheKey,
            {
              application: {
                ...currentData.application,
                status: newStatus,
                updated_at: new Date().toISOString(),
              },
            },
            false // Don't revalidate yet
          );
          
          // Also update in the list view if it exists in cache
          listCacheKeys.forEach(listKey => {
            const listData = cache.get(listKey)?.data as ApplicationsListResponse | undefined;
            
            if (listData) {
              const updatedApplications = listData.applications.map(app => 
                app.id === applicationId 
                  ? { ...app, status: newStatus, updated_at: new Date().toISOString() }
                  : app
              );
              
              mutate(
                listKey,
                { ...listData, applications: updatedApplications },
                false // Don't revalidate yet
              );
            }
          });
        }
        
        // Make the actual API call
        await applicationEndpoints.updateStatus(applicationId, newStatus);
        
        // Revalidate the cache to ensure it's in sync with the server
        await mutate(cacheKey);
        await Promise.all(listCacheKeys.map(key => mutate(key)));
        
        setIsUpdating(false);
        return true;
      } catch (error) {
        console.error('Failed to update application status:', error);
        
        // Revalidate to restore the correct data
        await mutate(['application', applicationId]);
        
        // Revalidate list views - use the listCacheKeys we already defined
        await Promise.all(listCacheKeys.map(key => mutate(key)));
        
        setIsUpdating(false);
        return false;
      }
    },
    [cache]
  );
  
  return { updateStatus, isUpdating };
}

// ----------------------------------------------------------------------

/**
 * Hook for batch operations on multiple selected applications
 * 
 * @returns Object with bulk action function and loading state
 */
export function useBulkActionApplications() {
  // Track loading state
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Get SWR config including cache
  const { cache } = useSWRConfig();
  
  // Bulk action function
  const performBulkAction = useCallback(
    async (params: IBulkActionParams) => {
      if (!params.ids.length) return false;
      
      // Start loading
      setIsProcessing(true);
      
      try {
        // Make the API call
        await applicationEndpoints.bulkAction(params.ids, params.action);
        
        // Revalidate all application list caches
        const listCacheKeys = Array.from(cache.keys()).filter(key => 
          typeof key === 'string' && key.startsWith('applications')
        );
        await Promise.all(listCacheKeys.map(key => mutate(key)));
        
        // Revalidate individual application caches if they exist
        await Promise.all(
          params.ids.map(id => {
            const cacheKey = ['application', id];
            if (cache.has(cacheKey)) {
              return mutate(cacheKey);
            }
            return Promise.resolve();
          })
        );
        
        setIsProcessing(false);
        return true;
      } catch (error) {
        console.error('Failed to perform bulk action:', error);
        setIsProcessing(false);
        return false;
      }
    },
    [cache]
  );
  
  return { performBulkAction, isProcessing };
}