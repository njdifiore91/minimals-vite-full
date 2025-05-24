import type { Dayjs, OpUnitType } from 'dayjs';

import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';

// ----------------------------------------------------------------------

/**
 * Configure dayjs plugins for the Email Service
 * - utc: For handling UTC timestamps
 * - timezone: For consistent timezone representation
 * - duration: For calculating time differences
 * - relativeTime: For human-readable time differences
 * - isSameOrBefore/isSameOrAfter: For date comparisons
 */
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(duration);
dayjs.extend(relativeTime);
dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);

// Set default timezone to UTC for consistent server-side processing
dayjs.tz.setDefault('UTC');

// ----------------------------------------------------------------------

/**
 * Type definition for date inputs that can be processed by the formatting functions
 */
export type DateInput = Dayjs | Date | string | number | null | undefined;

/**
 * Email-specific date formats
 */
export const emailDateFormats = {
  /** RFC 2822 format used in email headers */
  rfc2822: 'ddd, DD MMM YYYY HH:mm:ss ZZ',
  /** ISO 8601 format for standardized date exchange */
  iso8601: 'YYYY-MM-DDTHH:mm:ss.SSSZ',
  /** ISO 8601 date only */
  isoDate: 'YYYY-MM-DD',
  /** ISO 8601 time only */
  isoTime: 'HH:mm:ss.SSSZ',
  /** Compact timestamp for logging */
  logTimestamp: 'YYYY-MM-DD HH:mm:ss.SSS',
};

/**
 * Validates if a date input is valid
 * @param date - The date to validate
 * @returns boolean indicating if the date is valid
 */
export const isValidDate = (date: DateInput): boolean =>
  date !== null && date !== undefined && dayjs(date).isValid();

// ----------------------------------------------------------------------

/**
 * Returns the current date and time in ISO 8601 format
 * @returns ISO 8601 formatted current timestamp
 */
export function getCurrentISOTimestamp(): string {
  return dayjs().toISOString();
}

/**
 * Returns the current date and time in RFC 2822 format (email header format)
 * @returns RFC 2822 formatted current timestamp
 */
export function getCurrentRFC2822Timestamp(): string {
  return dayjs().format(emailDateFormats.rfc2822);
}

/**
 * Returns the current date and time in a format suitable for logging
 * @returns Formatted timestamp for logging
 */
export function getLogTimestamp(): string {
  return dayjs().format(emailDateFormats.logTimestamp);
}

// ----------------------------------------------------------------------

/**
 * Formats a date in ISO 8601 format
 * @param date - The date to format
 * @returns ISO 8601 formatted date string or 'Invalid date' if input is invalid
 */
export function formatISO(date: DateInput): string {
  if (!isValidDate(date)) {
    return 'Invalid date';
  }
  return dayjs(date).toISOString();
}

/**
 * Formats a date in RFC 2822 format (used in email headers)
 * @param date - The date to format
 * @returns RFC 2822 formatted date string or 'Invalid date' if input is invalid
 */
export function formatRFC2822(date: DateInput): string {
  if (!isValidDate(date)) {
    return 'Invalid date';
  }
  return dayjs(date).format(emailDateFormats.rfc2822);
}

/**
 * Formats a date with a custom format pattern
 * @param date - The date to format
 * @param format - Optional custom format pattern
 * @returns Formatted date string or 'Invalid date' if input is invalid
 */
export function formatDate(date: DateInput, format?: string): string {
  if (!isValidDate(date)) {
    return 'Invalid date';
  }
  return dayjs(date).format(format || emailDateFormats.isoDate);
}

// ----------------------------------------------------------------------

/**
 * Parses an email header date string (RFC 2822 format)
 * @param dateString - The RFC 2822 date string to parse
 * @returns Dayjs object or null if parsing fails
 */
export function parseEmailHeaderDate(dateString: string): Dayjs | null {
  const parsedDate = dayjs(dateString);
  return parsedDate.isValid() ? parsedDate : null;
}

/**
 * Converts a date to a Unix timestamp (milliseconds since epoch)
 * @param date - The date to convert
 * @returns Unix timestamp in milliseconds or 'Invalid date' if input is invalid
 */
export function toUnixTimestamp(date: DateInput): number | 'Invalid date' {
  if (!isValidDate(date)) {
    return 'Invalid date';
  }
  return dayjs(date).valueOf();
}

// ----------------------------------------------------------------------

/**
 * Calculates the age of a message in milliseconds
 * @param messageDate - The date of the message
 * @returns Age in milliseconds or null if input is invalid
 */
export function calculateMessageAge(messageDate: DateInput): number | null {
  if (!isValidDate(messageDate)) {
    return null;
  }
  return dayjs().diff(dayjs(messageDate));
}

/**
 * Calculates the age of a message in a human-readable format
 * @param messageDate - The date of the message
 * @returns Human-readable age (e.g., "2 hours ago") or null if input is invalid
 */
export function getMessageAgeHumanReadable(messageDate: DateInput): string | null {
  if (!isValidDate(messageDate)) {
    return null;
  }
  return dayjs(messageDate).fromNow();
}

/**
 * Calculates the processing time between two timestamps
 * @param startTime - The start timestamp
 * @param endTime - The end timestamp (defaults to current time if not provided)
 * @returns Processing time in milliseconds or null if input is invalid
 */
export function calculateProcessingTime(
  startTime: DateInput,
  endTime: DateInput = dayjs()
): number | null {
  if (!isValidDate(startTime) || !isValidDate(endTime)) {
    return null;
  }
  return dayjs(endTime).diff(dayjs(startTime));
}

/**
 * Formats a duration in milliseconds to a human-readable string
 * @param milliseconds - Duration in milliseconds
 * @returns Human-readable duration string (e.g., "2.5s" or "150ms")
 */
export function formatDuration(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  }
  return `${(milliseconds / 1000).toFixed(1)}s`;
}

// ----------------------------------------------------------------------

/**
 * Checks if a date is before another date
 * @param date - The date to check
 * @param compareDate - The date to compare against
 * @returns Boolean indicating if date is before compareDate
 */
export function isBefore(date: DateInput, compareDate: DateInput): boolean {
  if (!isValidDate(date) || !isValidDate(compareDate)) {
    return false;
  }
  return dayjs(date).isBefore(dayjs(compareDate));
}

/**
 * Checks if a date is after another date
 * @param date - The date to check
 * @param compareDate - The date to compare against
 * @returns Boolean indicating if date is after compareDate
 */
export function isAfter(date: DateInput, compareDate: DateInput): boolean {
  if (!isValidDate(date) || !isValidDate(compareDate)) {
    return false;
  }
  return dayjs(date).isAfter(dayjs(compareDate));
}

/**
 * Checks if a date is between two other dates (inclusive)
 * @param date - The date to check
 * @param startDate - The start date of the range
 * @param endDate - The end date of the range
 * @returns Boolean indicating if date is between startDate and endDate (inclusive)
 */
export function isBetween(
  date: DateInput,
  startDate: DateInput,
  endDate: DateInput
): boolean {
  if (!isValidDate(date) || !isValidDate(startDate) || !isValidDate(endDate)) {
    return false;
  }
  return (
    dayjs(date).isSameOrAfter(dayjs(startDate)) &&
    dayjs(date).isSameOrBefore(dayjs(endDate))
  );
}

/**
 * Checks if two dates are the same, optionally comparing only specific units
 * @param date1 - First date to compare
 * @param date2 - Second date to compare
 * @param unit - Optional unit to compare (year, month, day, etc.)
 * @returns Boolean indicating if dates are the same
 */
export function isSame(
  date1: DateInput,
  date2: DateInput,
  unit?: OpUnitType
): boolean {
  if (!isValidDate(date1) || !isValidDate(date2)) {
    return false;
  }
  return unit ? dayjs(date1).isSame(dayjs(date2), unit) : dayjs(date1).isSame(dayjs(date2));
}

// ----------------------------------------------------------------------

/**
 * Adds a specified duration to a date
 * @param date - The base date
 * @param amount - The amount to add
 * @param unit - The unit of time to add (days, hours, minutes, etc.)
 * @returns New date with added duration
 */
export function addTime(
  date: DateInput,
  amount: number,
  unit: OpUnitType
): Dayjs | null {
  if (!isValidDate(date)) {
    return null;
  }
  return dayjs(date).add(amount, unit);
}

/**
 * Subtracts a specified duration from a date
 * @param date - The base date
 * @param amount - The amount to subtract
 * @param unit - The unit of time to subtract (days, hours, minutes, etc.)
 * @returns New date with subtracted duration
 */
export function subtractTime(
  date: DateInput,
  amount: number,
  unit: OpUnitType
): Dayjs | null {
  if (!isValidDate(date)) {
    return null;
  }
  return dayjs(date).subtract(amount, unit);
}

// ----------------------------------------------------------------------

/**
 * Converts a date to UTC
 * @param date - The date to convert
 * @returns Date in UTC
 */
export function toUTC(date: DateInput): Dayjs | null {
  if (!isValidDate(date)) {
    return null;
  }
  return dayjs(date).utc();
}

/**
 * Converts a date to a specific timezone
 * @param date - The date to convert
 * @param timezone - The timezone to convert to
 * @returns Date in the specified timezone
 */
export function toTimezone(date: DateInput, timezone: string): Dayjs | null {
  if (!isValidDate(date)) {
    return null;
  }
  return dayjs(date).tz(timezone);
}