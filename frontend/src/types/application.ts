/**
 * TypeScript interfaces for MCA application data
 */

// Merchant details interface
export interface IMerchantDetails {
  id: string;
  applicationId: string;
  legalName: string;
  dbaName?: string;
  ein: string;
  address: string;
  industry?: string;
  revenue?: number;
}

// Document interface
export interface IDocument {
  id: string;
  applicationId: string;
  type: string;
  storagePath: string;
  classification: string;
  uploadedAt: Date | string;
  metadata: Record<string, any>;
}

// Application status type
export type ApplicationStatus = 
  | 'pending'
  | 'in_review'
  | 'approved'
  | 'rejected'
  | 'incomplete';

// Application interface
export interface IApplication {
  id: string;
  status: ApplicationStatus;
  metadata: Record<string, any>;
  createdAt: Date | string;
  updatedAt: Date | string;
  submittedAt: Date | string;
  reviewStatus?: string;
  requestedAmount: number;
  merchant: IMerchantDetails;
  documents?: IDocument[];
}

// Application list response interface
export interface IApplicationListResponse {
  applications: IApplication[];
  total: number;
  page: number;
  limit: number;
}

// Application filter options
export interface IApplicationFilter {
  status?: ApplicationStatus;
  dateRange?: {
    start: Date | string;
    end: Date | string;
  };
  merchantName?: string;
  requestedAmountRange?: {
    min: number;
    max: number;
  };
  industry?: string;
}