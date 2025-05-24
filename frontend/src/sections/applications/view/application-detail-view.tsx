import { useState, useCallback } from 'react';
import type { IApplicationItem, IApplicationStatus } from 'src/types/application';

import Box from '@mui/material/Box';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import { varAlpha } from 'minimal-shared/utils';
import { useTabs } from 'minimal-shared/hooks';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';
import { useGetDocuments } from 'src/actions/documents';
import { useUpdateApplicationStatus } from 'src/actions/applications';

import { Iconify } from 'src/components/iconify';
import { Label } from 'src/components/label';
import { EmptyContent } from 'src/components/empty-content';
import { DashboardContent } from 'src/layouts/dashboard';

import { DocumentViewer } from 'src/sections/documents/document-viewer';
import { DocumentClassificationInfo } from 'src/sections/documents/document-classification-info';
import { DocumentControls } from 'src/sections/documents/document-controls';

// ----------------------------------------------------------------------

type Props = {
  application?: IApplicationItem;
  loading?: boolean;
  error?: any;
};

export function ApplicationDetailView({ application, error, loading }: Props) {
  const tabs = useTabs('details');
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  
  const { documents, isLoading: documentsLoading } = useGetDocuments(
    application?.id || '',
    { enabled: !!application?.id }
  );

  const { updateStatus, isLoading: updateLoading } = useUpdateApplicationStatus();

  const handleStatusChange = useCallback((newStatus: IApplicationStatus) => {
    if (application?.id) {
      updateStatus({
        id: application.id,
        status: newStatus,
      });
    }
  }, [application?.id, updateStatus]);

  const handleDocumentSelect = useCallback((documentId: string) => {
    setSelectedDocumentId(documentId);
  }, []);

  if (loading) {
    return (
      <DashboardContent sx={{ pt: 5 }}>
        <Box sx={{ p: 3 }}>
          <Stack spacing={3}>
            <Stack direction="row" justifyContent="space-between">
              <Box sx={{ width: '60%', height: 24, bgcolor: 'background.neutral', borderRadius: 1 }} />
              <Box sx={{ width: '30%', height: 24, bgcolor: 'background.neutral', borderRadius: 1 }} />
            </Stack>
            <Box sx={{ width: '100%', height: 320, bgcolor: 'background.neutral', borderRadius: 1 }} />
            <Box sx={{ width: '100%', height: 320, bgcolor: 'background.neutral', borderRadius: 1 }} />
          </Stack>
        </Box>
      </DashboardContent>
    );
  }

  if (error) {
    return (
      <DashboardContent sx={{ pt: 5 }}>
        <EmptyContent
          filled
          title="Application not found!"
          action={
            <Button
              component={RouterLink}
              href={paths.dashboard.root}
              startIcon={<Iconify width={16} icon="eva:arrow-ios-back-fill" />}
              sx={{ mt: 3 }}
            >
              Back to dashboard
            </Button>
          }
          sx={{ py: 10, height: 'auto', flexGrow: 'unset' }}
        />
      </DashboardContent>
    );
  }

  if (!application) {
    return null;
  }

  const selectedDocument = documents.find((doc) => doc.id === selectedDocumentId) || documents[0];

  return (
    <DashboardContent>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Button
            component={RouterLink}
            href={paths.dashboard.root}
            startIcon={<Iconify width={16} icon="eva:arrow-ios-back-fill" />}
          >
            Back
          </Button>
          <Typography variant="h4">
            Application #{application.id.slice(-8)}
          </Typography>
          <Label
            variant="soft"
            color={
              (application.status === 'approved' && 'success') ||
              (application.status === 'rejected' && 'error') ||
              (application.status === 'reviewing' && 'warning') ||
              (application.status === 'incomplete' && 'error') ||
              'info'
            }
          >
            {application.status.charAt(0).toUpperCase() + application.status.slice(1)}
          </Label>
        </Stack>

        <Stack direction="row" spacing={1}>
          {application.status === 'pending' && (
            <>
              <Button
                variant="contained"
                color="success"
                startIcon={<Iconify icon="eva:checkmark-circle-2-fill" />}
                onClick={() => handleStatusChange('approved')}
                disabled={updateLoading}
              >
                Approve
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<Iconify icon="eva:close-circle-fill" />}
                onClick={() => handleStatusChange('rejected')}
                disabled={updateLoading}
              >
                Reject
              </Button>
            </>
          )}
          {application.status === 'incomplete' && (
            <Button
              variant="contained"
              color="warning"
              startIcon={<Iconify icon="eva:alert-triangle-fill" />}
              onClick={() => handleStatusChange('reviewing')}
              disabled={updateLoading}
            >
              Mark for Review
            </Button>
          )}
          {application.status === 'reviewing' && (
            <>
              <Button
                variant="contained"
                color="success"
                startIcon={<Iconify icon="eva:checkmark-circle-2-fill" />}
                onClick={() => handleStatusChange('approved')}
                disabled={updateLoading}
              >
                Approve
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<Iconify icon="eva:close-circle-fill" />}
                onClick={() => handleStatusChange('rejected')}
                disabled={updateLoading}
              >
                Reject
              </Button>
            </>
          )}
        </Stack>
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={5} lg={4}>
          <Card sx={{ mb: 3 }}>
            <Typography variant="subtitle1" sx={{ p: 2, pb: 1 }}>
              Merchant Details
            </Typography>
            <Divider />
            <Stack spacing={2} sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Legal Name
                </Typography>
                <Typography variant="body2">{application.merchantDetails.legalName}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  DBA Name
                </Typography>
                <Typography variant="body2">{application.merchantDetails.dbaName}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  EIN
                </Typography>
                <Typography variant="body2">{application.merchantDetails.ein}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Industry
                </Typography>
                <Typography variant="body2">{application.merchantDetails.industry}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Annual Revenue
                </Typography>
                <Typography variant="body2">
                  ${application.merchantDetails.revenue.toLocaleString()}
                </Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Address
                </Typography>
                <Typography variant="body2" sx={{ textAlign: 'right' }}>
                  {application.merchantDetails.address}
                </Typography>
              </Stack>
            </Stack>
          </Card>

          <Card>
            <Typography variant="subtitle1" sx={{ p: 2, pb: 1 }}>
              Application Details
            </Typography>
            <Divider />
            <Stack spacing={2} sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Submission Date
                </Typography>
                <Typography variant="body2">
                  {new Date(application.createdAt).toLocaleDateString()}
                </Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Last Updated
                </Typography>
                <Typography variant="body2">
                  {new Date(application.updatedAt).toLocaleDateString()}
                </Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Status
                </Typography>
                <Label
                  variant="soft"
                  color={
                    (application.status === 'approved' && 'success') ||
                    (application.status === 'rejected' && 'error') ||
                    (application.status === 'reviewing' && 'warning') ||
                    (application.status === 'incomplete' && 'error') ||
                    'info'
                  }
                >
                  {application.status.charAt(0).toUpperCase() + application.status.slice(1)}
                </Label>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Review Status
                </Typography>
                <Typography variant="body2">{application.reviewStatus}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Documents
                </Typography>
                <Typography variant="body2">{documents.length}</Typography>
              </Stack>
            </Stack>
          </Card>

          {documents.length > 0 && (
            <Card sx={{ mt: 3 }}>
              <Typography variant="subtitle1" sx={{ p: 2, pb: 1 }}>
                Documents
              </Typography>
              <Divider />
              <Stack spacing={1} sx={{ p: 2 }}>
                {documents.map((document) => (
                  <Button
                    key={document.id}
                    variant={selectedDocumentId === document.id ? 'contained' : 'outlined'}
                    startIcon={<Iconify icon="eva:file-text-fill" />}
                    onClick={() => handleDocumentSelect(document.id)}
                    sx={{ justifyContent: 'flex-start', textAlign: 'left' }}
                  >
                    {document.type.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </Button>
                ))}
              </Stack>
            </Card>
          )}
        </Grid>

        <Grid item xs={12} md={7} lg={8}>
          <Card>
            <Tabs
              value={tabs.value}
              onChange={tabs.onChange}
              sx={[
                (theme) => ({
                  px: 3,
                  boxShadow: `inset 0 -2px 0 0 ${varAlpha(
                    theme.vars.palette.grey['500Channel'],
                    0.08
                  )}`,
                }),
              ]}
            >
              {[
                { value: 'details', label: 'Application Details' },
                { value: 'documents', label: 'Documents' },
              ].map((tab) => (
                <Tab key={tab.value} value={tab.value} label={tab.label} />
              ))}
            </Tabs>

            {tabs.value === 'details' && (
              <Box sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 3 }}>
                  Application Summary
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  This application was submitted on{' '}
                  {new Date(application.createdAt).toLocaleDateString()} by{' '}
                  {application.merchantDetails.legalName}{' '}
                  {application.merchantDetails.dbaName
                    ? `(DBA: ${application.merchantDetails.dbaName})`
                    : ''}
                  .
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  The merchant operates in the {application.merchantDetails.industry} industry
                  with an annual revenue of ${application.merchantDetails.revenue.toLocaleString()}.
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  Current application status: {application.status.charAt(0).toUpperCase() + application.status.slice(1)}
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  Review status: {application.reviewStatus}
                </Typography>

                {application.metadata && (
                  <>
                    <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>
                      Additional Information
                    </Typography>
                    <Grid container spacing={2}>
                      {Object.entries(application.metadata).map(([key, value]) => (
                        <Grid item xs={12} sm={6} key={key}>
                          <Stack direction="row" justifyContent="space-between">
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                              {key.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
                            </Typography>
                            <Typography variant="body2">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </Typography>
                          </Stack>
                        </Grid>
                      ))}
                    </Grid>
                  </>
                )}
              </Box>
            )}

            {tabs.value === 'documents' && documents.length > 0 && selectedDocument && (
              <Box sx={{ p: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="h6">
                    {selectedDocument.type.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </Typography>
                  <DocumentControls document={selectedDocument} />
                </Stack>
                
                <DocumentViewer document={selectedDocument} />
                
                <Box sx={{ mt: 3 }}>
                  <DocumentClassificationInfo document={selectedDocument} />
                </Box>
              </Box>
            )}

            {tabs.value === 'documents' && (!documents.length || documentsLoading) && (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="body1" sx={{ color: 'text.secondary', my: 5 }}>
                  {documentsLoading ? 'Loading documents...' : 'No documents available for this application.'}
                </Typography>
              </Box>
            )}
          </Card>
        </Grid>
      </Grid>
    </DashboardContent>
  );
}