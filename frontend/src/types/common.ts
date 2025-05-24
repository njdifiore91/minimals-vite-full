/**
 * Common type definitions used across the application
 */

/**
 * Represents a date value that can be a Date object, ISO string, or timestamp
 */
export type IDateValue = Date | string | number;

/**
 * Represents a paginated response from the API
 */
export interface IPaginatedResponse<T> {
  /** Array of items */
  items: T[];
  /** Total number of items */
  total: number;
  /** Current page number */
  page: number;
  /** Number of items per page */
  limit: number;
  /** Total number of pages */
  totalPages: number;
  /** Whether there is a next page */
  hasNextPage: boolean;
  /** Whether there is a previous page */
  hasPrevPage: boolean;
}

/**
 * Represents pagination parameters for API requests
 */
export interface IPaginationParams {
  /** Page number (1-based) */
  page?: number;
  /** Number of items per page */
  limit?: number;
  /** Sort field */
  sortBy?: string;
  /** Sort direction */
  sortDirection?: 'asc' | 'desc';
}

/**
 * Represents filter parameters for API requests
 */
export interface IFilterParams {
  /** Search query */
  search?: string;
  /** Filter by status */
  status?: string | string[];
  /** Filter by date range */
  dateRange?: {
    /** Start date */
    start?: IDateValue;
    /** End date */
    end?: IDateValue;
  };
  /** Additional custom filters */
  [key: string]: any;
}

/**
 * Represents an API error response
 */
export interface IApiError {
  /** Error message */
  message: string;
  /** Error code */
  code?: string;
  /** HTTP status code */
  status?: number;
  /** Additional error details */
  details?: Record<string, any>;
  /** Field-specific validation errors */
  fieldErrors?: Record<string, string>;
}

/**
 * Represents a user's role in the system
 */
export enum UserRole {
  /** System administrator with full access */
  ADMIN = 'admin',
  /** Operations staff with application processing access */
  OPERATIONS = 'operations',
  /** Read-only user */
  VIEWER = 'viewer',
}

/**
 * Represents a user's permission in the system
 */
export enum Permission {
  /** View applications */
  VIEW_APPLICATIONS = 'view:applications',
  /** Create applications */
  CREATE_APPLICATIONS = 'create:applications',
  /** Update applications */
  UPDATE_APPLICATIONS = 'update:applications',
  /** Delete applications */
  DELETE_APPLICATIONS = 'delete:applications',
  /** View documents */
  VIEW_DOCUMENTS = 'view:documents',
  /** Upload documents */
  UPLOAD_DOCUMENTS = 'upload:documents',
  /** Delete documents */
  DELETE_DOCUMENTS = 'delete:documents',
  /** Verify document fields */
  VERIFY_DOCUMENT_FIELDS = 'verify:document-fields',
  /** Configure webhooks */
  MANAGE_WEBHOOKS = 'manage:webhooks',
  /** View users */
  VIEW_USERS = 'view:users',
  /** Create users */
  CREATE_USERS = 'create:users',
  /** Update users */
  UPDATE_USERS = 'update:users',
  /** Delete users */
  DELETE_USERS = 'delete:users',
}

/**
 * Represents a theme mode
 */
export type ThemeMode = 'light' | 'dark' | 'system';

/**
 * Represents a theme color scheme
 */
export type ThemeColorPreset = 'default' | 'cyan' | 'purple' | 'blue' | 'orange' | 'red' | 'funding';

/**
 * Represents a theme contrast level
 */
export type ThemeContrast = 'default' | 'bold';

/**
 * Represents a theme layout
 */
export type ThemeLayout = 'vertical' | 'horizontal' | 'mini';

/**
 * Represents a theme stretch option
 */
export type ThemeStretch = boolean;

/**
 * Represents a notification type
 */
export type NotificationType = 'info' | 'success' | 'warning' | 'error';

/**
 * Represents a notification
 */
export interface INotification {
  /** Unique identifier */
  id: string;
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** Notification type */
  type: NotificationType;
  /** Notification creation date */
  createdAt: IDateValue;
  /** Whether the notification has been read */
  isRead: boolean;
  /** Action URL (optional) */
  actionUrl?: string;
  /** Action label (optional) */
  actionLabel?: string;
}