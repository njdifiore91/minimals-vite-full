/**
 * Document Management Hooks for MCA Application Processing System
 * 
 * This file implements custom React hooks for document management using SWR:
 * - useGetDocuments: Retrieves documents associated with an application
 * - useGetDocumentById: Fetches single document with classification metadata
 * - useDocumentDownload: Generates secure download URLs with expiration timestamps
 */

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import type { SWRConfiguration } from 'swr';

import axiosInstance, { fetcher } from '../lib/axios';
import type { IDocumentItem } from '../types/document';

// ----------------------------------------------------------------------

/**
 * SWR configuration options for document-related hooks
 * Disables automatic revalidation to prevent unnecessary API calls
 */
const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};

// ----------------------------------------------------------------------

/**
 * Response type for document list API
 */
interface DocumentsResponse {
  documents: IDocumentItem[];
  total: number;
  page: number;
  limit: number;
}

/**
 * Hook return type for useGetDocuments
 */
interface UseGetDocumentsReturn {
  documents: IDocumentItem[];
  documentsLoading: boolean;
  documentsError: any;
  documentsValidating: boolean;
  documentsEmpty: boolean;
  pagination: {
    total: number;
    page: number;
    limit: number;
  };
}

/**
 * Retrieves documents associated with an application
 * 
 * @param applicationId - Optional application ID to filter documents
 * @param params - Optional query parameters for filtering and pagination
 * @returns Documents data with loading/error states and pagination info
 */
export function useGetDocuments(
  applicationId?: string,
  params?: Record<string, any>
): UseGetDocumentsReturn {
  // Only fetch if applicationId is provided
  const enabled = Boolean(applicationId);
  
  const { data, isLoading, error, isValidating } = useSWR<DocumentsResponse>(
    enabled ? [`/api/v1/documents`, { params: { application_id: applicationId, ...params } }] : null,
    fetcher,
    {
      ...swrOptions,
      keepPreviousData: true,
    }
  );

  const memoizedValue = useMemo<UseGetDocumentsReturn>(
    () => ({
      documents: data?.documents || [],
      documentsLoading: isLoading,
      documentsError: error,
      documentsValidating: isValidating,
      documentsEmpty: !isLoading && !isValidating && !data?.documents.length,
      pagination: {
        total: data?.total || 0,
        page: data?.page || 1,
        limit: data?.limit || 10,
      },
    }),
    [data, error, isLoading, isValidating]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Response type for single document API
 */
interface DocumentResponse {
  document: IDocumentItem;
}

/**
 * Hook return type for useGetDocumentById
 */
interface UseGetDocumentByIdReturn {
  document: IDocumentItem | undefined;
  documentLoading: boolean;
  documentError: any;
  documentValidating: boolean;
}

/**
 * Fetches a single document with classification metadata
 * 
 * @param documentId - Document ID to retrieve
 * @returns Document data with loading/error states
 */
export function useGetDocumentById(documentId?: string): UseGetDocumentByIdReturn {
  // Only fetch if documentId is provided
  const enabled = Boolean(documentId);
  
  const { data, isLoading, error, isValidating } = useSWR<DocumentResponse>(
    enabled ? `/api/v1/documents/${documentId}` : null,
    fetcher,
    swrOptions
  );

  const memoizedValue = useMemo<UseGetDocumentByIdReturn>(
    () => ({
      document: data?.document,
      documentLoading: isLoading,
      documentError: error,
      documentValidating: isValidating,
    }),
    [data?.document, error, isLoading, isValidating]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Response type for document download API
 */
interface DocumentDownloadResponse {
  downloadUrl: string;
  expiresAt: number; // Timestamp in milliseconds
}

/**
 * Hook return type for useDocumentDownload
 */
interface UseDocumentDownloadReturn {
  downloadUrl: string | null;
  expiresAt: number | null;
  isGenerating: boolean;
  error: any;
  generateDownloadUrl: () => Promise<string | null>;
  downloadDocument: () => Promise<void>;
}

/**
 * Generates secure download URLs with expiration timestamps
 * 
 * @param documentId - Document ID to download
 * @returns Download URL data with generation and download functions
 */
export function useDocumentDownload(documentId?: string): UseDocumentDownloadReturn {
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<any>(null);

  /**
   * Generates a new download URL for the document
   * @returns Promise resolving to the download URL or null on error
   */
  const generateDownloadUrl = async (): Promise<string | null> => {
    if (!documentId) return null;
    
    try {
      setIsGenerating(true);
      setError(null);
      
      const response = await axiosInstance.get(`/api/v1/documents/${documentId}/download`);
      
      // Extract the download URL and expiration from the response
      const { downloadUrl, expiresAt } = response.data;
      
      setDownloadUrl(downloadUrl);
      setExpiresAt(expiresAt);
      
      return downloadUrl;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setIsGenerating(false);
    }
  };

  /**
   * Initiates document download in the browser
   */
  const downloadDocument = async (): Promise<void> => {
    if (!documentId) return;
    
    try {
      setIsGenerating(true);
      setError(null);
      
      // Get a fresh download URL if none exists or the current one is expired
      const currentTime = Date.now();
      let url = downloadUrl;
      
      if (!url || !expiresAt || currentTime >= expiresAt) {
        url = await generateDownloadUrl();
        if (!url) throw new Error('Failed to generate download URL');
      }
      
      // Trigger the download by opening the URL in a new tab/window
      window.open(url, '_blank');
    } catch (err) {
      setError(err);
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    downloadUrl,
    expiresAt,
    isGenerating,
    error,
    generateDownloadUrl,
    downloadDocument,
  };
}