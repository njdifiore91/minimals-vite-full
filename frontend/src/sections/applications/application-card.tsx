import type { IApplicationItem, IApplicationStatus } from 'src/types/application';
import type { CardProps } from '@mui/material/Card';

import { useState } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';

import { useRouter } from 'src/routes/hooks';
import { paths } from 'src/routes/paths';

import { fCurrency } from 'src/utils/format-number';
import { fDate } from 'src/utils/format-time';

import { Label } from 'src/components/label';
import { Iconify } from 'src/components/iconify';

// ----------------------------------------------------------------------

type Props = CardProps & {
  application: IApplicationItem;
  userRole?: 'operations_staff' | 'system_admin';
};

export function ApplicationCard({ application, userRole = 'operations_staff', sx, ...other }: Props) {
  const router = useRouter();
  
  const { id, status, created_at, merchant, metadata } = application;
  
  const requestedAmount = metadata?.requested_amount || 0;

  const handleViewDetails = () => {
    router.push(paths.dashboard.applications.details(id));
  };

  const handleProcessApplication = () => {
    router.push(paths.dashboard.applications.process(id));
  };

  const renderStatus = () => (
    <Label
      variant="filled"
      color={
        (status === IApplicationStatus.APPROVED && 'success') ||
        (status === IApplicationStatus.REJECTED && 'error') ||
        (status === IApplicationStatus.REVIEWING && 'warning') ||
        (status === IApplicationStatus.INCOMPLETE && 'error') ||
        'info'
      }
      sx={{
        textTransform: 'uppercase',
        fontSize: '0.75rem',
        fontWeight: 'bold',
        ...(status === IApplicationStatus.APPROVED && {
          bgcolor: (theme) => theme.palette.fundingSuccess || theme.palette.success.main,
        }),
        ...(status === IApplicationStatus.REJECTED && {
          bgcolor: (theme) => theme.palette.fundingError || theme.palette.error.main,
        }),
        ...(status === IApplicationStatus.REVIEWING && {
          bgcolor: (theme) => theme.palette.fundingWarning || theme.palette.warning.main,
        }),
        ...(status === IApplicationStatus.INCOMPLETE && {
          bgcolor: (theme) => theme.palette.fundingError || theme.palette.error.main,
        }),
        ...(status === IApplicationStatus.PENDING && {
          bgcolor: (theme) => theme.palette.fundingPrimary || theme.palette.info.main,
        }),
      }}
    >
      {status}
    </Label>
  );

  const renderMerchantInfo = () => (
    <Stack spacing={0.5}>
      <Typography variant="subtitle1" noWrap>
        {merchant.legal_name}
      </Typography>
      
      {merchant.dba_name && (
        <Typography variant="body2" sx={{ color: 'text.secondary' }} noWrap>
          DBA: {merchant.dba_name}
        </Typography>
      )}
      
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
        EIN: {merchant.ein}
      </Typography>
    </Stack>
  );

  const renderMetadata = () => (
    <Stack
      direction="row"
      flexWrap="wrap"
      alignItems="center"
      justifyContent="space-between"
      sx={{ mt: 3, mb: 1 }}
    >
      <Stack direction="row" spacing={1} alignItems="center">
        <Iconify icon="solar:calendar-date-bold" width={16} />
        <Typography variant="caption" sx={{ color: 'text.disabled' }}>
          Submitted: {fDate(created_at)}
        </Typography>
      </Stack>

      <Stack direction="row" spacing={1} alignItems="center">
        <Iconify icon="solar:dollar-bold" width={16} />
        <Typography variant="subtitle1">
          {fCurrency(requestedAmount)}
        </Typography>
      </Stack>
    </Stack>
  );

  const renderActions = () => (
    <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
      <Button
        fullWidth
        size="small"
        color="inherit"
        variant="outlined"
        onClick={handleViewDetails}
        startIcon={<Iconify icon="solar:eye-bold" />}
      >
        View
      </Button>

      {(status === IApplicationStatus.PENDING || status === IApplicationStatus.REVIEWING) && (
        <Button
          fullWidth
          size="small"
          variant="contained"
          onClick={handleProcessApplication}
          startIcon={<Iconify icon="solar:file-check-bold" />}
          sx={{
            bgcolor: (theme) => theme.palette.fundingPrimary || theme.palette.primary.main,
            '&:hover': {
              bgcolor: (theme) => theme.palette.fundingSecondary || theme.palette.primary.dark,
            },
          }}
        >
          Process
        </Button>
      )}
    </Stack>
  );

  return (
    <Card
      sx={{
        p: 3,
        width: 1,
        boxShadow: (theme) => theme.customShadows?.z8,
        ...(Array.isArray(sx) ? sx : [sx]),
      }}
      {...other}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
        <Box sx={{ flexGrow: 1 }}>
          {renderMerchantInfo()}
        </Box>

        <Box>
          {renderStatus()}
        </Box>
      </Stack>

      <Divider sx={{ borderStyle: 'dashed', my: 2 }} />

      {renderMetadata()}

      {userRole && renderActions()}
    </Card>
  );
}