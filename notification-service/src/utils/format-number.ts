/**
 * Number Formatting Utilities for Notification Service
 *
 * This file provides utility functions for formatting numbers in different locales and formats
 * for use in notification payloads. It supports currency formatting, percentage formatting,
 * and plain number formatting with configurable options.
 *
 * Key features:
 * - Locale-aware number formatting for international notifications
 * - Currency formatting with configurable options
 * - Percentage formatting
 * - Configurable decimal places and grouping
 * - Support for accounting format for negative numbers
 */

import { config } from '../config';

/**
 * Available number format styles
 */
export enum NumberFormatStyle {
  DECIMAL = 'decimal',
  CURRENCY = 'currency',
  PERCENT = 'percent',
  UNIT = 'unit'
}

/**
 * Available currency display options
 */
export enum CurrencyDisplay {
  SYMBOL = 'symbol',       // $
  CODE = 'code',           // USD
  NAME = 'name',           // US Dollar
  NARROW_SYMBOL = 'narrowSymbol' // Narrow version of the symbol
}

/**
 * Available currency sign options
 */
export enum CurrencySign {
  STANDARD = 'standard',   // -$10
  ACCOUNTING = 'accounting' // ($10)
}

/**
 * Number formatting options
 */
export interface FormatNumberOptions {
  locale?: string;
  style?: NumberFormatStyle;
  currency?: string;
  currencyDisplay?: CurrencyDisplay;
  currencySign?: CurrencySign;
  minimumFractionDigits?: number;
  maximumFractionDigits?: number;
  minimumIntegerDigits?: number;
  minimumSignificantDigits?: number;
  maximumSignificantDigits?: number;
  useGrouping?: boolean;
  notation?: 'standard' | 'scientific' | 'engineering' | 'compact';
  compactDisplay?: 'short' | 'long';
}

/**
 * Default locale for number formatting
 * Uses the configured locale from environment variables or falls back to 'en-US'
 */
export const DEFAULT_LOCALE = config.app.defaultLocale || 'en-US';

/**
 * Default currency for formatting
 * Uses the configured currency from environment variables or falls back to 'USD'
 */
export const DEFAULT_CURRENCY = config.app.defaultCurrency || 'USD';

/**
 * Default number of decimal places for currency formatting
 */
export const DEFAULT_CURRENCY_FRACTION_DIGITS = 2;

/**
 * Default number of decimal places for number formatting
 */
export const DEFAULT_NUMBER_FRACTION_DIGITS = 2;

/**
 * Formats a number according to the specified locale and options
 *
 * @param value - The number to format
 * @param options - Formatting options
 * @returns The formatted number as a string
 */
export function formatNumber(value: number, options: FormatNumberOptions = {}): string {
  const {
    locale = DEFAULT_LOCALE,
    style = NumberFormatStyle.DECIMAL,
    currency = DEFAULT_CURRENCY,
    currencyDisplay = CurrencyDisplay.SYMBOL,
    currencySign = CurrencySign.STANDARD,
    minimumFractionDigits,
    maximumFractionDigits = style === NumberFormatStyle.CURRENCY ? DEFAULT_CURRENCY_FRACTION_DIGITS : DEFAULT_NUMBER_FRACTION_DIGITS,
    minimumIntegerDigits,
    minimumSignificantDigits,
    maximumSignificantDigits,
    useGrouping = true,
    notation = 'standard',
    compactDisplay = 'short'
  } = options;

  // Create formatter with specified options
  const formatter = new Intl.NumberFormat(locale, {
    style,
    ...(style === NumberFormatStyle.CURRENCY && { currency, currencyDisplay, currencySign }),
    minimumFractionDigits,
    maximumFractionDigits,
    minimumIntegerDigits,
    minimumSignificantDigits,
    maximumSignificantDigits,
    useGrouping,
    notation,
    compactDisplay
  });

  return formatter.format(value);
}

/**
 * Formats a number as currency
 *
 * @param value - The number to format as currency
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use for formatting
 * @param options - Additional formatting options
 * @returns The formatted currency as a string
 */
export function formatCurrency(
  value: number,
  currency: string = DEFAULT_CURRENCY,
  locale: string = DEFAULT_LOCALE,
  options: Omit<FormatNumberOptions, 'style' | 'currency' | 'locale'> = {}
): string {
  return formatNumber(value, {
    style: NumberFormatStyle.CURRENCY,
    currency,
    locale,
    ...options
  });
}

/**
 * Formats a number as currency for webhook payloads
 * This is optimized for machine-readable formats in webhook payloads
 *
 * @param value - The number to format as currency
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use for formatting
 * @returns The formatted currency as a string
 */
export function formatCurrencyForWebhook(
  value: number,
  currency: string = DEFAULT_CURRENCY,
  locale: string = DEFAULT_LOCALE
): string {
  return formatNumber(value, {
    style: NumberFormatStyle.CURRENCY,
    currency,
    locale,
    currencyDisplay: CurrencyDisplay.CODE,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

/**
 * Formats a number as currency without the currency symbol
 * Useful for tables or lists where the currency is shown in a header
 *
 * @param value - The number to format
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use for formatting
 * @returns The formatted number as a string without currency symbol
 */
export function formatCurrencyWithoutSymbol(
  value: number,
  currency: string = DEFAULT_CURRENCY,
  locale: string = DEFAULT_LOCALE
): string {
  // Use formatToParts to get individual parts of the formatted number
  const parts = new Intl.NumberFormat(locale, {
    style: NumberFormatStyle.CURRENCY,
    currency,
    currencyDisplay: CurrencyDisplay.CODE
  }).formatToParts(value);

  // Filter out the currency part and any whitespace literals
  return parts
    .filter(part => part.type !== 'currency')
    .filter(part => part.type !== 'literal' || part.value.trim().length !== 0)
    .map(part => part.value)
    .join('');
}

/**
 * Formats a number as a percentage
 *
 * @param value - The number to format as percentage (0.1 = 10%)
 * @param locale - The locale to use for formatting
 * @param fractionDigits - The number of decimal places to show
 * @returns The formatted percentage as a string
 */
export function formatPercent(
  value: number,
  locale: string = DEFAULT_LOCALE,
  fractionDigits: number = 1
): string {
  return formatNumber(value, {
    style: NumberFormatStyle.PERCENT,
    locale,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  });
}

/**
 * Formats a number with thousands separators
 *
 * @param value - The number to format
 * @param locale - The locale to use for formatting
 * @param fractionDigits - The number of decimal places to show
 * @returns The formatted number as a string
 */
export function formatWithThousandsSeparator(
  value: number,
  locale: string = DEFAULT_LOCALE,
  fractionDigits: number = DEFAULT_NUMBER_FRACTION_DIGITS
): string {
  return formatNumber(value, {
    locale,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    useGrouping: true
  });
}

/**
 * Formats a number for display in a compact form
 * (e.g., 1.2K, 1.2M, etc.)
 *
 * @param value - The number to format
 * @param locale - The locale to use for formatting
 * @param fractionDigits - The number of decimal places to show
 * @returns The formatted number as a string in compact form
 */
export function formatCompact(
  value: number,
  locale: string = DEFAULT_LOCALE,
  fractionDigits: number = 1
): string {
  return formatNumber(value, {
    locale,
    notation: 'compact',
    compactDisplay: 'short',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  });
}

/**
 * Formats a number for accounting purposes
 * Uses parentheses for negative numbers instead of minus sign
 *
 * @param value - The number to format
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use for formatting
 * @returns The formatted number as a string with accounting format
 */
export function formatAccountingCurrency(
  value: number,
  currency: string = DEFAULT_CURRENCY,
  locale: string = DEFAULT_LOCALE
): string {
  return formatNumber(value, {
    style: NumberFormatStyle.CURRENCY,
    currency,
    locale,
    currencySign: CurrencySign.ACCOUNTING
  });
}

/**
 * Formats a number with a specific unit
 * (e.g., 100 kg, 200 lb, etc.)
 *
 * @param value - The number to format
 * @param unit - The unit to use (e.g., 'kilogram', 'pound', etc.)
 * @param locale - The locale to use for formatting
 * @param fractionDigits - The number of decimal places to show
 * @returns The formatted number with unit as a string
 */
export function formatWithUnit(
  value: number,
  unit: string,
  locale: string = DEFAULT_LOCALE,
  fractionDigits: number = DEFAULT_NUMBER_FRACTION_DIGITS
): string {
  return formatNumber(value, {
    style: NumberFormatStyle.UNIT,
    unit,
    locale,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  });
}

/**
 * Gets the currency symbol for a specific currency and locale
 *
 * @param currency - The currency code (e.g., 'USD', 'EUR')
 * @param locale - The locale to use
 * @returns The currency symbol as a string
 */
export function getCurrencySymbol(currency: string = DEFAULT_CURRENCY, locale: string = DEFAULT_LOCALE): string {
  const formatter = new Intl.NumberFormat(locale, {
    style: NumberFormatStyle.CURRENCY,
    currency,
    currencyDisplay: CurrencyDisplay.SYMBOL
  });
  
  const parts = formatter.formatToParts(0);
  const currencyPart = parts.find(part => part.type === 'currency');
  
  return currencyPart ? currencyPart.value : currency;
}

/**
 * Parses a localized number string back to a number
 *
 * @param value - The localized number string to parse
 * @param locale - The locale of the string
 * @returns The parsed number or NaN if parsing fails
 */
export function parseLocaleNumber(value: string, locale: string = DEFAULT_LOCALE): number {
  // Get the decimal and group separators for the locale
  const formatter = new Intl.NumberFormat(locale);
  const parts = formatter.formatToParts(1234.5);
  const decimalSeparator = parts.find(part => part.type === 'decimal')?.value || '.';
  const groupSeparator = parts.find(part => part.type === 'group')?.value || ',';
  
  // Replace the locale-specific separators with standard ones
  const normalized = value
    .replace(new RegExp(`\\${groupSeparator}`, 'g'), '')
    .replace(new RegExp(`\\${decimalSeparator}`), '.');
  
  // Parse the normalized string
  return parseFloat(normalized);
}