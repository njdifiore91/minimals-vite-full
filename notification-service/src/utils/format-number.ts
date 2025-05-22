/**
 * Number formatting utilities for the Notification Service
 * 
 * This module provides functions for formatting numbers in various locales and formats
 * for use in notification payloads. It's specifically designed for server-side use in Node.js.
 */

import { config } from '../config';

// Default locale to use when none is specified
const DEFAULT_LOCALE = 'en-US';

// Fallback locales to use if the primary locale is not available
const FALLBACK_LOCALES = ['en-US', 'en'];

/**
 * Available locales in the current Node.js environment
 * Note: Node.js may have limited locale data depending on how it was built
 */
const getAvailableLocales = (): string[] => {
  try {
    return Intl.NumberFormat.supportedLocalesOf(Intl.NumberFormat().resolvedOptions().locale);
  } catch (error) {
    console.warn('Error getting available locales:', error);
    return ['en-US']; // Fallback to US English if there's an error
  }
};

/**
 * Checks if a locale is supported in the current environment
 * @param locale - The locale to check
 * @returns Whether the locale is supported
 */
const isLocaleSupported = (locale: string): boolean => {
  try {
    return Intl.NumberFormat.supportedLocalesOf([locale]).length > 0;
  } catch (error) {
    return false;
  }
};

/**
 * Gets the best supported locale from a list of preferred locales
 * @param preferredLocales - List of preferred locales in order of preference
 * @returns The best supported locale
 */
const getBestSupportedLocale = (preferredLocales: string[]): string => {
  // Try each preferred locale
  for (const locale of preferredLocales) {
    if (isLocaleSupported(locale)) {
      return locale;
    }
  }
  
  // If none of the preferred locales are supported, try the fallbacks
  for (const locale of FALLBACK_LOCALES) {
    if (isLocaleSupported(locale)) {
      return locale;
    }
  }
  
  // If all else fails, return the default locale and hope for the best
  return DEFAULT_LOCALE;
};

/**
 * Formats a number according to the specified locale and options
 * @param value - The number to format
 * @param locale - The locale to use for formatting
 * @param options - Formatting options
 * @returns The formatted number string
 */
export const formatNumber = (value: number, locale?: string, options?: Intl.NumberFormatOptions): string => {
  if (value === null || value === undefined || isNaN(value)) {
    return '';
  }
  
  try {
    // Use the provided locale, or get it from config, or use the default
    const localeToUse = locale || config.defaultLocale || DEFAULT_LOCALE;
    
    // Get the best supported locale
    const bestLocale = getBestSupportedLocale([localeToUse]);
    
    // Create the formatter and format the number
    const formatter = new Intl.NumberFormat(bestLocale, options);
    return formatter.format(value);
  } catch (error) {
    console.error('Error formatting number:', error);
    // Fallback to basic formatting if Intl fails
    return value.toString();
  }
};

/**
 * Formats a number as currency according to the specified locale and currency
 * @param value - The number to format
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use for formatting
 * @param options - Additional formatting options
 * @returns The formatted currency string
 */
export const formatCurrency = (
  value: number,
  currency: string,
  locale?: string,
  options?: Omit<Intl.NumberFormatOptions, 'style' | 'currency'>
): string => {
  return formatNumber(value, locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    ...options,
  });
};

/**
 * Formats a number as a percentage according to the specified locale
 * @param value - The number to format (e.g., 0.25 for 25%)
 * @param locale - The locale to use for formatting
 * @param options - Additional formatting options
 * @returns The formatted percentage string
 */
export const formatPercent = (
  value: number,
  locale?: string,
  options?: Omit<Intl.NumberFormatOptions, 'style'>
): string => {
  return formatNumber(value, locale, {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
    ...options,
  });
};

/**
 * Formats a currency amount for webhook payloads
 * This ensures consistent formatting across all webhook notifications
 * 
 * @param value - The number to format
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use for formatting
 * @returns The formatted currency string
 */
export const formatWebhookCurrency = (
  value: number,
  currency: string,
  locale?: string
): string => {
  return formatCurrency(value, currency, locale, {
    currencyDisplay: 'symbol',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

/**
 * Formats a number for webhook payloads without currency symbol
 * Useful when the currency symbol is displayed separately
 * 
 * @param value - The number to format
 * @param locale - The locale to use for formatting
 * @returns The formatted number string
 */
export const formatWebhookAmount = (
  value: number,
  locale?: string
): string => {
  return formatNumber(value, locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

/**
 * Formats a number as a compact notation (e.g., 1.2K, 5.3M)
 * Useful for displaying large numbers in notifications
 * 
 * @param value - The number to format
 * @param locale - The locale to use for formatting
 * @returns The formatted compact number string
 */
export const formatCompactNumber = (
  value: number,
  locale?: string
): string => {
  return formatNumber(value, locale, {
    notation: 'compact',
    compactDisplay: 'short',
  });
};

/**
 * Formats a number with a specific number of decimal places
 * @param value - The number to format
 * @param decimalPlaces - The number of decimal places to include
 * @param locale - The locale to use for formatting
 * @returns The formatted number string
 */
export const formatDecimal = (
  value: number,
  decimalPlaces: number,
  locale?: string
): string => {
  return formatNumber(value, locale, {
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  });
};

/**
 * Formats a number for display in a specific locale without any additional formatting
 * @param value - The number to format
 * @param locale - The locale to use for formatting
 * @returns The formatted number string
 */
export const formatPlainNumber = (value: number, locale?: string): string => {
  return formatNumber(value, locale);
};

/**
 * Extracts just the numeric part from a formatted currency string
 * Useful when you need to display the currency symbol separately
 * 
 * @param formattedCurrency - The formatted currency string
 * @returns The numeric part of the currency string
 */
export const extractNumericValue = (formattedCurrency: string): string => {
  // Remove all non-numeric characters except decimal separator and digits
  // This is a simplified approach and may need adjustment for some locales
  return formattedCurrency.replace(/[^\d.,]/g, '');
};

/**
 * Formats a number for international notifications based on recipient's locale
 * @param value - The number to format
 * @param recipientLocale - The recipient's locale
 * @param options - Formatting options
 * @returns The formatted number string
 */
export const formatInternationalNumber = (
  value: number,
  recipientLocale: string,
  options?: Intl.NumberFormatOptions
): string => {
  // Try the recipient's locale first, then fall back to defaults
  const bestLocale = getBestSupportedLocale([recipientLocale]);
  return formatNumber(value, bestLocale, options);
};