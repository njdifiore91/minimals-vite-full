import { Helmet } from 'react-helmet-async';
import { useEffect, useState } from 'react';

// hooks
import { useAuth } from 'src/auth/hooks';

// config
import { CONFIG } from 'src/global-config';
import { AUTH_CONFIG } from 'src/global-config';
import { FEATURE_FLAGS } from 'src/global-config';

// types
import { IWebhookConfig, IWebhookEvent, IWebhookDeliveryLog, IWebhookTestResult } from 'src/types/webhook';

// components
import { Container, Typography, Card, CardHeader, CardContent, Alert, Box, Tab, Tabs, Button, TextField, Grid, IconButton, Tooltip, Divider, Paper, Stack, CircularProgress } from '@mui/material';
import LoadingScreen from 'src/components/loading-screen';
import Iconify from 'src/components/iconify';
import { DataGrid, GridColDef } from 'src/components/data-grid';
import { useSnackbar } from 'src/components/snackbar';
import Label from 'src/components/label';

// sections
import { webhookEndpoints } from 'src/lib/axios';

// ----------------------------------------------------------------------

/**
 * Webhook Configuration Page
 * 
 * This page allows System Admins to create, test, and manage webhook endpoints for integration with external systems.
 * It displays webhook delivery history and status, and enforces role-based access control.
 * 
 * Requirements:
 * - F-020-RQ-001: Create and manage webhook endpoints - Form validates URL format, supports CRUD operations
 * - F-020-RQ-002: Test webhook delivery with real-time feedback - User can send test payload, view response status
 * - F-020-RQ-003: Persist webhook configuration - Configuration saved in under 200ms, persists across sessions
 * - F-020-RQ-004: Enforce webhook access by role - Only System Admin can create or delete webhooks
 */

const metadata = {
  title: `Webhook configuration | Dashboard - ${CONFIG.appName}`,
};

export default function WebhookConfigPage() {
  const { user } = useAuth();
  const { enqueueSnackbar } = useSnackbar();
  const [isLoading, setIsLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [currentTab, setCurrentTab] = useState('webhooks');
  const [webhooks, setWebhooks] = useState<IWebhookConfig[]>([]);
  const [webhooksLoading, setWebhooksLoading] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState<IWebhookConfig | null>(null);
  const [deliveryLogs, setDeliveryLogs] = useState<IWebhookDeliveryLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [testResult, setTestResult] = useState<IWebhookTestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testEvent, setTestEvent] = useState<IWebhookEvent>(IWebhookEvent.APPLICATION_CREATED);
  
  // New webhook form state
  const [newWebhook, setNewWebhook] = useState({
    url: '',
    description: '',
    events: [IWebhookEvent.APPLICATION_CREATED],
    active: true,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Check user permissions
  useEffect(() => {
    if (user) {
      const userRoles = user.roles || [];
      const hasSystemAdminRole = userRoles.includes(AUTH_CONFIG.roles.SYSTEM_ADMIN);
      const hasOperationsRole = userRoles.includes(AUTH_CONFIG.roles.OPERATIONS_STAFF);
      
      setIsAdmin(hasSystemAdminRole);
      setHasAccess(hasSystemAdminRole || hasOperationsRole);
      setIsLoading(false);
    }
  }, [user]);

  // Load webhooks on initial render
  useEffect(() => {
    if (hasAccess && FEATURE_FLAGS.enableWebhookConfiguration) {
      fetchWebhooks();
    }
  }, [hasAccess]);

  // Fetch webhooks from API
  const fetchWebhooks = async () => {
    try {
      setWebhooksLoading(true);
      const response = await webhookEndpoints.list();
      setWebhooks(response.data);
    } catch (error) {
      console.error('Error fetching webhooks:', error);
      enqueueSnackbar('Failed to load webhooks', { variant: 'error' });
    } finally {
      setWebhooksLoading(false);
    }
  };

  // Fetch webhook delivery logs
  const fetchWebhookLogs = async (webhookId: string) => {
    if (!webhookId) return;
    
    try {
      setLogsLoading(true);
      const response = await webhookEndpoints.logs(webhookId);
      setDeliveryLogs(response.data);
    } catch (error) {
      console.error('Error fetching webhook logs:', error);
      enqueueSnackbar('Failed to load webhook delivery logs', { variant: 'error' });
    } finally {
      setLogsLoading(false);
    }
  };

  // Test webhook
  const testWebhook = async (webhookId: string, eventType: IWebhookEvent) => {
    if (!webhookId) return;
    
    try {
      setTestLoading(true);
      const response = await webhookEndpoints.test(webhookId, eventType);
      setTestResult(response.data);
      
      if (response.data.success) {
        enqueueSnackbar('Webhook test successful', { variant: 'success' });
      } else {
        enqueueSnackbar('Webhook test failed', { variant: 'warning' });
      }
      
      // Refresh logs after test
      fetchWebhookLogs(webhookId);
    } catch (error) {
      console.error('Error testing webhook:', error);
      enqueueSnackbar('Failed to test webhook', { variant: 'error' });
    } finally {
      setTestLoading(false);
    }
  };

  // Create new webhook
  const createWebhook = async () => {
    // Validate form
    const errors: Record<string, string> = {};
    if (!newWebhook.url) errors.url = 'URL is required';
    if (!newWebhook.description) errors.description = 'Description is required';
    if (!newWebhook.events.length) errors.events = 'At least one event must be selected';
    
    // URL validation
    if (newWebhook.url && !/^https?:\/\/[^\s$.?#].[^\s]*$/i.test(newWebhook.url)) {
      errors.url = 'Please enter a valid URL';
    }
    
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    
    try {
      const response = await webhookEndpoints.create(newWebhook);
      enqueueSnackbar('Webhook created successfully', { variant: 'success' });
      
      // Reset form
      setNewWebhook({
        url: '',
        description: '',
        events: [IWebhookEvent.APPLICATION_CREATED],
        active: true,
      });
      setFormErrors({});
      
      // Refresh webhooks list
      fetchWebhooks();
    } catch (error) {
      console.error('Error creating webhook:', error);
      enqueueSnackbar('Failed to create webhook', { variant: 'error' });
    }
  };

  // Delete webhook
  const deleteWebhook = async (webhookId: string) => {
    if (!isAdmin) {
      enqueueSnackbar('Only System Admins can delete webhooks', { variant: 'warning' });
      return;
    }
    
    if (!window.confirm('Are you sure you want to delete this webhook?')) {
      return;
    }
    
    try {
      await webhookEndpoints.delete(webhookId);
      enqueueSnackbar('Webhook deleted successfully', { variant: 'success' });
      
      // Reset selected webhook if it was deleted
      if (selectedWebhook?.id === webhookId) {
        setSelectedWebhook(null);
        setDeliveryLogs([]);
        setTestResult(null);
      }
      
      // Refresh webhooks list
      fetchWebhooks();
    } catch (error) {
      console.error('Error deleting webhook:', error);
      enqueueSnackbar('Failed to delete webhook', { variant: 'error' });
    }
  };

  // Toggle webhook active status
  const toggleWebhookStatus = async (webhook: IWebhookConfig) => {
    if (!isAdmin) {
      enqueueSnackbar('Only System Admins can modify webhooks', { variant: 'warning' });
      return;
    }
    
    try {
      const updatedWebhook = { ...webhook, active: !webhook.active };
      await webhookEndpoints.update(webhook.id, updatedWebhook);
      enqueueSnackbar(`Webhook ${updatedWebhook.active ? 'activated' : 'deactivated'} successfully`, { variant: 'success' });
      
      // Update selected webhook if it was modified
      if (selectedWebhook?.id === webhook.id) {
        setSelectedWebhook(updatedWebhook);
      }
      
      // Refresh webhooks list
      fetchWebhooks();
    } catch (error) {
      console.error('Error updating webhook:', error);
      enqueueSnackbar('Failed to update webhook', { variant: 'error' });
    }
  };

  // Handle tab change
  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setCurrentTab(newValue);
  };

  // Handle webhook selection
  const handleWebhookSelect = (webhook: IWebhookConfig) => {
    setSelectedWebhook(webhook);
    fetchWebhookLogs(webhook.id);
    setTestResult(null);
  };

  // Webhook table columns
  const webhookColumns: GridColDef[] = [
    { field: 'description', headerName: 'Description', flex: 1 },
    { field: 'url', headerName: 'URL', flex: 2 },
    { 
      field: 'active', 
      headerName: 'Status', 
      width: 120,
      renderCell: (params) => (
        <Label color={params.value ? 'success' : 'error'}>
          {params.value ? 'Active' : 'Inactive'}
        </Label>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <Tooltip title="View Details">
            <IconButton onClick={() => handleWebhookSelect(params.row)}>
              <Iconify icon="eva:eye-outline" />
            </IconButton>
          </Tooltip>
          {isAdmin && (
            <Tooltip title={params.row.active ? 'Deactivate' : 'Activate'}>
              <IconButton onClick={() => toggleWebhookStatus(params.row)}>
                <Iconify icon={params.row.active ? 'eva:toggle-right-outline' : 'eva:toggle-left-outline'} />
              </IconButton>
            </Tooltip>
          )}
          {isAdmin && (
            <Tooltip title="Delete">
              <IconButton onClick={() => deleteWebhook(params.row.id)} color="error">
                <Iconify icon="eva:trash-2-outline" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      ),
    },
  ];

  // Webhook logs table columns
  const logColumns: GridColDef[] = [
    { 
      field: 'createdAt', 
      headerName: 'Time', 
      width: 180,
      valueFormatter: (params) => new Date(params.value).toLocaleString(),
    },
    { 
      field: 'event', 
      headerName: 'Event', 
      width: 200,
      valueFormatter: (params) => params.value.replace(/_/g, ' ').toLowerCase(),
    },
    { 
      field: 'status', 
      headerName: 'Status', 
      width: 120,
      renderCell: (params) => {
        const color = 
          params.value === 'success' ? 'success' :
          params.value === 'failed' ? 'error' :
          params.value === 'retrying' ? 'warning' : 'info';
        
        return (
          <Label color={color}>
            {params.value}
          </Label>
        );
      },
    },
    { field: 'statusCode', headerName: 'Status Code', width: 120 },
    { field: 'attemptCount', headerName: 'Attempts', width: 100 },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      renderCell: (params) => (
        <Tooltip title="View Details">
          <IconButton>
            <Iconify icon="eva:info-outline" />
          </IconButton>
        </Tooltip>
      ),
    },
  ];

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!hasAccess) {
    return (
      <Container>
        <Helmet>
          <title>{metadata.title}</title>
        </Helmet>
        <Box sx={{ py: 12 }}>
          <Alert severity="error">
            You do not have permission to access the webhook configuration. This feature requires System Admin or Operations Staff role.
          </Alert>
        </Box>
      </Container>
    );
  }

  if (!FEATURE_FLAGS.enableWebhookConfiguration) {
    return (
      <Container>
        <Helmet>
          <title>{metadata.title}</title>
        </Helmet>
        <Box sx={{ py: 12 }}>
          <Alert severity="info">
            Webhook configuration is currently disabled. Please contact your system administrator.
          </Alert>
        </Box>
      </Container>
    );
  }

  return (
    <>
      <Helmet>
        <title>{metadata.title}</title>
      </Helmet>

      <Container maxWidth={false}>
        <Typography variant="h4" sx={{ mb: 3 }}>
          Webhook Configuration
        </Typography>

        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          sx={{ mb: 3 }}
        >
          <Tab value="webhooks" label="Webhooks" />
          <Tab value="create" label="Create Webhook" disabled={!isAdmin} />
        </Tabs>

        {currentTab === 'webhooks' && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={selectedWebhook ? 7 : 12}>
              <Card>
                <CardHeader 
                  title="Webhook Endpoints" 
                  action={
                    <Button
                      variant="contained"
                      startIcon={<Iconify icon="eva:plus-fill" />}
                      onClick={() => setCurrentTab('create')}
                      disabled={!isAdmin}
                    >
                      New Webhook
                    </Button>
                  }
                />
                <CardContent>
                  {webhooksLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                      <CircularProgress />
                    </Box>
                  ) : webhooks.length === 0 ? (
                    <Alert severity="info">
                      No webhooks configured. {isAdmin && 'Click the "New Webhook" button to create one.'}
                    </Alert>
                  ) : (
                    <DataGrid
                      rows={webhooks}
                      columns={webhookColumns}
                      autoHeight
                      disableRowSelectionOnClick
                      pageSizeOptions={[5, 10, 25]}
                      initialState={{
                        pagination: { paginationModel: { pageSize: 5 } },
                      }}
                    />
                  )}
                </CardContent>
              </Card>
            </Grid>

            {selectedWebhook && (
              <Grid item xs={12} md={5}>
                <Card>
                  <CardHeader 
                    title={`Webhook Details: ${selectedWebhook.description}`}
                    subheader={selectedWebhook.url}
                    action={
                      <Label color={selectedWebhook.active ? 'success' : 'error'}>
                        {selectedWebhook.active ? 'Active' : 'Inactive'}
                      </Label>
                    }
                  />
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>Events:</Typography>
                    <Box sx={{ mb: 3 }}>
                      {selectedWebhook.events.map((event) => (
                        <Label key={event} color="primary" sx={{ mr: 1, mb: 1 }}>
                          {event.replace(/_/g, ' ').toLowerCase()}
                        </Label>
                      ))}
                    </Box>

                    <Divider sx={{ my: 3 }} />

                    <Typography variant="subtitle2" gutterBottom>Test Webhook:</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                      <TextField
                        select
                        label="Event Type"
                        value={testEvent}
                        onChange={(e) => setTestEvent(e.target.value as IWebhookEvent)}
                        SelectProps={{ native: true }}
                        sx={{ mr: 2, minWidth: 200 }}
                      >
                        {Object.values(IWebhookEvent).map((event) => (
                          <option key={event} value={event}>
                            {event.replace(/_/g, ' ').toLowerCase()}
                          </option>
                        ))}
                      </TextField>
                      <Button
                        variant="contained"
                        onClick={() => testWebhook(selectedWebhook.id, testEvent)}
                        disabled={testLoading}
                        startIcon={testLoading ? <CircularProgress size={20} /> : <Iconify icon="eva:flash-outline" />}
                      >
                        Test
                      </Button>
                    </Box>

                    {testResult && (
                      <Paper 
                        variant="outlined" 
                        sx={{ 
                          p: 2, 
                          mb: 3, 
                          bgcolor: testResult.success ? 'success.lighter' : 'error.lighter',
                          borderColor: testResult.success ? 'success.light' : 'error.light',
                        }}
                      >
                        <Typography variant="subtitle2">
                          Test Result: {testResult.success ? 'Success' : 'Failed'}
                        </Typography>
                        {testResult.statusCode && (
                          <Typography variant="body2">
                            Status Code: {testResult.statusCode}
                          </Typography>
                        )}
                        {testResult.responseTime && (
                          <Typography variant="body2">
                            Response Time: {testResult.responseTime}ms
                          </Typography>
                        )}
                        {testResult.errorMessage && (
                          <Typography variant="body2" color="error.main">
                            Error: {testResult.errorMessage}
                          </Typography>
                        )}
                      </Paper>
                    )}

                    <Divider sx={{ my: 3 }} />

                    <Typography variant="subtitle2" gutterBottom>Recent Delivery Logs:</Typography>
                    {logsLoading ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                        <CircularProgress />
                      </Box>
                    ) : deliveryLogs.length === 0 ? (
                      <Alert severity="info">
                        No delivery logs found for this webhook.
                      </Alert>
                    ) : (
                      <DataGrid
                        rows={deliveryLogs}
                        columns={logColumns}
                        autoHeight
                        disableRowSelectionOnClick
                        pageSizeOptions={[5, 10]}
                        initialState={{
                          pagination: { paginationModel: { pageSize: 5 } },
                        }}
                      />
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        )}

        {currentTab === 'create' && isAdmin && (
          <Card>
            <CardHeader title="Create New Webhook" />
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Webhook URL"
                    placeholder="https://example.com/webhook"
                    value={newWebhook.url}
                    onChange={(e) => setNewWebhook({ ...newWebhook, url: e.target.value })}
                    error={!!formErrors.url}
                    helperText={formErrors.url || 'Enter the URL that will receive webhook events'}
                    required
                  />
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Description"
                    placeholder="Application status notifications"
                    value={newWebhook.description}
                    onChange={(e) => setNewWebhook({ ...newWebhook, description: e.target.value })}
                    error={!!formErrors.description}
                    helperText={formErrors.description || 'Enter a description for this webhook'}
                    required
                  />
                </Grid>

                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>Events to trigger this webhook:</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {Object.values(IWebhookEvent).map((event) => {
                      const isSelected = newWebhook.events.includes(event);
                      return (
                        <Button
                          key={event}
                          variant={isSelected ? 'contained' : 'outlined'}
                          color={isSelected ? 'primary' : 'inherit'}
                          onClick={() => {
                            if (isSelected) {
                              // Don't allow removing the last event
                              if (newWebhook.events.length > 1) {
                                setNewWebhook({
                                  ...newWebhook,
                                  events: newWebhook.events.filter(e => e !== event)
                                });
                              }
                            } else {
                              setNewWebhook({
                                ...newWebhook,
                                events: [...newWebhook.events, event]
                              });
                            }
                          }}
                          sx={{ mb: 1 }}
                        >
                          {event.replace(/_/g, ' ').toLowerCase()}
                        </Button>
                      );
                    })}
                  </Box>
                  {formErrors.events && (
                    <Typography color="error" variant="caption">
                      {formErrors.events}
                    </Typography>
                  )}
                </Grid>

                <Grid item xs={12}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={createWebhook}
                    startIcon={<Iconify icon="eva:save-outline" />}
                  >
                    Create Webhook
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}
      </Container>
    </>
  );
}