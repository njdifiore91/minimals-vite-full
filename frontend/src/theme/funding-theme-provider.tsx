import { ReactNode, useMemo } from 'react';
import type { ThemeProviderProps as MuiThemeProviderProps } from '@mui/material/styles';

import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider as ThemeVarsProvider } from '@mui/material/styles';

import { useTranslate } from 'src/locales';
import { useSettingsContext } from 'src/components/settings';

import { createTheme } from './create-theme';
import { Rtl } from './with-settings/right-to-left';

// Import funding-specific utilities
import { getFundingPalette, FundingSource } from './funding-colors';
import { fundingComponents, extendThemeWithFundingComponents } from './funding-components';

import type {} from './extend-theme-types';
import type { ThemeOptions } from './types';

// ----------------------------------------------------------------------

export type FundingThemeProviderProps = Partial<MuiThemeProviderProps> & {
  fundingSource: FundingSource;
  children: ReactNode;
};

/**
 * FundingThemeProvider - A specialized theme provider that applies funding-specific
 * theming to UI sections based on the provided funding source.
 * 
 * This component wraps UI sections with a theme that includes funding-specific colors
 * and component variants, while maintaining integration with the application's settings
 * and localization systems.
 * 
 * @param {FundingThemeProviderProps} props - Component props including fundingSource and children
 * @returns {JSX.Element} The themed UI section
 */
export function FundingThemeProvider({
  fundingSource,
  children,
  ...other
}: FundingThemeProviderProps) {
  const { currentLang } = useTranslate();
  const settings = useSettingsContext();

  // Get the funding-specific palette based on the provided source
  const fundingPalette = useMemo(() => getFundingPalette(fundingSource), [fundingSource]);

  // Create a theme with funding-specific overrides
  const theme = useMemo(
    () =>
      createTheme({
        settingsState: settings.state,
        localeComponents: currentLang?.systemValue,
        themeOverrides: {
          colorSchemes: {
            light: {
              palette: {
                fundingPrimary: fundingPalette.primary,
                fundingSecondary: fundingPalette.secondary,
              },
            },
            dark: {
              palette: {
                fundingPrimary: fundingPalette.primaryDark,
                fundingSecondary: fundingPalette.secondaryDark,
              },
            },
          },
          // Apply funding-specific component variants
          components: extendThemeWithFundingComponents({}),
          
        },
      }),
    [settings.state, currentLang?.systemValue, fundingPalette]
  );

  return (
    <ThemeVarsProvider disableTransitionOnChange theme={theme} {...other}>
      <CssBaseline />
      <Rtl direction={settings.state.direction!}>{children}</Rtl>
    </ThemeVarsProvider>
  );
}