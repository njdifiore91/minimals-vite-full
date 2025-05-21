import { alpha } from '@mui/material/styles';

// ----------------------------------------------------------------------

/**
 * Available funding sources for theming
 */
export type FundingSource = 'alpha' | 'beta' | 'gamma' | 'default';

/**
 * Structure of a funding color palette
 */
export interface FundingColorPalette {
  primary: {
    lighter: string;
    light: string;
    main: string;
    dark: string;
    darker: string;
    contrastText: string;
  };
  secondary: {
    lighter: string;
    light: string;
    main: string;
    dark: string;
    darker: string;
    contrastText: string;
  };
  primaryDark: {
    lighter: string;
    light: string;
    main: string;
    dark: string;
    darker: string;
    contrastText: string;
  };
  secondaryDark: {
    lighter: string;
    light: string;
    main: string;
    dark: string;
    darker: string;
    contrastText: string;
  };
}

/**
 * Default funding color palette
 */
const defaultFundingPalette: FundingColorPalette = {
  primary: {
    lighter: '#D1E9FC',
    light: '#76B0F1',
    main: '#0052CC',
    dark: '#103996',
    darker: '#061B64',
    contrastText: '#FFFFFF',
  },
  secondary: {
    lighter: '#C8FAD6',
    light: '#5BE49B',
    main: '#00875A',
    dark: '#007B55',
    darker: '#005249',
    contrastText: '#FFFFFF',
  },
  primaryDark: {
    lighter: '#424C80',
    light: '#2A3875',
    main: '#0052CC',
    dark: '#0046B0',
    darker: '#003994',
    contrastText: '#FFFFFF',
  },
  secondaryDark: {
    lighter: '#2A6D5A',
    light: '#1A6150',
    main: '#00875A',
    dark: '#007B55',
    darker: '#006F4C',
    contrastText: '#FFFFFF',
  },
};

/**
 * Alpha funding source color palette
 */
const alphaFundingPalette: FundingColorPalette = {
  primary: {
    lighter: '#D0F2FF',
    light: '#74CAFF',
    main: '#1890FF',
    dark: '#0C53B7',
    darker: '#04297A',
    contrastText: '#FFFFFF',
  },
  secondary: {
    lighter: '#D6E4FF',
    light: '#84A9FF',
    main: '#3366FF',
    dark: '#1939B7',
    darker: '#091A7A',
    contrastText: '#FFFFFF',
  },
  primaryDark: {
    lighter: '#3D5CFF',
    light: '#304BDF',
    main: '#1890FF',
    dark: '#0C53B7',
    darker: '#04297A',
    contrastText: '#FFFFFF',
  },
  secondaryDark: {
    lighter: '#4D69FF',
    light: '#3A56DF',
    main: '#3366FF',
    dark: '#1939B7',
    darker: '#091A7A',
    contrastText: '#FFFFFF',
  },
};

/**
 * Beta funding source color palette
 */
const betaFundingPalette: FundingColorPalette = {
  primary: {
    lighter: '#FFF7CD',
    light: '#FFE16A',
    main: '#FFC107',
    dark: '#B78103',
    darker: '#7A4F01',
    contrastText: '#212B36',
  },
  secondary: {
    lighter: '#FFE9D5',
    light: '#FFAC82',
    main: '#FF5630',
    dark: '#B71D18',
    darker: '#7A0916',
    contrastText: '#FFFFFF',
  },
  primaryDark: {
    lighter: '#B78103',
    light: '#A77700',
    main: '#FFC107',
    dark: '#E8B000',
    darker: '#DBA700',
    contrastText: '#212B36',
  },
  secondaryDark: {
    lighter: '#B71D18',
    light: '#A01A16',
    main: '#FF5630',
    dark: '#E84C2A',
    darker: '#DB4726',
    contrastText: '#FFFFFF',
  },
};

/**
 * Gamma funding source color palette
 */
const gammaFundingPalette: FundingColorPalette = {
  primary: {
    lighter: '#E9FCD4',
    light: '#AAF27F',
    main: '#54D62C',
    dark: '#229A16',
    darker: '#08660D',
    contrastText: '#FFFFFF',
  },
  secondary: {
    lighter: '#FEE9D1',
    light: '#FDAB76',
    main: '#FA541C',
    dark: '#B3200E',
    darker: '#770508',
    contrastText: '#FFFFFF',
  },
  primaryDark: {
    lighter: '#229A16',
    light: '#1B8A13',
    main: '#54D62C',
    dark: '#4CC726',
    darker: '#45B721',
    contrastText: '#FFFFFF',
  },
  secondaryDark: {
    lighter: '#B3200E',
    light: '#A01D0C',
    main: '#FA541C',
    dark: '#E54B19',
    darker: '#DB4617',
    contrastText: '#FFFFFF',
  },
};

/**
 * Mapping of funding sources to their respective color palettes
 */
export const fundingColorPresets: Record<FundingSource, FundingColorPalette> = {
  default: defaultFundingPalette,
  alpha: alphaFundingPalette,
  beta: betaFundingPalette,
  gamma: gammaFundingPalette,
};

/**
 * Returns the funding color palette for the specified funding source
 * @param source The funding source to get colors for
 * @returns The funding color palette
 */
export function getFundingPalette(source: FundingSource = 'default'): FundingColorPalette {
  return fundingColorPresets[source];
}