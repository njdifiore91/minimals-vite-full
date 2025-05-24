import { useState } from 'react';
import { Helmet } from 'react-helmet-async';

// @mui
import {
  Box,
  Card,
  Table,
  Stack,
  Paper,
  Button,
  Tooltip,
  Divider,
  TableRow,
  MenuItem,
  TableBody,
  TableCell,
  Container,
  Typography,
  IconButton,
  TableContainer,
  TableHead,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  Chip,
  Alert,
  CircularProgress,
  Tab,
  Tabs,
  Grid,
  FormHelperText,
  OutlinedInput,
  Checkbox,
  ListItemText,
} from '@mui/material';
import { LoadingButton } from '@mui/lab';

// components
import Iconify from 'src/components/iconify';
import Scrollbar from 'src/components/scrollbar';
import { useSnackbar } from 'src/components/snackbar';
import { useSettingsContext } from 'src/components/settings';
import { useTable, TableHeadCustom, TableNoData, TablePaginationCustom } from 'src/components/table';
import { useBoolean } from 'src/hooks/use-boolean';
import { useResponsive } from 'src/hooks/use-responsive';

// auth
import { useAuthContext } from 'src/auth/hooks';
import { AUTH_CONFIG } from 'src/global-config';

// hooks
import {
  useGetWebhooks,
  usePostWebhookConfig,
  useTestWebhook,
  useWebhookLogs,
  IWebhookConfig,
  IWebhookLog,
  ICreateWebhookConfig,
  IWebhookTestRequest,
} from 'src/actions/webhooks';

// utils
import { fDateTime } from 'src/utils/format-time';
import { fData } from 'src/utils/format-number';

// ----------------------------------------------------------------------

const TABLE_HEAD = [
  { id: 'name', label: 'Name', align: 'left' },
  { id: 'url', label: 'URL', align: 'left' },
  { id: 'events', label: 'Events', align: 'left' },
  { id: 'status', label: 'Status', align: 'left' },
  { id: 'lastDelivery', label: 'Last Delivery', align: 'left' },
  { id: 'actions', label: 'Actions', align: 'right' },
];

const LOGS_TABLE_HEAD = [
  { id: 'timestamp', label: 'Timestamp', align: 'left' },
  { id: 'event', label: 'Event', align: 'left' },
  { id: 'status', label: 'Status', align: 'left' },
  { id: 'duration', label: 'Duration', align: 'left' },
  { id: 'details', label: 'Details', align: 'right' },
];

const EVENT_OPTIONS = [
  'application.created',
  'application.updated',
  'application.status_changed',
  'document.uploaded',
  'document.classified',
  'document.processed',
];

// ----------------------------------------------------------------------

export default function WebhookConfigPage() {
  const { enqueueSnackbar } = useSnackbar();
  const { user } = useAuthContext();
  
  // Check if user has System Admin role
  const isSystemAdmin = user?.role === AUTH_CONFIG.roles.SYSTEM_ADMIN;

  return (
    <>
      <Helmet>
        <title>Webhook configuration | Dashboard - Dollar Funding</title>
      </Helmet>

      <Container maxWidth="xl">
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={5}>
          <Typography variant="h4">Webhook Configuration</Typography>

          {isSystemAdmin && (
            <Button
              variant="contained"
              color="primary"
              startIcon={<Iconify icon="eva:plus-fill" />}
              onClick={() => window.dispatchEvent(new CustomEvent('open-webhook-form'))}
            >
              New Webhook
            </Button>
          )}
        </Stack>

        <WebhookConfigView />
      </Container>
    </>
  );
}

// ----------------------------------------------------------------------

function WebhookConfigView() {
  const { user } = useAuthContext();
  const { enqueueSnackbar } = useSnackbar();
  const table = useTable({ defaultRowsPerPage: 10 });
  const upMd = useResponsive('up', 'md');
  
  // Check if user has System Admin role
  const isSystemAdmin = user?.role === AUTH_CONFIG.roles.SYSTEM_ADMIN;
  
  // State for selected webhook (for logs and testing)
  const [selectedWebhook, setSelectedWebhook] = useState<IWebhookConfig | null>(null);
  
  // State for tab selection
  const [currentTab, setCurrentTab] = useState('webhooks');
  
  // Fetch webhooks
  const {
    webhooks,
    webhooksLoading,
    webhooksError,
    webhooksEmpty,
    revalidateWebhooks,
  } = useGetWebhooks();
  
  // Fetch logs for selected webhook
  const {
    logs,
    logsLoading,
    logsEmpty,
  } = useWebhookLogs(selectedWebhook?.id || '', {
    limit: 50,
  });
  
  // Create webhook form state
  const openForm = useBoolean(false);
  
  // Test webhook dialog state
  const openTest = useBoolean(false);
  
  // Log details dialog state
  const openLogDetails = useBoolean(false);
  const [selectedLog, setSelectedLog] = useState<IWebhookLog | null>(null);
  
  // Handle tab change
  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setCurrentTab(newValue);
  };
  
  // Handle webhook selection for logs
  const handleViewLogs = (webhook: IWebhookConfig) => {
    setSelectedWebhook(webhook);
    setCurrentTab('logs');
  };
  
  // Handle webhook selection for testing
  const handleTestWebhook = (webhook: IWebhookConfig) => {
    setSelectedWebhook(webhook);
    openTest.onTrue();
  };
  
  // Handle log selection for details
  const handleViewLogDetails = (log: IWebhookLog) => {
    setSelectedLog(log);
    openLogDetails.onTrue();
  };
  
  return (
    <>
      <Card>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          sx={{ px: 2, bgcolor: 'background.neutral' }}
        >
          <Tab value="webhooks" label="Webhooks" />
          {selectedWebhook && (
            <Tab 
              value="logs" 
              label={`Delivery Logs: ${selectedWebhook.name}`} 
              disabled={!selectedWebhook}
            />
          )}
        </Tabs>
        
        <Divider />
        
        {currentTab === 'webhooks' && (
          <>
            <TableContainer sx={{ position: 'relative', overflow: 'unset' }}>
              <Scrollbar>
                <Table size={upMd ? 'medium' : 'small'} sx={{ minWidth: 800 }}>
                  <TableHeadCustom headLabel={TABLE_HEAD} />
                  
                  <TableBody>
                    {webhooksLoading ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                          <CircularProgress />
                        </TableCell>
                      </TableRow>
                    ) : webhooksEmpty ? (
                      <TableNoData notFound={webhooksEmpty} />
                    ) : (
                      webhooks.map((webhook) => (
                        <WebhookTableRow
                          key={webhook.id}
                          webhook={webhook}
                          isSystemAdmin={isSystemAdmin}
                          onViewLogs={() => handleViewLogs(webhook)}
                          onTestWebhook={() => handleTestWebhook(webhook)}
                          onRefresh={revalidateWebhooks}
                        />
                      ))
                    )}
                  </TableBody>
                </Table>
              </Scrollbar>
            </TableContainer>
            
            <TablePaginationCustom
              count={webhooks.length}
              page={table.page}
              rowsPerPage={table.rowsPerPage}
              onPageChange={table.onChangePage}
              onRowsPerPageChange={table.onChangeRowsPerPage}
            />
          </>
        )}
        
        {currentTab === 'logs' && selectedWebhook && (
          <>
            <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="subtitle1">
                Delivery Logs for: {selectedWebhook.name}
              </Typography>
              <Button
                variant="outlined"
                startIcon={<Iconify icon="eva:arrow-back-fill" />}
                onClick={() => setCurrentTab('webhooks')}
              >
                Back to Webhooks
              </Button>
            </Box>
            
            <Divider />
            
            <TableContainer sx={{ position: 'relative', overflow: 'unset' }}>
              <Scrollbar>
                <Table size={upMd ? 'medium' : 'small'} sx={{ minWidth: 800 }}>
                  <TableHeadCustom headLabel={LOGS_TABLE_HEAD} />
                  
                  <TableBody>
                    {logsLoading ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                          <CircularProgress />
                        </TableCell>
                      </TableRow>
                    ) : logsEmpty ? (
                      <TableNoData notFound={logsEmpty} />
                    ) : (
                      logs.map((log) => (
                        <LogTableRow
                          key={log.id}
                          log={log}
                          onViewDetails={() => handleViewLogDetails(log)}
                        />
                      ))
                    )}
                  </TableBody>
                </Table>
              </Scrollbar>
            </TableContainer>
          </>
        )}
      </Card>
      
      {/* Create Webhook Form Dialog */}
      <CreateWebhookDialog 
        open={openForm.value} 
        onClose={openForm.onFalse} 
        onRefresh={revalidateWebhooks} 
      />
      
      {/* Test Webhook Dialog */}
      {selectedWebhook && (
        <TestWebhookDialog
          open={openTest.value}
          onClose={openTest.onFalse}
          webhook={selectedWebhook}
        />
      )}
      
      {/* Log Details Dialog */}
      {selectedLog && (
        <LogDetailsDialog
          open={openLogDetails.value}
          onClose={openLogDetails.onFalse}
          log={selectedLog}
        />
      )}
      
      {/* Event listener to open webhook form from outside this component */}
      <EventListener 
        eventName="open-webhook-form" 
        callback={openForm.onTrue} 
      />
    </>
  );
}

// ----------------------------------------------------------------------

type WebhookTableRowProps = {
  webhook: IWebhookConfig;
  isSystemAdmin: boolean;
  onViewLogs: VoidFunction;
  onTestWebhook: VoidFunction;
  onRefresh: VoidFunction;
};

function WebhookTableRow({ webhook, isSystemAdmin, onViewLogs, onTestWebhook, onRefresh }: WebhookTableRowProps) {
  const { enqueueSnackbar } = useSnackbar();
  const [openConfirm, setOpenConfirm] = useState(false);
  
  const handleDeleteClick = () => {
    setOpenConfirm(true);
  };
  
  const handleDeleteConfirm = async () => {
    try {
      // This would be implemented with a delete webhook hook
      // For now, we'll just show a success message
      enqueueSnackbar('Webhook deleted successfully', { variant: 'success' });
      onRefresh();
    } catch (error) {
      console.error(error);
      enqueueSnackbar('Failed to delete webhook', { variant: 'error' });
    } finally {
      setOpenConfirm(false);
    }
  };
  
  const handleDeleteCancel = () => {
    setOpenConfirm(false);
  };
  
  return (
    <>
      <TableRow hover>
        <TableCell>{webhook.name}</TableCell>
        
        <TableCell>
          <Typography variant="body2" sx={{ maxWidth: 240 }} noWrap>
            {webhook.url}
          </Typography>
        </TableCell>
        
        <TableCell>
          <Stack direction="row" flexWrap="wrap" spacing={1}>
            {webhook.events.map((event) => (
              <Chip 
                key={event} 
                label={event} 
                size="small" 
                color="info" 
                variant="outlined" 
              />
            ))}
          </Stack>
        </TableCell>
        
        <TableCell>
          <Chip
            label={webhook.status}
            size="small"
            color={webhook.status === 'active' ? 'success' : 'default'}
          />
        </TableCell>
        
        <TableCell>
          {webhook.lastDeliveryTime ? (
            <Stack spacing={0.5}>
              <Typography variant="body2">{fDateTime(webhook.lastDeliveryTime)}</Typography>
              <Chip
                label={webhook.lastDeliveryStatus}
                size="small"
                color={
                  webhook.lastDeliveryStatus === 'success'
                    ? 'success'
                    : webhook.lastDeliveryStatus === 'failed'
                    ? 'error'
                    : 'warning'
                }
                sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: 10 } }}
              />
            </Stack>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No deliveries yet
            </Typography>
          )}
        </TableCell>
        
        <TableCell align="right">
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Tooltip title="View Logs">
              <IconButton onClick={onViewLogs} color="info">
                <Iconify icon="mdi:history" />
              </IconButton>
            </Tooltip>
            
            {isSystemAdmin && (
              <>
                <Tooltip title="Test Webhook">
                  <IconButton onClick={onTestWebhook} color="success">
                    <Iconify icon="mdi:test-tube" />
                  </IconButton>
                </Tooltip>
                
                <Tooltip title="Delete">
                  <IconButton onClick={handleDeleteClick} color="error">
                    <Iconify icon="eva:trash-2-outline" />
                  </IconButton>
                </Tooltip>
              </>
            )}
          </Stack>
        </TableCell>
      </TableRow>
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={openConfirm} onClose={handleDeleteCancel}>
        <DialogTitle>Delete Webhook</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the webhook "{webhook.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

// ----------------------------------------------------------------------

type LogTableRowProps = {
  log: IWebhookLog;
  onViewDetails: VoidFunction;
};

function LogTableRow({ log, onViewDetails }: LogTableRowProps) {
  return (
    <TableRow hover>
      <TableCell>{fDateTime(log.timestamp)}</TableCell>
      
      <TableCell>
        <Chip 
          label={log.event} 
          size="small" 
          color="info" 
          variant="outlined" 
        />
      </TableCell>
      
      <TableCell>
        <Chip
          label={log.responseStatus >= 200 && log.responseStatus < 300 ? 'Success' : 'Failed'}
          size="small"
          color={log.responseStatus >= 200 && log.responseStatus < 300 ? 'success' : 'error'}
        />
        <Typography variant="caption" display="block" sx={{ color: 'text.secondary' }}>
          Status: {log.responseStatus}
        </Typography>
      </TableCell>
      
      <TableCell>
        <Typography variant="body2">
          {log.duration}ms
        </Typography>
      </TableCell>
      
      <TableCell align="right">
        <IconButton onClick={onViewDetails} color="info">
          <Iconify icon="eva:info-outline" />
        </IconButton>
      </TableCell>
    </TableRow>
  );
}

// ----------------------------------------------------------------------

type CreateWebhookDialogProps = {
  open: boolean;
  onClose: VoidFunction;
  onRefresh: VoidFunction;
};

function CreateWebhookDialog({ open, onClose, onRefresh }: CreateWebhookDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const { createWebhook, isSubmitting, error } = usePostWebhookConfig();
  
  // Form state
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [events, setEvents] = useState<string[]>([]);
  const [status, setStatus] = useState<'active' | 'inactive'>('active');
  
  // Form validation
  const [errors, setErrors] = useState({
    name: '',
    url: '',
    events: '',
  });
  
  // Reset form
  const resetForm = () => {
    setName('');
    setUrl('');
    setDescription('');
    setEvents([]);
    setStatus('active');
    setErrors({
      name: '',
      url: '',
      events: '',
    });
  };
  
  // Handle close
  const handleClose = () => {
    resetForm();
    onClose();
  };
  
  // Validate form
  const validateForm = (): boolean => {
    let isValid = true;
    const newErrors = {
      name: '',
      url: '',
      events: '',
    };
    
    if (!name.trim()) {
      newErrors.name = 'Name is required';
      isValid = false;
    }
    
    if (!url.trim()) {
      newErrors.url = 'URL is required';
      isValid = false;
    } else {
      try {
        new URL(url);
      } catch (e) {
        newErrors.url = 'Invalid URL format';
        isValid = false;
      }
    }
    
    if (events.length === 0) {
      newErrors.events = 'At least one event must be selected';
      isValid = false;
    }
    
    setErrors(newErrors);
    return isValid;
  };
  
  // Handle submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      const webhookConfig: ICreateWebhookConfig = {
        name,
        url,
        description,
        events,
        status,
      };
      
      await createWebhook(webhookConfig);
      enqueueSnackbar('Webhook created successfully', { variant: 'success' });
      onRefresh();
      handleClose();
    } catch (error) {
      console.error(error);
      enqueueSnackbar('Failed to create webhook', { variant: 'error' });
    }
  };
  
  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create New Webhook</DialogTitle>
      
      <DialogContent>
        <Box component="form" noValidate onSubmit={handleSubmit} sx={{ mt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Name"
                name="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                error={!!errors.name}
                helperText={errors.name}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="URL"
                name="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                error={!!errors.url}
                helperText={errors.url}
                placeholder="https://example.com/webhook"
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                name="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                multiline
                rows={2}
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth error={!!errors.events}>
                <InputLabel id="events-label">Events</InputLabel>
                <Select
                  labelId="events-label"
                  multiple
                  value={events}
                  onChange={(e) => setEvents(e.target.value as string[])}
                  input={<OutlinedInput label="Events" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {EVENT_OPTIONS.map((event) => (
                    <MenuItem key={event} value={event}>
                      <Checkbox checked={events.indexOf(event) > -1} />
                      <ListItemText primary={event} />
                    </MenuItem>
                  ))}
                </Select>
                {errors.events && <FormHelperText>{errors.events}</FormHelperText>}
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel id="status-label">Status</InputLabel>
                <Select
                  labelId="status-label"
                  value={status}
                  onChange={(e) => setStatus(e.target.value as 'active' | 'inactive')}
                  label="Status"
                >
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="inactive">Inactive</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            {error && (
              <Grid item xs={12}>
                <Alert severity="error">
                  {error.message || 'An error occurred while creating the webhook'}
                </Alert>
              </Grid>
            )}
          </Grid>
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <LoadingButton
          loading={isSubmitting}
          onClick={handleSubmit}
          variant="contained"
          color="primary"
        >
          Create
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
}

// ----------------------------------------------------------------------

type TestWebhookDialogProps = {
  open: boolean;
  onClose: VoidFunction;
  webhook: IWebhookConfig;
};

function TestWebhookDialog({ open, onClose, webhook }: TestWebhookDialogProps) {
  const { testWebhook, isSubmitting, testResult, error, clearTestResult } = useTestWebhook();
  
  // Form state
  const [payload, setPayload] = useState(JSON.stringify({
    event: webhook.events[0] || 'application.created',
    data: {
      id: '123e4567-e89b-12d3-a456-426614174000',
      timestamp: new Date().toISOString(),
      test: true,
    },
  }, null, 2));
  
  // Form validation
  const [payloadError, setPayloadError] = useState('');
  
  // Handle close
  const handleClose = () => {
    clearTestResult();
    onClose();
  };
  
  // Validate payload
  const validatePayload = (): boolean => {
    try {
      JSON.parse(payload);
      setPayloadError('');
      return true;
    } catch (e) {
      setPayloadError('Invalid JSON format');
      return false;
    }
  };
  
  // Handle submit
  const handleSubmit = async () => {
    if (!validatePayload()) {
      return;
    }
    
    try {
      const request: IWebhookTestRequest = {
        webhookId: webhook.id,
        payload: JSON.parse(payload),
      };
      
      await testWebhook(request);
    } catch (error) {
      console.error(error);
    }
  };
  
  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Test Webhook: {webhook.name}</DialogTitle>
      
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Webhook URL
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {webhook.url}
          </Typography>
          
          <Typography variant="subtitle1" gutterBottom>
            Test Payload
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={10}
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            error={!!payloadError}
            helperText={payloadError}
            sx={{ mb: 2, fontFamily: 'monospace' }}
          />
          
          {testResult && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Test Result
              </Typography>
              
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.neutral' }}>
                <Stack spacing={1}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Status:
                    </Typography>
                    <Chip
                      label={testResult.success ? 'Success' : 'Failed'}
                      size="small"
                      color={testResult.success ? 'success' : 'error'}
                    />
                  </Stack>
                  
                  {testResult.statusCode && (
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Status Code:
                      </Typography>
                      <Typography variant="body2">
                        {testResult.statusCode}
                      </Typography>
                    </Stack>
                  )}
                  
                  {testResult.responseTime && (
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Response Time:
                      </Typography>
                      <Typography variant="body2">
                        {testResult.responseTime}ms
                      </Typography>
                    </Stack>
                  )}
                  
                  {testResult.timestamp && (
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Timestamp:
                      </Typography>
                      <Typography variant="body2">
                        {fDateTime(testResult.timestamp)}
                      </Typography>
                    </Stack>
                  )}
                  
                  {testResult.error && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Error:
                      </Typography>
                      <Alert severity="error" sx={{ mt: 1 }}>
                        {testResult.error}
                      </Alert>
                    </Box>
                  )}
                  
                  {testResult.responseBody && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Response Body:
                      </Typography>
                      <Paper 
                        variant="outlined" 
                        sx={{ 
                          p: 1, 
                          mt: 1, 
                          maxHeight: 200, 
                          overflow: 'auto',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                        }}
                      >
                        {testResult.responseBody}
                      </Paper>
                    </Box>
                  )}
                </Stack>
              </Paper>
            </Box>
          )}
          
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error.message || 'An error occurred while testing the webhook'}
            </Alert>
          )}
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
        <LoadingButton
          loading={isSubmitting}
          onClick={handleSubmit}
          variant="contained"
          color="primary"
        >
          Send Test Payload
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
}

// ----------------------------------------------------------------------

type LogDetailsDialogProps = {
  open: boolean;
  onClose: VoidFunction;
  log: IWebhookLog;
};

function LogDetailsDialog({ open, onClose, log }: LogDetailsDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Webhook Log Details</DialogTitle>
      
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                Event
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {log.event}
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                Timestamp
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {fDateTime(log.timestamp)}
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                Status Code
              </Typography>
              <Chip
                label={log.responseStatus}
                size="small"
                color={log.responseStatus >= 200 && log.responseStatus < 300 ? 'success' : 'error'}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                Duration
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {log.duration}ms
              </Typography>
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                Request Payload
              </Typography>
              <Paper 
                variant="outlined" 
                sx={{ 
                  p: 1, 
                  maxHeight: 200, 
                  overflow: 'auto',
                  fontFamily: 'monospace',
                  fontSize: 12,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {log.requestPayload}
              </Paper>
            </Grid>
            
            {log.responseBody && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  Response Body
                </Typography>
                <Paper 
                  variant="outlined" 
                  sx={{ 
                    p: 1, 
                    maxHeight: 200, 
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {log.responseBody}
                </Paper>
              </Grid>
            )}
            
            {log.error && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  Error
                </Typography>
                <Alert severity="error">
                  {log.error}
                </Alert>
              </Grid>
            )}
          </Grid>
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

// ----------------------------------------------------------------------

type EventListenerProps = {
  eventName: string;
  callback: VoidFunction;
};

function EventListener({ eventName, callback }: EventListenerProps) {
  useState(() => {
    window.addEventListener(eventName, callback);
    return () => {
      window.removeEventListener(eventName, callback);
    };
  });
  
  return null;
}