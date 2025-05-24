import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// mui
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';

// components
import { Label } from 'src/components/label';
import { Iconify } from 'src/components/iconify';
import { CustomPopover } from 'src/components/custom-popover';

// utils
import { fCurrency } from 'src/utils/format-number';
import { fDate } from 'src/utils/format-time';

// hooks
import { usePopover } from 'minimal-shared/hooks';
import { useAuthContext } from 'src/auth/hooks';

// types
import { IApplication } from 'src/types/application';

// ----------------------------------------------------------------------

type Props = {
  application: IApplication;
};

export function ApplicationCard({ application }: Props) {
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const popover = usePopover();
  
  const { 
    id, 
    status, 
    submittedAt, 
    requestedAmount,
    merchant
  } = application;

  const canProcess = user?.role === 'operations_staff' || user?.role === 'system_admin';

  const handleViewDetails = () => {
    navigate(`/dashboard/application/${id}`);
  };

  const handleProcessApplication = () => {
    navigate(`/dashboard/application/${id}`);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'approved':
        return 'success';
      case 'pending':
        return 'warning';
      case 'rejected':
        return 'error';
      case 'in_review':
        return 'info';
      case 'incomplete':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Card
      sx={{
        p: 3,
        width: 1,
        boxShadow: (theme) => theme.customShadows.z8,
        '&:hover': {
          boxShadow: (theme) => theme.customShadows.z24,
        },
      }}
    >
      <Stack spacing={2}>
        {/* Header with Status */}
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="subtitle1" noWrap>
            {merchant.legalName}
          </Typography>

          <Label 
            variant="soft" 
            color={getStatusColor(status)}
            sx={{ 
              textTransform: 'capitalize',
              fontWeight: 'bold',
              px: 2,
              py: 0.5,
            }}
          >
            {status.replace('_', ' ')}
          </Label>
        </Stack>

        {/* Merchant Details */}
        <Stack spacing={0.5}>
          {merchant.dbaName && (
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              DBA: {merchant.dbaName}
            </Typography>
          )}
          
          {merchant.industry && (
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              Industry: {merchant.industry}
            </Typography>
          )}
        </Stack>

        <Divider sx={{ borderStyle: 'dashed' }} />

        {/* Application Details */}
        <Stack direction="row" justifyContent="space-between">
          <Stack spacing={0.5}>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Submitted
            </Typography>
            <Typography variant="subtitle2">{fDate(submittedAt)}</Typography>
          </Stack>

          <Stack spacing={0.5} sx={{ textAlign: 'right' }}>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Requested Amount
            </Typography>
            <Typography variant="subtitle2">{fCurrency(requestedAmount)}</Typography>
          </Stack>
        </Stack>

        <Divider sx={{ borderStyle: 'dashed' }} />

        {/* Actions */}
        <Stack direction="row" spacing={2} justifyContent="flex-end">
          <Button
            size="small"
            color="inherit"
            variant="outlined"
            startIcon={<Iconify icon="eva:eye-fill" />}
            onClick={handleViewDetails}
          >
            View
          </Button>

          {canProcess && status.toLowerCase() === 'pending' && (
            <Button
              size="small"
              variant="contained"
              color="primary"
              startIcon={<Iconify icon="eva:checkmark-circle-2-fill" />}
              onClick={handleProcessApplication}
              sx={{
                bgcolor: (theme) => theme.palette.fundingPrimary?.main || theme.palette.primary.main,
                '&:hover': {
                  bgcolor: (theme) => theme.palette.fundingPrimary?.dark || theme.palette.primary.dark,
                },
              }}
            >
              Process
            </Button>
          )}

          <IconButton onClick={popover.onOpen}>
            <Iconify icon="eva:more-vertical-fill" />
          </IconButton>
        </Stack>
      </Stack>

      <CustomPopover
        open={popover.open}
        anchorEl={popover.anchorEl}
        onClose={popover.onClose}
      >
        <MenuItem onClick={handleViewDetails}>
          <Iconify icon="eva:eye-fill" sx={{ mr: 1 }} />
          View Details
        </MenuItem>

        {canProcess && (
          <MenuItem onClick={handleProcessApplication}>
            <Iconify icon="eva:checkmark-circle-2-fill" sx={{ mr: 1 }} />
            Process Application
          </MenuItem>
        )}
      </CustomPopover>
    </Card>
  );
}