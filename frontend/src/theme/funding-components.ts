import { Components, Theme } from '@mui/material/styles';

// ----------------------------------------------------------------------

/**
 * Declare module augmentation for custom component variants
 */
declare module '@mui/material/Button' {
  interface ButtonPropsVariantOverrides {
    fundingAction: true;
  }
}

declare module '@mui/material/Chip' {
  interface ChipPropsVariantOverrides {
    fundingLabel: true;
  }
}

/**
 * Funding-specific component variants for the MCA application
 * 
 * This module defines style overrides for MuiButton (fundingAction variant)
 * and MuiChip (fundingLabel variant) components, using the funding-specific
 * colors from the theme palette.
 */
export const fundingComponents = {
  MuiButton: {
    variants: [
      {
        props: { variant: 'fundingAction' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.fundingPrimary.main,
          color: theme.palette.fundingPrimary.contrastText,
          fontWeight: 600,
          '&:hover': {
            backgroundColor: theme.palette.fundingPrimary.dark,
          },
          '&:active': {
            backgroundColor: theme.palette.fundingPrimary.darker,
          },
          '&.Mui-disabled': {
            backgroundColor: theme.palette.action.disabledBackground,
            color: theme.palette.action.disabled,
          },
        }),
      },
    ],
  },
  MuiChip: {
    variants: [
      {
        props: { variant: 'fundingLabel' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.fundingPrimary.lighter,
          color: theme.palette.fundingPrimary.darker,
          fontWeight: 500,
          '& .MuiChip-icon': {
            color: theme.palette.fundingPrimary.main,
          },
          '& .MuiChip-deleteIcon': {
            color: theme.palette.fundingPrimary.main,
            '&:hover': {
              color: theme.palette.fundingPrimary.dark,
            },
          },
        }),
      },
    ],
  },
};

/**
 * Extends the theme with funding-specific component variants
 * 
 * @param baseComponents - Base components configuration to extend
 * @returns Extended components configuration with funding-specific variants
 */
export function extendThemeWithFundingComponents(baseComponents: Components<Theme> = {}): Components<Theme> {
  return {
    ...baseComponents,
    ...fundingComponents,
  };
}