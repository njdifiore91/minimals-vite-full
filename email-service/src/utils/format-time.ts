/**
 * Date and time formatting utilities for the Email Service
 * 
 * This module provides functions for ISO timestamp generation, RFC 2822 formatting,
 * date comparison, duration calculation, and relative time formatting. It's essential
 * for consistent timestamp handling in logs, message publishing, and email metadata extraction.
 */

import type { Dayjs, OpUnitType } from 'dayjs';
import type { IDateValue } from '../types/common';

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';

// ----------------------------------------------------------------------

// Extend dayjs with required plugins
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(duration);
dayjs.extend(relativeTime);
dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);

// Set default timezone to UTC for server-side operations
dayjs.tz.setDefault('UTC');

// ----------------------------------------------------------------------

/**
 * Type for date input values that can be parsed by dayjs
 */
export type DateInput = Dayjs | Date | string | number | null | undefined;

/**
 * Email-specific date formats
 */
export const emailDateFormats = {
  /** ISO 8601 format (2023-04-17T12:00:00Z) */
  iso8601: 'YYYY-MM-DDTHH:mm:ss[Z]',
  
  /** RFC 2822 format for email headers (Mon, 17 Apr 2023 12:00:00 +0000) */
  rfc2822: 'ddd, DD MMM YYYY HH:mm:ss ZZ',
  
  /** ISO 8601 with milliseconds (2023-04-17T12:00:00.000Z) */
  isoWithMs: 'YYYY-MM-DDTHH:mm:ss.SSS[Z]',
  
  /** Simple date format (2023-04-17) */
  simpleDate: 'YYYY-MM-DD',
  
  /** Simple time format (12:00:00) */
  simpleTime: 'HH:mm:ss',
  
  /** Log timestamp format (2023-04-17 12:00:00.000) */
  logTimestamp: 'YYYY-MM-DD HH:mm:ss.SSS',
};

/**
 * Checks if a date value is valid
 * 
 * @param date - The date to validate
 * @returns True if the date is valid, false otherwise
 */
export const isValidDate = (date: DateInput): boolean =>
  date !== null && date !== undefined && dayjs(date).isValid();

// ----------------------------------------------------------------------

/**
 * Creates a standardized date value object with ISO string and timestamp
 * 
 * @param date - The date to format (defaults to current time)
 * @returns An IDateValue object with ISO string and timestamp
 */
export function createDateValue(date: DateInput = new Date()): IDateValue {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to createDateValue');
  }
  
  const dayjsDate = dayjs(date).utc();
  
  return {
    iso: dayjsDate.format(),
    timestamp: dayjsDate.valueOf(),
  };
}

/**
 * Gets the current time as an IDateValue
 * 
 * @returns Current time as IDateValue
 */
export function getCurrentTime(): IDateValue {
  return createDateValue(new Date());
}

/**
 * Formats a date in ISO 8601 format
 * 
 * @param date - The date to format
 * @param withMs - Whether to include milliseconds
 * @returns ISO 8601 formatted date string
 */
export function formatISODate(date: DateInput, withMs = false): string {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to formatISODate');
  }
  
  const format = withMs ? emailDateFormats.isoWithMs : emailDateFormats.iso8601;
  return dayjs(date).utc().format(format);
}

/**
 * Formats a date in RFC 2822 format for email headers
 * 
 * @param date - The date to format
 * @returns RFC 2822 formatted date string
 */
export function formatRFC2822Date(date: DateInput): string {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to formatRFC2822Date');
  }
  
  return dayjs(date).utc().format(emailDateFormats.rfc2822);
}

/**
 * Formats a date for log entries
 * 
 * @param date - The date to format
 * @returns Formatted date string for logs
 */
export function formatLogDate(date: DateInput = new Date()): string {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to formatLogDate');
  }
  
  return dayjs(date).utc().format(emailDateFormats.logTimestamp);
}

/**
 * Parses an email date header (RFC 2822 format)
 * 
 * @param dateHeader - The date header string from email
 * @returns Parsed date as IDateValue
 */
export function parseEmailDateHeader(dateHeader: string): IDateValue {
  const parsedDate = dayjs(dateHeader).utc();
  
  if (!parsedDate.isValid()) {
    throw new Error(`Invalid email date header: ${dateHeader}`);
  }
  
  return createDateValue(parsedDate);
}

// ----------------------------------------------------------------------

/**
 * Calculates the age of a message in milliseconds
 * 
 * @param messageDate - The date of the message
 * @param referenceDate - The reference date (defaults to current time)
 * @returns Age in milliseconds
 */
export function calculateMessageAge(messageDate: DateInput, referenceDate: DateInput = new Date()): number {
  if (!isValidDate(messageDate) || !isValidDate(referenceDate)) {
    throw new Error('Invalid date provided to calculateMessageAge');
  }
  
  const start = dayjs(messageDate);
  const end = dayjs(referenceDate);
  
  return end.diff(start);
}

/**
 * Formats a duration in milliseconds to a human-readable string
 * 
 * @param milliseconds - Duration in milliseconds
 * @returns Human-readable duration string
 */
export function formatDuration(milliseconds: number): string {
  return dayjs.duration(milliseconds).humanize();
}

/**
 * Calculates processing time between two timestamps
 * 
 * @param startTime - Start timestamp
 * @param endTime - End timestamp (defaults to current time)
 * @returns Processing time in milliseconds
 */
export function calculateProcessingTime(startTime: DateInput, endTime: DateInput = new Date()): number {
  if (!isValidDate(startTime) || !isValidDate(endTime)) {
    throw new Error('Invalid date provided to calculateProcessingTime');
  }
  
  return dayjs(endTime).diff(dayjs(startTime));
}

/**
 * Formats processing time for logging
 * 
 * @param milliseconds - Processing time in milliseconds
 * @returns Formatted processing time string
 */
export function formatProcessingTime(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  }
  
  return `${(milliseconds / 1000).toFixed(2)}s`;
}

// ----------------------------------------------------------------------

/**
 * Checks if a date is before another date
 * 
 * @param date - The date to check
 * @param compareDate - The date to compare against
 * @returns True if date is before compareDate
 */
export function isBefore(date: DateInput, compareDate: DateInput): boolean {
  if (!isValidDate(date) || !isValidDate(compareDate)) {
    return false;
  }
  
  return dayjs(date).isBefore(dayjs(compareDate));
}

/**
 * Checks if a date is after another date
 * 
 * @param date - The date to check
 * @param compareDate - The date to compare against
 * @returns True if date is after compareDate
 */
export function isAfter(date: DateInput, compareDate: DateInput): boolean {
  if (!isValidDate(date) || !isValidDate(compareDate)) {
    return false;
  }
  
  return dayjs(date).isAfter(dayjs(compareDate));
}

/**
 * Checks if a date is between two other dates
 * 
 * @param date - The date to check
 * @param startDate - The start date of the range
 * @param endDate - The end date of the range
 * @param inclusivity - Inclusion of start and end dates ('()' = exclusive, '[]' = inclusive, '[)' = start inclusive, end exclusive)
 * @returns True if date is between startDate and endDate
 */
export function isBetween(
  date: DateInput,
  startDate: DateInput,
  endDate: DateInput,
  inclusivity: '()' | '[]' | '[)' | '(]' = '[]'
): boolean {
  if (!isValidDate(date) || !isValidDate(startDate) || !isValidDate(endDate)) {
    return false;
  }
  
  const d = dayjs(date);
  const start = dayjs(startDate);
  const end = dayjs(endDate);
  
  if (inclusivity === '[]') {
    return d.isSameOrAfter(start) && d.isSameOrBefore(end);
  }
  
  if (inclusivity === '()') {
    return d.isAfter(start) && d.isBefore(end);
  }
  
  if (inclusivity === '[)') {
    return d.isSameOrAfter(start) && d.isBefore(end);
  }
  
  if (inclusivity === '(]') {
    return d.isAfter(start) && d.isSameOrBefore(end);
  }
  
  return false;
}

/**
 * Checks if two dates are the same, optionally comparing only specific units
 * 
 * @param date1 - First date to compare
 * @param date2 - Second date to compare
 * @param unit - Unit to compare (year, month, day, hour, minute, second)
 * @returns True if dates are the same for the specified unit
 */
export function isSame(
  date1: DateInput,
  date2: DateInput,
  unit?: OpUnitType
): boolean {
  if (!isValidDate(date1) || !isValidDate(date2)) {
    return false;
  }
  
  return dayjs(date1).isSame(dayjs(date2), unit);
}

// ----------------------------------------------------------------------

/**
 * Adds a duration to a date
 * 
 * @param date - The base date
 * @param amount - The amount to add
 * @param unit - The unit to add (years, months, days, hours, minutes, seconds)
 * @returns New date with duration added
 */
export function addToDate(date: DateInput, amount: number, unit: OpUnitType): IDateValue {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to addToDate');
  }
  
  const newDate = dayjs(date).add(amount, unit);
  return createDateValue(newDate);
}

/**
 * Subtracts a duration from a date
 * 
 * @param date - The base date
 * @param amount - The amount to subtract
 * @param unit - The unit to subtract (years, months, days, hours, minutes, seconds)
 * @returns New date with duration subtracted
 */
export function subtractFromDate(date: DateInput, amount: number, unit: OpUnitType): IDateValue {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to subtractFromDate');
  }
  
  const newDate = dayjs(date).subtract(amount, unit);
  return createDateValue(newDate);
}

/**
 * Gets the start of a time unit for a date
 * 
 * @param date - The date to process
 * @param unit - The unit to get the start of (year, month, day, hour, minute, second)
 * @returns Date at the start of the specified unit
 */
export function startOf(date: DateInput, unit: OpUnitType): IDateValue {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to startOf');
  }
  
  const newDate = dayjs(date).startOf(unit);
  return createDateValue(newDate);
}

/**
 * Gets the end of a time unit for a date
 * 
 * @param date - The date to process
 * @param unit - The unit to get the end of (year, month, day, hour, minute, second)
 * @returns Date at the end of the specified unit
 */
export function endOf(date: DateInput, unit: OpUnitType): IDateValue {
  if (!isValidDate(date)) {
    throw new Error('Invalid date provided to endOf');
  }
  
  const newDate = dayjs(date).endOf(unit);
  return createDateValue(newDate);
}