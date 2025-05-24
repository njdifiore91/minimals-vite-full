import { Components, Theme } from '@mui/material/styles';

/**
 * Funding-specific component variants for the MCA application
 * These component overrides use the funding-specific colors from the theme palette
 */
export const fundingComponents = {
  MuiButton: {
    variants: [
      {
        props: { variant: 'fundingAction' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.fundingPrimary,
          color: theme.palette.common.white,
          fontWeight: 600,
          boxShadow: theme.shadows[2],
          '&:hover': {
            backgroundColor: theme.palette.fundingSecondary,
            boxShadow: theme.shadows[4],
          },
          '&:active': {
            boxShadow: theme.shadows[1],
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
          backgroundColor: theme.palette.fundingPrimary,
          color: theme.palette.common.white,
          fontWeight: 500,
          '&.MuiChip-filled': {
            '&:hover': {
              backgroundColor: theme.palette.fundingPrimary,
              opacity: 0.9,
            },
          },
        }),
      },
    ],
  },
} as Components<Omit<Theme, 'components'>>;