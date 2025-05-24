import type { SWRConfiguration, SWRResponse } from 'swr';
import type {
  IApplicationItem,
  IApplicationStatus,
  IApplicationFilters,
  IBulkActionParams,
} from 'src/types/application';

import useSWR, { mutate } from 'swr';
import { useMemo, useCallback } from 'react';

import axiosInstance, { API_ENDPOINTS, NormalizedError } from 'src/lib/axios';

// ----------------------------------------------------------------------

/**
 * SWR configuration options for application data fetching.
 * - Disables automatic revalidation on stale data
 * - Disables automatic revalidation on focus
 * - Disables automatic revalidation on reconnect
 */
const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};

// ----------------------------------------------------------------------

/**
 * Interface for pagination parameters.
 */
export interface IPaginationParams {
  page: number;
  limit: number;
}

/**
 * Interface for the response data from the applications list endpoint.
 */
interface ApplicationsListResponse {
  applications: IApplicationItem[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

/**
 * Interface for the response data from the application details endpoint.
 */
interface ApplicationDetailResponse {
  application: IApplicationItem;
}

/**
 * Interface for the response data from the application status update endpoint.
 */
interface ApplicationStatusUpdateResponse {
  success: boolean;
  application: IApplicationItem;
}

/**
 * Interface for the response data from the bulk action endpoint.
 */
interface BulkActionResponse {
  success: boolean;
  processed: number;
  failed: number;
  applications: IApplicationItem[];
}

/**
 * Custom hook for fetching a paginated list of applications with filtering options.
 * 
 * @param pagination - Pagination parameters (page and limit)
 * @param filters - Optional filters for status, date range, and merchant name
 * @returns Object containing applications data, loading state, error state, and empty state
 */
export function useGetApplications(
  pagination: IPaginationParams,
  filters?: Partial<IApplicationFilters>
) {
  // Construct the query parameters
  const params: Record<string, any> = {
    page: pagination.page,
    limit: pagination.limit,
  };

  // Add filters to params if they exist
  if (filters) {
    if (filters.status && filters.status !== 'all') {
      params.status = filters.status;
    }

    if (filters.merchantName) {
      params.merchantName = filters.merchantName;
    }

    if (filters.dateRange?.startDate) {
      params.startDate = filters.dateRange.startDate?.toISOString();
    }

    if (filters.dateRange?.endDate) {
      params.endDate = filters.dateRange.endDate?.toISOString();
    }
  }

  // Create the SWR key with the endpoint and params
  const url = [API_ENDPOINTS.applications.list, { params }];

  // Fetch data using SWR
  const { data, error, isLoading, isValidating, mutate } = useSWR<ApplicationsListResponse, NormalizedError>(
    url,
    async ([endpoint, config]) => {
      const response = await axiosInstance.get(endpoint, config);
      return response.data;
    },
    {
      ...swrOptions,
      keepPreviousData: true,
    }
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
      refetch: () => mutate(),
    }),
    [data, error, isLoading, isValidating, mutate, pagination.limit, pagination.page]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Custom hook for fetching detailed information about a specific application.
 * 
 * @param applicationId - The ID of the application to fetch
 * @returns Object containing application data, loading state, and error state
 */
export function useGetApplicationById(applicationId: string) {
  // Only create a URL if we have an applicationId
  const url = applicationId ? [API_ENDPOINTS.applications.details(applicationId)] : null;

  // Fetch data using SWR
  const { data, error, isLoading, isValidating, mutate } = useSWR<ApplicationDetailResponse, NormalizedError>(
    url,
    async ([endpoint]) => {
      const response = await axiosInstance.get(endpoint);
      return response.data;
    },
    swrOptions
  );

  // Memoize the return value to prevent unnecessary re-renders
  const memoizedValue = useMemo(
    () => ({
      application: data?.application,
      applicationLoading: isLoading,
      applicationError: error,
      applicationValidating: isValidating,
      refetch: () => mutate(),
    }),
    [data?.application, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Custom hook for updating the status of an application with optimistic updates.
 * 
 * @returns Object containing update function and loading state
 */
export function useUpdateApplicationStatus() {
  // Track loading state
  const [isUpdating, setIsUpdating] = useMemo(() => [false, () => {}], []);

  /**
   * Updates the status of an application with optimistic UI updates.
   * 
   * @param applicationId - The ID of the application to update
   * @param newStatus - The new status to set
   * @param notes - Optional notes to add to the application
   * @returns Promise resolving to the updated application or rejecting with an error
   */
  const updateStatus = useCallback(
    async (applicationId: string, newStatus: IApplicationStatus, notes?: string) => {
      // Endpoint for the specific application
      const endpoint = API_ENDPOINTS.applications.status(applicationId);
      // Key for the application detail in SWR cache
      const detailKey = [API_ENDPOINTS.applications.details(applicationId)];

      try {
        setIsUpdating(true);

        // Optimistically update the application in the cache
        await mutate(
          detailKey,
          async (currentData: ApplicationDetailResponse | undefined) => {
            if (!currentData) return currentData;

            // Create an optimistically updated version of the application
            const updatedApplication = {
              ...currentData.application,
              status: newStatus,
              updated_at: new Date().toISOString(),
              notes: notes || currentData.application.notes,
            };

            // Return the updated data
            return {
              application: updatedApplication,
            };
          },
          // Don't revalidate immediately as we're doing an optimistic update
          { revalidate: false }
        );

        // Make the actual API call to update the status
        const response = await axiosInstance.patch(endpoint, {
          status: newStatus,
          notes,
        });

        // Get the updated application from the response
        const updatedApplication = response.data.application;

        // Update all lists that might contain this application
        // This will update any application list views that are currently loaded
        mutate(
          (key) => Array.isArray(key) && key[0] === API_ENDPOINTS.applications.list,
          async (currentData: ApplicationsListResponse | undefined) => {
            if (!currentData) return currentData;

            // Update the application in the list if it exists
            const updatedApplications = currentData.applications.map((app) =>
              app.id === applicationId ? updatedApplication : app
            );

            // Return the updated list
            return {
              ...currentData,
              applications: updatedApplications,
            };
          },
          // Don't revalidate as we already have the updated data
          { revalidate: false }
        );

        // Update the detail view with the actual response data
        mutate(detailKey, { application: updatedApplication }, { revalidate: false });

        return updatedApplication;
      } catch (error) {
        // If the API call fails, revalidate the cache to get the correct data
        mutate(detailKey);
        
        // Also revalidate any application lists
        mutate((key) => Array.isArray(key) && key[0] === API_ENDPOINTS.applications.list);
        
        // Re-throw the error for the caller to handle
        throw error;
      } finally {
        setIsUpdating(false);
      }
    },
    [setIsUpdating]
  );

  return { updateStatus, isUpdating };
}

// ----------------------------------------------------------------------

/**
 * Custom hook for performing bulk actions on multiple applications.
 * 
 * @returns Object containing bulk action function and loading state
 */
export function useBulkActionApplications() {
  // Track loading state
  const [isProcessing, setIsProcessing] = useMemo(() => [false, () => {}], []);

  /**
   * Performs a bulk action on multiple applications.
   * 
   * @param params - Bulk action parameters including IDs and action type
   * @returns Promise resolving to the result of the bulk action
   */
  const bulkAction = useCallback(
    async (params: IBulkActionParams) => {
      try {
        setIsProcessing(true);

        // Make the API call to perform the bulk action
        const response = await axiosInstance.post(
          API_ENDPOINTS.applications.bulkActions,
          params
        );

        // Get the result from the response
        const result = response.data as BulkActionResponse;

        // Update all application lists that might contain these applications
        mutate(
          (key) => Array.isArray(key) && key[0] === API_ENDPOINTS.applications.list,
          async (currentData: ApplicationsListResponse | undefined) => {
            if (!currentData) return currentData;

            // Create a map of updated applications for quick lookup
            const updatedAppsMap = new Map(
              result.applications.map((app) => [app.id, app])
            );

            // Update applications in the list if they exist
            const updatedApplications = currentData.applications.map((app) => {
              const updatedApp = updatedAppsMap.get(app.id);
              return updatedApp || app;
            });

            // Return the updated list
            return {
              ...currentData,
              applications: updatedApplications,
            };
          },
          // Don't revalidate as we already have the updated data
          { revalidate: false }
        );

        // Also update any individual application detail views that might be open
        for (const app of result.applications) {
          const detailKey = [API_ENDPOINTS.applications.details(app.id)];
          mutate(detailKey, { application: app }, { revalidate: false });
        }

        return result;
      } catch (error) {
        // If the API call fails, revalidate all application lists
        mutate((key) => Array.isArray(key) && key[0] === API_ENDPOINTS.applications.list);
        
        // Re-throw the error for the caller to handle
        throw error;
      } finally {
        setIsProcessing(false);
      }
    },
    [setIsProcessing]
  );

  return { bulkAction, isProcessing };
}