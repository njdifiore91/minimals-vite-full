import type { PaletteColor } from '@mui/material/styles';

// ----------------------------------------------------------------------

/**
 * TypeScript interfaces for funding color palettes
 */
export interface FundingColorPalette {
  fundingPrimary: string;
  fundingSecondary: string;
  fundingAccent?: string;
  fundingNeutral?: string;
  fundingSuccess?: string;
  fundingWarning?: string;
  fundingError?: string;
}

export type FundingSource = 'alpha' | 'beta' | 'gamma' | 'default';

// ----------------------------------------------------------------------

/**
 * Color palettes for different funding sources
 */
export const alphaFundingPalette: FundingColorPalette = {
  fundingPrimary: '#0052CC',   // Blue
  fundingSecondary: '#00875A',  // Green
  fundingAccent: '#6554C0',     // Purple
  fundingNeutral: '#505F79',    // Slate
  fundingSuccess: '#36B37E',    // Green
  fundingWarning: '#FFAB00',    // Yellow
  fundingError: '#FF5630',      // Red
};

export const betaFundingPalette: FundingColorPalette = {
  fundingPrimary: '#6E44FF',   // Purple
  fundingSecondary: '#FF5630',  // Red
  fundingAccent: '#00B8D9',     // Cyan
  fundingNeutral: '#42526E',    // Navy
  fundingSuccess: '#36B37E',    // Green
  fundingWarning: '#FFAB00',    // Yellow
  fundingError: '#FF5630',      // Red
};

export const gammaFundingPalette: FundingColorPalette = {
  fundingPrimary: '#006644',   // Dark Green
  fundingSecondary: '#DE350B',  // Red
  fundingAccent: '#0065FF',     // Blue
  fundingNeutral: '#253858',    // Dark Navy
  fundingSuccess: '#00875A',    // Green
  fundingWarning: '#FF8B00',    // Orange
  fundingError: '#DE350B',      // Red
};

export const defaultFundingPalette: FundingColorPalette = {
  fundingPrimary: '#00A76F',   // Default primary from theme
  fundingSecondary: '#8E33FF',  // Default secondary from theme
  fundingAccent: '#00B8D9',     // Default info from theme
  fundingNeutral: '#637381',    // Default grey[600] from theme
  fundingSuccess: '#22C55E',    // Default success from theme
  fundingWarning: '#FFAB00',    // Default warning from theme
  fundingError: '#FF5630',      // Default error from theme
};

// ----------------------------------------------------------------------

/**
 * Returns the appropriate funding color palette based on the provided source
 * @param source - The funding source ('alpha', 'beta', 'gamma', or 'default')
 * @returns The corresponding funding color palette
 */
export function getFundingPalette(source: FundingSource = 'default'): FundingColorPalette {
  switch (source) {
    case 'alpha':
      return alphaFundingPalette;
    case 'beta':
      return betaFundingPalette;
    case 'gamma':
      return gammaFundingPalette;
    default:
      return defaultFundingPalette;
  }
}

// ----------------------------------------------------------------------

/**
 * Maps funding source names to their respective color palettes
 */
export const fundingColorPresets: Record<FundingSource, FundingColorPalette> = {
  alpha: alphaFundingPalette,
  beta: betaFundingPalette,
  gamma: gammaFundingPalette,
  default: defaultFundingPalette,
};