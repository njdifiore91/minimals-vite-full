import type { SWRConfiguration } from 'swr';
import useSWR from 'swr';
import { useMemo } from 'react';

import axiosInstance, { API_ENDPOINTS, NormalizedError } from 'src/lib/axios';

// ----------------------------------------------------------------------
// MCA Document Management Hooks
// These hooks provide standardized document access patterns for the MCA application system
// They handle loading/error states and ensure consistent caching across the application

/**
 * Document classification types supported by the system
 */
export enum DocumentClassification {
  BANK_STATEMENT = 'BANK_STATEMENT',
  BUSINESS_LICENSE = 'BUSINESS_LICENSE',
  TAX_RETURN = 'TAX_RETURN',
  INVOICE = 'INVOICE',
  IDENTITY_DOCUMENT = 'IDENTITY_DOCUMENT',
  UTILITY_BILL = 'UTILITY_BILL',
  CREDIT_CARD_STATEMENT = 'CREDIT_CARD_STATEMENT',
  MERCHANT_PROCESSING_STATEMENT = 'MERCHANT_PROCESSING_STATEMENT',
  LEASE_AGREEMENT = 'LEASE_AGREEMENT',
  OTHER = 'OTHER',
}

/**
 * Document interface representing a document in the MCA system
 */
export interface IDocument {
  id: string;
  applicationId: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  uploadedAt: string;
  classification: DocumentClassification;
  confidenceScore: number;
  metadata: {
    pageCount?: number;
    extractedData?: Record<string, any>;
    [key: string]: any;
  };
  storagePath: string;
}

/**
 * Document download URL interface with expiration
 */
export interface IDocumentDownloadUrl {
  url: string;
  expiresAt: string;
}

// ----------------------------------------------------------------------

// Custom fetcher function for SWR that uses our axios instance
const fetcher = async (url: string, params?: any) => {
  try {
    const response = await axiosInstance.get(url, { params });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// SWR configuration to disable automatic revalidation
const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};

// ----------------------------------------------------------------------

/**
 * Response type for document list API
 */
type DocumentsData = {
  documents: IDocument[];
};

/**
 * Hook to retrieve documents associated with an application
 * @param applicationId - ID of the application to fetch documents for
 * @returns Object containing documents array and loading/error states
 */
export function useGetDocuments(applicationId: string) {
  const { data, error, isLoading, isValidating } = useSWR<DocumentsData, NormalizedError>(
    applicationId ? [API_ENDPOINTS.documents.list, { applicationId }] : null,
    ([url, params]) => fetcher(url, params),
    swrOptions
  );

  const memoizedValue = useMemo(
    () => ({
      documents: data?.documents || [],
      documentsLoading: isLoading,
      documentsError: error,
      documentsValidating: isValidating,
      documentsEmpty: !isLoading && !isValidating && !data?.documents.length,
    }),
    [data?.documents, error, isLoading, isValidating]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

/**
 * Response type for single document API
 */
type DocumentData = {
  document: IDocument;
};

/**
 * Hook to fetch a single document with classification metadata
 * @param documentId - ID of the document to fetch
 * @returns Object containing document data and loading/error states
 */
export function useGetDocumentById(documentId: string) {
  const { data, error, isLoading, isValidating } = useSWR<DocumentData, NormalizedError>(
    documentId ? [API_ENDPOINTS.documents.details(documentId), {}] : null,
    ([url, params]) => fetcher(url, params),
    swrOptions
  );

  const memoizedValue = useMemo(
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
 * Response type for document download URL API
 */
type DocumentDownloadData = {
  downloadUrl: IDocumentDownloadUrl;
};

/**
 * Hook to generate secure download URLs with expiration timestamps
 * @param documentId - ID of the document to generate download URL for
 * @returns Object containing download URL data and loading/error states
 */
export function useDocumentDownload(documentId: string) {
  const { data, error, isLoading, isValidating } = useSWR<DocumentDownloadData, NormalizedError>(
    documentId ? [API_ENDPOINTS.documents.download(documentId), {}] : null,
    ([url, params]) => fetcher(url, params),
    {
      ...swrOptions,
      // Don't cache download URLs as they expire
      revalidateOnMount: true,
      // Set a short dedupingInterval to allow frequent refreshing of download URLs
      dedupingInterval: 5000, // 5 seconds
    }
  );

  const memoizedValue = useMemo(
    () => ({
      downloadUrl: data?.downloadUrl,
      downloadLoading: isLoading,
      downloadError: error,
      downloadValidating: isValidating,
      // Helper function to trigger download in the browser
      triggerDownload: () => {
        if (data?.downloadUrl?.url) {
          // Create a temporary anchor element to trigger the download
          const link = document.createElement('a');
          link.href = data.downloadUrl.url;
          link.setAttribute('download', ''); // This will use the server's suggested filename
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          return true;
        }
        return false;
      },
      // Check if the download URL is still valid
      isExpired: () => {
        if (data?.downloadUrl?.expiresAt) {
          const expiresAt = new Date(data.downloadUrl.expiresAt).getTime();
          const now = new Date().getTime();
          return now > expiresAt;
        }
        return true; // If no expiration time, consider it expired
      },
    }),
    [data?.downloadUrl, error, isLoading, isValidating]
  );

  return memoizedValue;
}