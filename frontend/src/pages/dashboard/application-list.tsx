import { useState, useEffect, useCallback } from 'react';
import { CONFIG } from 'src/global-config';
import { useBoolean, useSetState } from 'minimal-shared/hooks';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import { Pagination } from '@mui/material';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';
import { DashboardContent } from 'src/layouts/dashboard';

import { Iconify } from 'src/components/iconify';
import { EmptyContent } from 'src/components/empty-content';
import { ConfirmDialog } from 'src/components/custom-dialog';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';

import { ApplicationCard } from 'src/sections/applications';
import { useGetApplications } from 'src/actions/applications';
import type { IApplicationFilters, IApplicationStatus } from 'src/types/application';

// ----------------------------------------------------------------------

const metadata = { title: `Application list | Dashboard - ${CONFIG.appName}` };

/**
 * MCA Application List Page
 * 
 * Displays a list of Merchant Cash Advance applications with filtering, sorting,
 * and pagination capabilities. This page is accessible to Operations Staff and
 * System Admin roles only.
 * 
 * @returns React component for the application list page
 */
export default function ApplicationListPage() {
  const confirmDialog = useBoolean();
  
  // Pagination state
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 9,
  });

  // Filters state
  const filters = useSetState<IApplicationFilters>({
    status: '',
    dateRange: {
      startDate: null,
      endDate: null,
    },
    merchantName: '',
  });

  // Get applications data with pagination and filters
  const {
    applications,
    pagination: { total, totalPages },
    applicationsLoading,
    applicationsEmpty,
    refetch,
  } = useGetApplications(pagination, filters.state);

  // Handle page change
  const handlePageChange = useCallback(
    (_: React.ChangeEvent<unknown>, newPage: number) => {
      setPagination(prev => ({
        ...prev,
        page: newPage,
      }));
    },
    []
  );

  // Handle bulk actions (placeholder for future implementation)
  const handleBulkActions = useCallback(() => {
    confirmDialog.onTrue();
  }, [confirmDialog]);

  return (
    <>
      <title>{metadata.title}</title>

      <DashboardContent>
        <CustomBreadcrumbs
          heading="Applications"
          links={[
            { name: 'Dashboard', href: paths.dashboard.root },
            { name: 'Applications' },
          ]}
          action={
            <Button
              component={RouterLink}
              href={paths.dashboard.application.new}
              variant="contained"
              startIcon={<Iconify icon="mingcute:add-line" />}
            >
              New Application
            </Button>
          }
          sx={{ mb: { xs: 3, md: 5 } }}
        />

        {/* Application list */}
        <Card sx={{ p: 3 }}>
          {/* Filters would go here */}
          
          {applicationsEmpty ? (
            <EmptyContent
              title="No Applications Found"
              description="Try adjusting your search or filters to find what you're looking for."
              sx={{ py: 10 }}
            />
          ) : (
            <>
              <Box
                gap={3}
                display="grid"
                gridTemplateColumns={{
                  xs: 'repeat(1, 1fr)',
                  sm: 'repeat(2, 1fr)',
                  md: 'repeat(3, 1fr)',
                }}
              >
                {applications.map((application) => (
                  <ApplicationCard key={application.id} application={application} />
                ))}
              </Box>

              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}>
                  <Pagination
                    count={totalPages}
                    page={pagination.page}
                    onChange={handlePageChange}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </Card>
      </DashboardContent>

      <ConfirmDialog
        open={confirmDialog.value}
        onClose={confirmDialog.onFalse}
        title="Bulk Action"
        content="Are you sure you want to perform this action on the selected applications?"
        action={
          <Button
            variant="contained"
            color="error"
            onClick={() => {
              // Implement bulk action logic here
              confirmDialog.onFalse();
            }}
          >
            Confirm
          </Button>
        }
      />
    </>
  );
}