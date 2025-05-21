import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * Document type categories for the MCA system
 * Used for classification and processing routing
 */
export enum IDocumentType {
  BANK_STATEMENT = 'bank_statement',
  TAX_RETURN = 'tax_return',
  ID_VERIFICATION = 'id_verification',
  LOAN_APPLICATION = 'loan_application',
  PAY_STUB = 'pay_stub',
  BUSINESS_LICENSE = 'business_license',
  FINANCIAL_STATEMENT = 'financial_statement',
  CREDIT_REPORT = 'credit_report',
  UTILITY_BILL = 'utility_bill',
  OTHER = 'other'
}

/**
 * Confidence level for document classification and field extraction
 * Used to determine if human review is needed
 */
export interface IDocumentConfidence {
  /** Overall confidence score (0-100) */
  score: number;
  /** Threshold for automatic processing (typically 75) */
  threshold: number;
  /** Whether this document requires human review */
  requiresReview: boolean;
  /** Optional reviewer comments */
  reviewerNotes?: string;
  /** Timestamp of review completion if reviewed */
  reviewedAt?: IDateValue;
  /** User ID of reviewer if reviewed */
  reviewerId?: string;
}

/**
 * AI-generated classification metadata for documents
 * Contains information about the document type and confidence
 */
export interface IDocumentClassification {
  /** Primary document type determined by AI */
  primaryType: IDocumentType;
  /** Confidence information for the classification */
  confidence: IDocumentConfidence;
  /** Alternative document types with lower confidence scores */
  alternativeTypes?: Array<{
    type: IDocumentType;
    score: number;
  }>;
  /** Classification model version used */
  modelVersion: string;
  /** Timestamp when classification was performed */
  classifiedAt: IDateValue;
}

/**
 * OCR-extracted field with confidence metrics
 * Represents a single data point extracted from a document
 */
export interface IExtractedField {
  /** Field name/key */
  name: string;
  /** Extracted value */
  value: string;
  /** Confidence score for this extraction (0-100) */
  confidence: number;
  /** Whether this field requires human verification */
  requiresVerification: boolean;
  /** Bounding box coordinates in the document (x1,y1,x2,y2) */
  boundingBox?: [number, number, number, number];
  /** Page number where this field was found */
  pageNumber: number;
  /** Whether this field has been verified by a human */
  verified: boolean;
  /** Timestamp of verification if verified */
  verifiedAt?: IDateValue;
  /** User ID of verifier if verified */
  verifierId?: string;
}

/**
 * Core document data structure for the MCA system
 * Represents a document in the application with all metadata
 */
export interface IDocumentItem {
  /** Unique document identifier */
  id: string;
  /** Associated application ID */
  applicationId: string;
  /** Document file name */
  name: string;
  /** File size in bytes */
  size: number;
  /** File type/extension */
  type: string;
  /** S3 storage path */
  storagePath: string;
  /** Document classification information */
  classification: IDocumentClassification;
  /** Timestamp when document was uploaded */
  uploadedAt: IDateValue;
  /** Timestamp when document was last modified */
  modifiedAt: IDateValue;
  /** User who uploaded the document */
  uploadedBy: string;
  /** Whether document is favorited/starred */
  isFavorited: boolean;
  /** Document tags for categorization */
  tags: string[];
  /** Extracted fields from OCR processing */
  extractedFields?: IExtractedField[];
  /** Processing status (pending, processing, completed, error) */
  status: 'pending' | 'processing' | 'completed' | 'error';
  /** Error message if processing failed */
  errorMessage?: string;
  /** Number of pages in the document */
  pageCount?: number;
  /** Whether document is encrypted/password-protected */
  isEncrypted: boolean;
  /** Signed URL for secure download (with expiration) */
  downloadUrl?: string;
  /** URL expiration timestamp */
  downloadUrlExpiry?: IDateValue;
}

/**
 * Configuration options for the document viewer component
 * Controls the behavior and appearance of the document viewer
 */
export interface IDocumentViewerConfig {
  /** Whether to show classification metadata */
  showClassification: boolean;
  /** Whether to show confidence scores */
  showConfidence: boolean;
  /** Whether to show extracted fields */
  showExtractedFields: boolean;
  /** Whether to enable document download */
  enableDownload: boolean;
  /** Whether to enable document printing */
  enablePrint: boolean;
  /** Whether to enable document sharing */
  enableSharing: boolean;
  /** Whether to enable document annotation */
  enableAnnotation: boolean;
  /** Maximum zoom level (percentage) */
  maxZoom: number;
  /** Initial zoom level (percentage) */
  defaultZoom: number;
  /** Whether to show document thumbnails */
  showThumbnails: boolean;
  /** Whether to enable fullscreen mode */
  enableFullscreen: boolean;
  /** Whether to enable keyboard shortcuts */
  enableKeyboardShortcuts: boolean;
  /** Whether to show page navigation */
  showPageNavigation: boolean;
  /** Custom CSS class names */
  customClasses?: {
    container?: string;
    toolbar?: string;
    viewer?: string;
    thumbnails?: string;
  };
  /** Callback when document fails to load */
  onError?: (error: Error) => void;
  /** Callback when document is successfully loaded */
  onLoad?: () => void;
  /** Callback when document download is initiated */
  onDownload?: () => void;
}