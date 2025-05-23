/**
 * Time Formatting Utilities for Notification Service
 *
 * This file provides utility functions for formatting dates and times in different formats
 * for use in notification payloads and logs. It supports ISO 8601 formatting, timezone handling,
 * and webhook expiration timestamp calculations.
 *
 * Key features:
 * - ISO 8601 formatting for webhook payload timestamps
 * - Timezone handling for consistent date representation across different regions
 * - Utility functions for calculating webhook expiration timestamps
 * - Locale-aware date and time formatting
 * - Relative time formatting for user-friendly displays
 */

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import relativeTime from 'dayjs/plugin/relativeTime';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import advancedFormat from 'dayjs/plugin/advancedFormat';
import { config } from '../config';
import type { IDateValue } from '../types/common';

// Extend dayjs with plugins
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);
dayjs.extend(advancedFormat);

/**
 * Default timezone for date formatting
 * Uses the configured timezone from environment variables or falls back to 'UTC'
 */
export const DEFAULT_TIMEZONE = config.app.defaultTimezone || 'UTC';

/**
 * Default locale for date formatting
 * Uses the configured locale from environment variables or falls back to 'en-US'
 */
export const DEFAULT_LOCALE = config.app.defaultLocale || 'en-US';

/**
 * Available date format types
 */
export enum DateFormatType {
  ISO = 'iso',           // ISO 8601 format (2023-04-15T14:32:17.000Z)
  ISO_DATE = 'isoDate',  // ISO 8601 date only (2023-04-15)
  ISO_TIME = 'isoTime',  // ISO 8601 time only (14:32:17)
  FULL = 'full',         // Full date and time (April 15, 2023 2:32 PM)
  LONG = 'long',         // Long date and time (April 15, 2023 2:32:17 PM)
  MEDIUM = 'medium',     // Medium date and time (Apr 15, 2023 2:32 PM)
  SHORT = 'short',       // Short date and time (4/15/2023 2:32 PM)
  DATE_ONLY = 'dateOnly', // Date only (April 15, 2023)
  TIME_ONLY = 'timeOnly', // Time only (2:32 PM)
  RELATIVE = 'relative'   // Relative time (2 hours ago, in 3 days)
}

/**
 * Date formatting options
 */
export interface FormatDateOptions {
  format?: string | DateFormatType;
  locale?: string;
  timezone?: string;
}

/**
 * Converts a date value to a dayjs object
 *
 * @param date - The date value to convert (string, number, Date, dayjs, or null)
 * @returns A dayjs object or null if the input is null or invalid
 */
export function toDayjs(date: IDateValue | Date | dayjs.Dayjs): dayjs.Dayjs | null {
  if (date === null) {
    return null;
  }

  if (dayjs.isDayjs(date)) {
    return date;
  }

  const dayjsDate = dayjs(date);
  return dayjsDate.isValid() ? dayjsDate : null;
}

/**
 * Formats a date according to the specified format, locale, and timezone
 *
 * @param date - The date to format
 * @param options - Formatting options
 * @returns The formatted date as a string, or an empty string if the date is invalid
 */
export function formatDate(
  date: IDateValue | Date | dayjs.Dayjs,
  options: FormatDateOptions = {}
): string {
  const {
    format = DateFormatType.MEDIUM,
    locale = DEFAULT_LOCALE,
    timezone = DEFAULT_TIMEZONE
  } = options;

  const dayjsDate = toDayjs(date);
  if (!dayjsDate) {
    return '';
  }

  // Set locale for formatting
  const localizedDate = dayjsDate.locale(locale);
  
  // Apply timezone if specified
  const zonedDate = timezone ? localizedDate.tz(timezone) : localizedDate;

  // Format based on predefined format types or custom format string
  switch (format) {
    case DateFormatType.ISO:
      return zonedDate.toISOString();
    case DateFormatType.ISO_DATE:
      return zonedDate.format('YYYY-MM-DD');
    case DateFormatType.ISO_TIME:
      return zonedDate.format('HH:mm:ss');
    case DateFormatType.FULL:
      return zonedDate.format('MMMM D, YYYY h:mm A');
    case DateFormatType.LONG:
      return zonedDate.format('MMMM D, YYYY h:mm:ss A');
    case DateFormatType.MEDIUM:
      return zonedDate.format('MMM D, YYYY h:mm A');
    case DateFormatType.SHORT:
      return zonedDate.format('M/D/YYYY h:mm A');
    case DateFormatType.DATE_ONLY:
      return zonedDate.format('MMMM D, YYYY');
    case DateFormatType.TIME_ONLY:
      return zonedDate.format('h:mm A');
    case DateFormatType.RELATIVE:
      return zonedDate.fromNow();
    default:
      // If format is a string, use it as a custom format
      return typeof format === 'string' ? zonedDate.format(format) : zonedDate.format('YYYY-MM-DD HH:mm:ss');
  }
}

/**
 * Formats a date as ISO 8601 string (2023-04-15T14:32:17.000Z)
 * This is the recommended format for webhook payload timestamps
 *
 * @param date - The date to format
 * @returns The ISO 8601 formatted date string, or an empty string if the date is invalid
 */
export function formatISOString(date: IDateValue | Date | dayjs.Dayjs): string {
  const dayjsDate = toDayjs(date);
  return dayjsDate ? dayjsDate.toISOString() : '';
}

/**
 * Formats a date specifically for webhook payloads
 * Uses ISO 8601 format with UTC timezone for consistent representation
 *
 * @param date - The date to format
 * @returns The formatted date string for webhook payloads
 */
export function formatForWebhook(date: IDateValue | Date | dayjs.Dayjs): string {
  return formatISOString(date);
}

/**
 * Formats a date for log entries
 * Uses ISO 8601 format with timezone information
 *
 * @param date - The date to format
 * @param timezone - The timezone to use (defaults to UTC)
 * @returns The formatted date string for logs
 */
export function formatForLogs(date: IDateValue | Date | dayjs.Dayjs, timezone: string = DEFAULT_TIMEZONE): string {
  const dayjsDate = toDayjs(date);
  if (!dayjsDate) {
    return '';
  }
  
  return timezone === 'UTC' 
    ? dayjsDate.toISOString() 
    : dayjsDate.tz(timezone).format('YYYY-MM-DD HH:mm:ss.SSS Z');
}

/**
 * Calculates a webhook expiration timestamp
 * Adds the specified number of seconds to the current time
 *
 * @param expiresInSeconds - Number of seconds until expiration
 * @returns ISO 8601 formatted expiration timestamp
 */
export function calculateWebhookExpiration(expiresInSeconds: number = 3600): string {
  return dayjs().add(expiresInSeconds, 'second').toISOString();
}

/**
 * Checks if a webhook signature timestamp is expired
 * Webhook signatures typically expire after a certain period to prevent replay attacks
 *
 * @param timestamp - The timestamp to check
 * @param maxAgeSeconds - Maximum age in seconds before considering expired
 * @returns True if the timestamp is expired, false otherwise
 */
export function isWebhookTimestampExpired(
  timestamp: IDateValue | Date | dayjs.Dayjs,
  maxAgeSeconds: number = 300 // Default to 5 minutes
): boolean {
  const timestampDate = toDayjs(timestamp);
  if (!timestampDate) {
    return true; // Invalid timestamps are considered expired
  }
  
  const now = dayjs();
  const diffSeconds = now.diff(timestampDate, 'second');
  
  return diffSeconds > maxAgeSeconds;
}

/**
 * Formats a date range as a string
 *
 * @param startDate - The start date
 * @param endDate - The end date
 * @param options - Formatting options
 * @returns The formatted date range string
 */
export function formatDateRange(
  startDate: IDateValue | Date | dayjs.Dayjs,
  endDate: IDateValue | Date | dayjs.Dayjs,
  options: FormatDateOptions = {}
): string {
  const start = formatDate(startDate, options);
  const end = formatDate(endDate, options);
  
  return `${start} - ${end}`;
}

/**
 * Gets the current timestamp in ISO 8601 format
 *
 * @returns Current time as ISO 8601 string
 */
export function getCurrentISOTimestamp(): string {
  return dayjs().toISOString();
}

/**
 * Calculates the next retry timestamp based on retry count and backoff settings
 *
 * @param retryCount - Current retry attempt number (0-based)
 * @param initialDelayMs - Initial delay in milliseconds
 * @param backoffFactor - Exponential backoff factor
 * @param maxDelayMs - Maximum delay in milliseconds
 * @param useJitter - Whether to add random jitter to prevent thundering herd
 * @returns ISO 8601 formatted timestamp for the next retry
 */
export function calculateNextRetryTime(
  retryCount: number,
  initialDelayMs: number = 1000,
  backoffFactor: number = 2,
  maxDelayMs: number = 60000,
  useJitter: boolean = true
): string {
  // Calculate delay with exponential backoff
  let delay = initialDelayMs * Math.pow(backoffFactor, retryCount);
  
  // Cap at maximum delay
  delay = Math.min(delay, maxDelayMs);
  
  // Add jitter if enabled (±15%)
  if (useJitter) {
    const jitterFactor = 0.15; // 15% jitter
    const jitterRange = delay * jitterFactor;
    delay = delay - jitterRange + (Math.random() * jitterRange * 2);
  }
  
  // Calculate next retry time
  return dayjs().add(delay, 'millisecond').toISOString();
}

/**
 * Formats a date for display in a specific timezone
 *
 * @param date - The date to format
 * @param timezone - The timezone to use
 * @param format - The format to use
 * @returns The formatted date string in the specified timezone
 */
export function formatInTimezone(
  date: IDateValue | Date | dayjs.Dayjs,
  timezone: string,
  format: string | DateFormatType = DateFormatType.MEDIUM
): string {
  return formatDate(date, { timezone, format });
}

/**
 * Formats a date as a relative time string (e.g., "2 hours ago", "in 3 days")
 *
 * @param date - The date to format
 * @param locale - The locale to use for formatting
 * @returns The relative time string
 */
export function formatRelativeTime(
  date: IDateValue | Date | dayjs.Dayjs,
  locale: string = DEFAULT_LOCALE
): string {
  const dayjsDate = toDayjs(date);
  if (!dayjsDate) {
    return '';
  }
  
  return dayjsDate.locale(locale).fromNow();
}

/**
 * Checks if a date is in the future
 *
 * @param date - The date to check
 * @returns True if the date is in the future, false otherwise
 */
export function isFutureDate(date: IDateValue | Date | dayjs.Dayjs): boolean {
  const dayjsDate = toDayjs(date);
  if (!dayjsDate) {
    return false;
  }
  
  return dayjsDate.isAfter(dayjs());
}

/**
 * Checks if a date is in the past
 *
 * @param date - The date to check
 * @returns True if the date is in the past, false otherwise
 */
export function isPastDate(date: IDateValue | Date | dayjs.Dayjs): boolean {
  const dayjsDate = toDayjs(date);
  if (!dayjsDate) {
    return false;
  }
  
  return dayjsDate.isBefore(dayjs());
}

/**
 * Formats a date for display in a notification message
 * Uses a user-friendly format suitable for notifications
 *
 * @param date - The date to format
 * @param locale - The locale to use for formatting
 * @returns The formatted date string for notifications
 */
export function formatForNotification(
  date: IDateValue | Date | dayjs.Dayjs,
  locale: string = DEFAULT_LOCALE
): string {
  return formatDate(date, {
    format: DateFormatType.MEDIUM,
    locale
  });
}