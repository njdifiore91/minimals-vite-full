import type { IDateValue, IDatePickerControl } from './common';

// ----------------------------------------------------------------------

/**
 * Enum representing the possible statuses of a merchant cash advance application.
 * Used for filtering, display, and API interactions.
 */
export enum IApplicationStatus {
  PENDING = 'pending',
  REVIEWING = 'reviewing',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  INCOMPLETE = 'incomplete',
}

/**
 * Interface for merchant business details associated with an application.
 * Maps to the MerchantDetails database schema.
 */
export interface IMerchantDetails {
  id: string;
  application_id: string;
  legal_name: string;
  dba_name: string; // Doing Business As name
  ein: string; // Employer Identification Number
  address: string;
  industry: string;
  revenue: number;
}

/**
 * Interface for application search and filtering parameters.
 * Used in the application list view for filtering results.
 */
export interface IApplicationFilters {
  status: IApplicationStatus | string;
  dateRange: {
    startDate: IDatePickerControl;
    endDate: IDatePickerControl;
  };
  merchantName: string;
}

/**
 * Interface representing a merchant cash advance application.
 * Core data structure for the application processing system.
 */
export interface IApplicationItem {
  id: string;
  status: IApplicationStatus;
  metadata: Record<string, any>; // Flexible metadata from document processing
  created_at: IDateValue;
  updated_at: IDateValue;
  review_status: string;
  merchant: IMerchantDetails;
  documents: Array<{
    id: string;
    type: string;
    storage_path: string;
    classification: string;
    uploaded_at: IDateValue;
    confidence_score: number;
  }>;
  processing_time?: number; // Time taken to process the application (in seconds)
  assigned_to?: string; // User ID of the assigned reviewer
  notes?: string; // Additional notes from reviewers
}

/**
 * Interface for application table filtering options.
 * Extended version of IApplicationFilters with additional options for admin views.
 */
export interface IApplicationTableFilters extends IApplicationFilters {
  processingTime: number | null;
  assignedTo: string | null;
  documentTypes: string[];
  confidenceScore: number | null;
}

/**
 * Interface for bulk action parameters on multiple applications.
 * Used for operations like batch approval, rejection, or assignment.
 */
export interface IBulkActionParams {
  ids: string[];
  action: 'approve' | 'reject' | 'assign' | 'mark_incomplete';
  assignee?: string; // Required only for 'assign' action
  notes?: string; // Optional notes for the action
}