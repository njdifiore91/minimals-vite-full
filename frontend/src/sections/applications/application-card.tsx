import { useState } from 'react';
import { useTheme } from '@mui/material/styles';

import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';
import { useUpdateApplicationStatus } from 'src/actions/applications';

import { fCurrency } from 'src/utils/format-number';
import { fDate } from 'src/utils/format-time';

import { Label } from 'src/components/label';
import { Iconify } from 'src/components/iconify';

import type { IApplicationItem, IApplicationStatus } from 'src/types/application';

// ----------------------------------------------------------------------

type Props = {
  application: IApplicationItem;
};

/**
 * ApplicationCard Component
 * 
 * Renders an individual Merchant Cash Advance (MCA) application summary card.
 * Displays merchant details, application status, submission date, requested amount,
 * and provides action buttons based on user role permissions.
 * 
 * @param {Props} props - Component props
 * @returns {React.ReactElement} The rendered ApplicationCard component
 */
export default function ApplicationCard({ application }: Props) {
  const theme = useTheme();
  const { updateStatus, isUpdating } = useUpdateApplicationStatus();
  
  // Get application data
  const {
    id,
    status,
    created_at,
    merchant,
    metadata,
  } = application;

  // Get requested amount from metadata
  const requestedAmount = metadata?.requested_amount || 0;

  // Handle status update
  const handleStatusUpdate = async (newStatus: IApplicationStatus) => {
    await updateStatus(id, newStatus);
  };

  // Get status color based on application status
  const getStatusColor = (status: IApplicationStatus) => {
    switch (status) {
      case IApplicationStatus.APPROVED:
        return 'success';
      case IApplicationStatus.REJECTED:
        return 'error';
      case IApplicationStatus.REVIEWING:
        return 'fundingPrimary';
      case IApplicationStatus.INCOMPLETE:
        return 'warning';
      default:
        return 'info';
    }
  };

  return (
    <Card
      sx={{
        p: 3,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <Stack spacing={2} flexGrow={1}>
        {/* Status badge */}
        <Label
          variant="soft"
          color={getStatusColor(status as IApplicationStatus)}
          sx={{ 
            alignSelf: 'flex-start',
            textTransform: 'capitalize',
            px: 2,
            py: 0.75,
            borderRadius: 1,
            fontSize: '0.75rem',
            fontWeight: 'bold',
          }}
        >
          {status}
        </Label>

        {/* Merchant details */}
        <Link
          component={RouterLink}
          href={paths.dashboard.application.details(id)}
          color="inherit"
          variant="subtitle2"
          noWrap
          sx={{ fontWeight: 'bold' }}
        >
          {merchant.legal_name}
        </Link>

        {merchant.dba_name && (
          <Typography variant="body2" sx={{ color: 'text.secondary' }} noWrap>
            DBA: {merchant.dba_name}
          </Typography>
        )}

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ typography: 'body2', color: 'text.secondary' }}
        >
          <Typography variant="body2">EIN: {merchant.ein}</Typography>
          <Typography variant="body2">{merchant.industry}</Typography>
        </Stack>

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ typography: 'body2', color: 'text.secondary' }}
        >
          <Typography variant="body2">Submitted: {fDate(created_at)}</Typography>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
            {fCurrency(requestedAmount)}
          </Typography>
        </Stack>
      </Stack>

      <Divider sx={{ borderStyle: 'dashed', my: 2 }} />

      {/* Action buttons */}
      <Stack direction="row" spacing={2}>
        <Button
          fullWidth
          component={RouterLink}
          href={paths.dashboard.application.details(id)}
          color="fundingPrimary"
          variant="outlined"
          size="small"
          startIcon={<Iconify icon="eva:eye-fill" />}
        >
          View
        </Button>

        {status === IApplicationStatus.PENDING && (
          <Button
            fullWidth
            color="fundingPrimary"
            variant="contained"
            size="small"
            startIcon={<Iconify icon="eva:edit-fill" />}
            onClick={() => handleStatusUpdate(IApplicationStatus.REVIEWING)}
            disabled={isUpdating}
          >
            Process
          </Button>
        )}
      </Stack>
    </Card>
  );
}