/**
 * Format Time Utilities
 * 
 * This file provides utility functions for formatting dates and times in various formats,
 * with a focus on ISO 8601 format for webhook payloads and logs. It handles timezone
 * offsets correctly and provides functions for calculating webhook expiration timestamps.
 * 
 * Adapted for Node.js environment by removing browser-specific features while maintaining
 * the same API for consistency with the original file.
 */

import { IDateValue } from '../types/common';

/**
 * Pads a number to ensure it has at least 2 digits
 * @param {number} n - The number to pad
 * @returns {string} The padded number as a string
 */
const pad = (n: number): string => `${Math.abs(n)}`.padStart(2, '0');

/**
 * Pads a number to ensure it has at least 3 digits (for milliseconds)
 * @param {number} n - The number to pad
 * @returns {string} The padded number as a string
 */
const padMs = (n: number): string => `${Math.abs(n)}`.padStart(3, '0');

/**
 * Gets timezone offset in ISO format (+hh:mm or -hh:mm)
 * @param {Date} date - The date to get timezone offset for
 * @returns {string} The timezone offset in ISO format
 */
const getTimezoneOffset = (date: Date): string => {
  // getTimezoneOffset returns minutes, positive for negative UTC offset and vice versa
  const tzOffset = -date.getTimezoneOffset();
  const sign = tzOffset >= 0 ? '+' : '-';
  const hours = Math.floor(Math.abs(tzOffset) / 60);
  const minutes = Math.abs(tzOffset) % 60;
  
  return `${sign}${pad(hours)}:${pad(minutes)}`;
};

/**
 * Formats a date to ISO 8601 format with timezone offset
 * @param {Date} date - The date to format
 * @returns {string} The formatted date in ISO 8601 format with timezone offset
 */
export function formatToISOWithTimezone(date: Date): string {
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1); // getMonth() is 0-indexed
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());
  const milliseconds = padMs(date.getMilliseconds());
  const tzOffset = getTimezoneOffset(date);
  
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${milliseconds}${tzOffset}`;
}

/**
 * Formats a date to ISO 8601 format in UTC (Z)
 * @param {Date} date - The date to format
 * @returns {string} The formatted date in ISO 8601 format with Z timezone
 */
export function formatToISOString(date: Date): string {
  return date.toISOString();
}

/**
 * Creates a standardized date value object with multiple representations
 * @param {Date} date - The date to format
 * @returns {IDateValue} Object containing ISO string, timestamp, and Date object
 */
export function createDateValue(date: Date): IDateValue {
  return {
    iso: formatToISOWithTimezone(date),
    timestamp: date.getTime(),
    date: new Date(date)
  };
}

/**
 * Calculates a webhook expiration timestamp
 * @param {number} ttlMinutes - Time to live in minutes
 * @returns {IDateValue} Expiration date as a DateValue object
 */
export function calculateWebhookExpiration(ttlMinutes: number = 60): IDateValue {
  const now = new Date();
  const expirationDate = new Date(now.getTime() + ttlMinutes * 60 * 1000);
  return createDateValue(expirationDate);
}

/**
 * Formats a date for display in logs
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string for logs
 */
export function formatForLogs(date: Date): string {
  return `${formatToISOWithTimezone(date)}`;
}

/**
 * Checks if a webhook has expired
 * @param {Date|number|string} expirationDate - The expiration date (Date object, timestamp, or ISO string)
 * @returns {boolean} True if expired, false otherwise
 */
export function isWebhookExpired(expirationDate: Date | number | string): boolean {
  const now = new Date().getTime();
  let expiration: number;
  
  if (expirationDate instanceof Date) {
    expiration = expirationDate.getTime();
  } else if (typeof expirationDate === 'number') {
    expiration = expirationDate;
  } else {
    // Assume ISO string
    expiration = new Date(expirationDate).getTime();
  }
  
  return now > expiration;
}

/**
 * Formats a date for display in notification payloads
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string for notification payloads
 */
export function formatForNotification(date: Date): string {
  return formatToISOWithTimezone(date);
}

/**
 * Formats a relative time (e.g., "5 minutes ago")
 * @param {Date} date - The date to format relative to now
 * @returns {string} Formatted relative time string
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffDay > 0) {
    return diffDay === 1 ? '1 day ago' : `${diffDay} days ago`;
  }
  if (diffHour > 0) {
    return diffHour === 1 ? '1 hour ago' : `${diffHour} hours ago`;
  }
  if (diffMin > 0) {
    return diffMin === 1 ? '1 minute ago' : `${diffMin} minutes ago`;
  }
  return diffSec <= 5 ? 'just now' : `${diffSec} seconds ago`;
}

/**
 * Adds a specified number of minutes to a date
 * @param {Date} date - The base date
 * @param {number} minutes - Number of minutes to add
 * @returns {Date} New date with added minutes
 */
export function addMinutes(date: Date, minutes: number): Date {
  return new Date(date.getTime() + minutes * 60 * 1000);
}

/**
 * Formats a date for webhook retry attempts
 * @param {Date} date - The date to format
 * @param {number} attempt - The retry attempt number
 * @returns {string} Formatted date string with retry information
 */
export function formatForRetry(date: Date, attempt: number): string {
  return `${formatToISOWithTimezone(date)} (Retry ${attempt})`;
}

/**
 * Parses an ISO 8601 string to a Date object
 * @param {string} isoString - The ISO 8601 string to parse
 * @returns {Date} The parsed Date object
 */
export function parseISOString(isoString: string): Date {
  return new Date(isoString);
}

/**
 * Gets the current date and time as an IDateValue
 * @returns {IDateValue} Current date and time
 */
export function getCurrentDate(): IDateValue {
  return createDateValue(new Date());
}

/**
 * Formats a date for use in webhook headers
 * @param {Date} date - The date to format
 * @returns {string} RFC 7231 formatted date for HTTP headers
 */
export function formatForHttpHeader(date: Date): string {
  return date.toUTCString();
}