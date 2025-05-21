import { Theme } from '@mui/material/styles';

// ----------------------------------------------------------------------

/**
 * Funding-specific component variants for the MCA application
 * 
 * This file defines style overrides for MuiButton and MuiChip components
 * with funding-specific variants that use the funding colors from the theme palette.
 */
export const fundingComponents = {
  MuiButton: {
    variants: [
      {
        props: { variant: 'fundingAction' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.fundingPrimary.main,
          color: theme.palette.fundingPrimary.contrastText,
          boxShadow: theme.customShadows.primary,
          '&:hover': {
            backgroundColor: theme.palette.fundingPrimary.dark,
            boxShadow: 'none',
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
      {
        props: { variant: 'fundingAction', color: 'secondary' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.fundingSecondary.main,
          color: theme.palette.fundingSecondary.contrastText,
          boxShadow: theme.customShadows.secondary,
          '&:hover': {
            backgroundColor: theme.palette.fundingSecondary.dark,
            boxShadow: 'none',
          },
          '&:active': {
            backgroundColor: theme.palette.fundingSecondary.darker,
          },
          '&.Mui-disabled': {
            backgroundColor: theme.palette.action.disabledBackground,
            color: theme.palette.action.disabled,
          },
        }),
      },
      {
        props: { variant: 'fundingAction', color: 'info' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.info.main,
          color: theme.palette.info.contrastText,
          boxShadow: theme.customShadows.info,
          '&:hover': {
            backgroundColor: theme.palette.info.dark,
            boxShadow: 'none',
          },
        }),
      },
      {
        props: { variant: 'fundingOutlined' },
        style: ({ theme }: { theme: Theme }) => ({
          color: theme.palette.fundingPrimary.main,
          borderColor: theme.palette.fundingPrimary.main,
          '&:hover': {
            backgroundColor: theme.palette.fundingPrimary.lighter,
            borderColor: theme.palette.fundingPrimary.main,
          },
        }),
      },
      {
        props: { variant: 'fundingOutlined', color: 'secondary' },
        style: ({ theme }: { theme: Theme }) => ({
          color: theme.palette.fundingSecondary.main,
          borderColor: theme.palette.fundingSecondary.main,
          '&:hover': {
            backgroundColor: theme.palette.fundingSecondary.lighter,
            borderColor: theme.palette.fundingSecondary.main,
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
          '&.MuiChip-filled': {
            backgroundColor: theme.palette.fundingPrimary.main,
            color: theme.palette.fundingPrimary.contrastText,
          },
          '&.MuiChip-outlined': {
            borderColor: theme.palette.fundingPrimary.main,
            color: theme.palette.fundingPrimary.main,
          },
        }),
      },
      {
        props: { variant: 'fundingLabel', color: 'secondary' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.fundingSecondary.lighter,
          color: theme.palette.fundingSecondary.darker,
          '&.MuiChip-filled': {
            backgroundColor: theme.palette.fundingSecondary.main,
            color: theme.palette.fundingSecondary.contrastText,
          },
          '&.MuiChip-outlined': {
            borderColor: theme.palette.fundingSecondary.main,
            color: theme.palette.fundingSecondary.main,
          },
        }),
      },
      {
        props: { variant: 'fundingLabel', color: 'info' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.info.lighter,
          color: theme.palette.info.darker,
          '&.MuiChip-filled': {
            backgroundColor: theme.palette.info.main,
            color: theme.palette.info.contrastText,
          },
          '&.MuiChip-outlined': {
            borderColor: theme.palette.info.main,
            color: theme.palette.info.main,
          },
        }),
      },
      {
        props: { variant: 'fundingLabel', color: 'success' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.success.lighter,
          color: theme.palette.success.darker,
          '&.MuiChip-filled': {
            backgroundColor: theme.palette.success.main,
            color: theme.palette.success.contrastText,
          },
          '&.MuiChip-outlined': {
            borderColor: theme.palette.success.main,
            color: theme.palette.success.main,
          },
        }),
      },
      {
        props: { variant: 'fundingLabel', color: 'warning' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.warning.lighter,
          color: theme.palette.warning.darker,
          '&.MuiChip-filled': {
            backgroundColor: theme.palette.warning.main,
            color: theme.palette.warning.contrastText,
          },
          '&.MuiChip-outlined': {
            borderColor: theme.palette.warning.main,
            color: theme.palette.warning.main,
          },
        }),
      },
      {
        props: { variant: 'fundingLabel', color: 'error' },
        style: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.error.lighter,
          color: theme.palette.error.darker,
          '&.MuiChip-filled': {
            backgroundColor: theme.palette.error.main,
            color: theme.palette.error.contrastText,
          },
          '&.MuiChip-outlined': {
            borderColor: theme.palette.error.main,
            color: theme.palette.error.main,
          },
        }),
      },
    ],
  },
};

// Extend the theme's components with funding-specific variants
export function extendThemeWithFundingComponents(components: any) {
  return {
    ...components,
    ...fundingComponents,
  };
}