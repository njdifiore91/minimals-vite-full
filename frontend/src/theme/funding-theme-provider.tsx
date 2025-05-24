import type { ReactNode } from 'react';
import type { ThemeProviderProps as MuiThemeProviderProps } from '@mui/material/styles';

import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider as ThemeVarsProvider } from '@mui/material/styles';

import { useTranslate } from 'src/locales';
import { useSettingsContext } from 'src/components/settings';

import { createTheme } from './create-theme';
import { Rtl } from './with-settings/right-to-left';
import { getFundingPalette, FundingSource } from './funding-colors';
import { extendThemeWithFundingComponents } from './funding-components';

import type {} from './extend-theme-types';
import type { ThemeOptions } from './types';

// Declare module augmentation for funding-specific palette entries
declare module '@mui/material/styles' {
  interface Palette {
    fundingPrimary: Palette['primary'];
    fundingSecondary: Palette['secondary'];
    fundingAccent?: Palette['info'];
  }
  
  interface PaletteOptions {
    fundingPrimary?: PaletteOptions['primary'];
    fundingSecondary?: PaletteOptions['secondary'];
    fundingAccent?: PaletteOptions['info'];
  }
}

// ----------------------------------------------------------------------

/**
 * Props for the FundingThemeProvider component
 */
export type FundingThemeProviderProps = Partial<MuiThemeProviderProps> & {
  /**
   * The funding source to use for theming ('alpha', 'beta', 'gamma', or 'default')
   */
  fundingSource?: FundingSource;
  
  /**
   * Additional theme overrides to apply
   */
  themeOverrides?: ThemeOptions;
  
  /**
   * Children to render within the theme provider
   */
  children: ReactNode;
};

/**
 * A theme provider that applies funding-specific theming to UI sections
 * 
 * This component wraps UI sections with funding-specific theming based on the
 * provided fundingSource parameter. It integrates with the application's settings
 * and localization systems to ensure consistent theming across the application.
 * 
 * @example
 * ```tsx
 * <FundingThemeProvider fundingSource="alpha">
 *   <ApplicationCard />
 * </FundingThemeProvider>
 * ```
 */
export function FundingThemeProvider({
  fundingSource = 'default',
  themeOverrides,
  children,
  ...other
}: FundingThemeProviderProps) {
  const { currentLang } = useTranslate();
  const settings = useSettingsContext();

  // Get funding-specific palette based on source
  const fundingPalette = getFundingPalette(fundingSource);

  // Create theme with funding-specific overrides
  const theme = createTheme({
    settingsState: settings.state,
    localeComponents: currentLang?.systemValue,
    themeOverrides: {
      ...themeOverrides,
      // Add funding-specific palette entries
      colorSchemes: {
        light: {
          palette: {
            fundingPrimary: {
              main: fundingPalette.fundingPrimary,
              light: fundingPalette.fundingPrimary + '99', // 60% opacity
              dark: fundingPalette.fundingPrimary + 'CC',  // 80% opacity
              darker: fundingPalette.fundingPrimary,       // 100% opacity
              lighter: fundingPalette.fundingPrimary + '33', // 20% opacity
              contrastText: '#FFFFFF',
            },
            fundingSecondary: {
              main: fundingPalette.fundingSecondary,
              light: fundingPalette.fundingSecondary + '99', // 60% opacity
              dark: fundingPalette.fundingSecondary + 'CC',  // 80% opacity
              darker: fundingPalette.fundingSecondary,       // 100% opacity
              lighter: fundingPalette.fundingSecondary + '33', // 20% opacity
              contrastText: '#FFFFFF',
            },
            ...(fundingPalette.fundingAccent && {
              fundingAccent: {
                main: fundingPalette.fundingAccent,
                light: fundingPalette.fundingAccent + '99', // 60% opacity
                dark: fundingPalette.fundingAccent + 'CC',  // 80% opacity
                darker: fundingPalette.fundingAccent,       // 100% opacity
                lighter: fundingPalette.fundingAccent + '33', // 20% opacity
                contrastText: '#FFFFFF',
              },
            }),
          },
        },
        dark: {
          palette: {
            fundingPrimary: {
              main: fundingPalette.fundingPrimary,
              light: fundingPalette.fundingPrimary + '99', // 60% opacity
              dark: fundingPalette.fundingPrimary + 'CC',  // 80% opacity
              darker: fundingPalette.fundingPrimary,       // 100% opacity
              lighter: fundingPalette.fundingPrimary + '33', // 20% opacity
              contrastText: '#FFFFFF',
            },
            fundingSecondary: {
              main: fundingPalette.fundingSecondary,
              light: fundingPalette.fundingSecondary + '99', // 60% opacity
              dark: fundingPalette.fundingSecondary + 'CC',  // 80% opacity
              darker: fundingPalette.fundingSecondary,       // 100% opacity
              lighter: fundingPalette.fundingSecondary + '33', // 20% opacity
              contrastText: '#FFFFFF',
            },
            ...(fundingPalette.fundingAccent && {
              fundingAccent: {
                main: fundingPalette.fundingAccent,
                light: fundingPalette.fundingAccent + '99', // 60% opacity
                dark: fundingPalette.fundingAccent + 'CC',  // 80% opacity
                darker: fundingPalette.fundingAccent,       // 100% opacity
                lighter: fundingPalette.fundingAccent + '33', // 20% opacity
                contrastText: '#FFFFFF',
              },
            }),
          },
        },
      },
      // Add funding-specific component variants
      components: extendThemeWithFundingComponents(),
    },
  });

  return (
    <ThemeVarsProvider disableTransitionOnChange theme={theme} {...other}>
      <CssBaseline />
      <Rtl direction={settings.state.direction!}>{children}</Rtl>
    </ThemeVarsProvider>
  );
}