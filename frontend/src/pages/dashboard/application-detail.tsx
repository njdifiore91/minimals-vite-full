import { useParams } from 'src/routes/hooks';

import { CONFIG } from 'src/global-config';
import { useGetApplicationById, useUpdateApplicationStatus } from 'src/actions/applications';
import { useGetDocuments } from 'src/actions/documents';

import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardHeader from '@mui/material/CardHeader';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';

import { DocumentViewer } from 'src/sections/documents/document-viewer';
import { DocumentClassificationInfo } from 'src/sections/documents/document-classification-info';

// ----------------------------------------------------------------------

const metadata = { title: `Application details | Dashboard - ${CONFIG.appName}` };

export default function ApplicationDetailPage() {
  const { id = '' } = useParams();

  const { application, applicationLoading, applicationError } = useGetApplicationById(id);
  const { documents, documentsLoading } = useGetDocuments(id);
  const { updateStatus, updateStatusLoading } = useUpdateApplicationStatus();

  return (
    <>
      <title>{metadata.title}</title>

      <Container maxWidth="xl">
        {applicationError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Error loading application: {applicationError.message}
          </Alert>
        )}

        {(applicationLoading || documentsLoading) ? (
          <Stack direction="row" justifyContent="center" alignItems="center" spacing={2} sx={{ py: 5 }}>
            <CircularProgress />
            <Typography variant="body1">Loading application details...</Typography>
          </Stack>
        ) : application ? (
          <Grid container spacing={3}>
            {/* Application Details */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader 
                  title="Application Details" 
                  action={
                    <Stack direction="row" spacing={1}>
                      {application.status !== 'approved' && (
                        <Button 
                          variant="contained" 
                          color="success"
                          disabled={updateStatusLoading}
                          onClick={() => updateStatus(application.id, 'approved')}
                        >
                          {updateStatusLoading ? 'Updating...' : 'Approve'}
                        </Button>
                      )}
                      {application.status !== 'rejected' && (
                        <Button 
                          variant="contained" 
                          color="error"
                          disabled={updateStatusLoading}
                          onClick={() => updateStatus(application.id, 'rejected')}
                        >
                          {updateStatusLoading ? 'Updating...' : 'Reject'}
                        </Button>
                      )}
                    </Stack>
                  }
                />
                <Divider />
                <CardContent>
                  <Stack spacing={2}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Status</Typography>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          color: (
                            application.status === 'approved' ? 'success.main' : 
                            application.status === 'rejected' ? 'error.main' : 
                            application.status === 'pending' ? 'warning.main' : 
                            'text.secondary'
                          ),
                          fontWeight: 'bold',
                          textTransform: 'uppercase'
                        }}
                      >
                        {application.status}
                      </Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Application ID</Typography>
                      <Typography variant="body2">{application.id}</Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Submission Date</Typography>
                      <Typography variant="body2">
                        {new Date(application.created_at).toLocaleDateString()}
                      </Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Last Updated</Typography>
                      <Typography variant="body2">
                        {new Date(application.updated_at).toLocaleDateString()}
                      </Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Review Status</Typography>
                      <Typography variant="body2">{application.review_status}</Typography>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>

              {/* Merchant Details */}
              <Card sx={{ mt: 3 }}>
                <CardHeader title="Merchant Details" />
                <Divider />
                <CardContent>
                  <Stack spacing={2}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Legal Name</Typography>
                      <Typography variant="body2">{application.merchant?.legal_name}</Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">DBA Name</Typography>
                      <Typography variant="body2">{application.merchant?.dba_name}</Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">EIN</Typography>
                      <Typography variant="body2">{application.merchant?.ein}</Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Industry</Typography>
                      <Typography variant="body2">{application.merchant?.industry}</Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Revenue</Typography>
                      <Typography variant="body2">
                        ${application.merchant?.revenue?.toLocaleString()}
                      </Typography>
                    </Stack>

                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2">Address</Typography>
                      <Typography variant="body2" align="right">
                        {application.merchant?.address}
                      </Typography>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* Documents */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Documents" />
                <Divider />
                <CardContent>
                  {documents && documents.length > 0 ? (
                    <Stack spacing={3}>
                      {documents.map((document) => (
                        <Card key={document.id} variant="outlined">
                          <CardHeader 
                            title={document.type} 
                            subheader={`Uploaded: ${new Date(document.uploaded_at).toLocaleDateString()}`}
                          />
                          <CardContent>
                            <DocumentViewer documentId={document.id} />
                            <DocumentClassificationInfo 
                              classification={document.classification} 
                              metadata={document.metadata} 
                            />
                          </CardContent>
                        </Card>
                      ))}
                    </Stack>
                  ) : (
                    <Typography variant="body1" align="center" sx={{ py: 5 }}>
                      No documents found for this application.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Alert severity="info" sx={{ mb: 3 }}>
            Application not found. Please check the application ID and try again.
          </Alert>
        )}
      </Container>
    </>
  );
}