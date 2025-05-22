import { useState, useEffect, useRef, useCallback } from 'react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import useMediaQuery from '@mui/material/useMediaQuery';
import { Viewer, Worker, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';

// Import styles
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';

// Import components
import { Iconify } from 'src/components/iconify';
import { DocumentControls } from './document-controls';
import { DocumentClassificationInfo } from './document-classification-info';

// Import types
import type { IDocumentItem, IDocumentViewerConfig } from 'src/types/document';

// Import services
import { getSecureDocumentUrl } from 'src/services/document';

// ----------------------------------------------------------------------

type Props = {
  /** Document to display */
  document: IDocumentItem;
  /** Optional viewer configuration */
  config?: Partial<IDocumentViewerConfig>;
  /** Optional custom styling */
  sx?: object;
};

/**
 * DocumentViewer component
 * 
 * Renders interactive document previews (PDFs and images) with classification metadata display.
 * Integrates with S3-compatible storage to securely fetch documents using AES-256 encryption,
 * provides zoom/pagination controls, and displays AI-generated classification data with confidence scores.
 */
export function DocumentViewer({ document, config, sx }: Props) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const viewerContainerRef = useRef<HTMLDivElement>(null);
  
  // State for document viewing
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(100);
  const [rotation, setRotation] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  
  // Default configuration values
  const {
    showClassification = true,
    showConfidence = true,
    showExtractedFields = true,
    enableDownload = true,
    enablePrint = false,
    enableSharing = false,
    enableAnnotation = false,
    maxZoom = 300,
    defaultZoom = 100,
    showThumbnails = true,
    enableFullscreen = true,
    enableKeyboardShortcuts = true,
    showPageNavigation = true,
    onError,
    onLoad,
    onDownload,
  } = config || {};
  
  // Set up PDF viewer plugins
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: (defaultTabs) => [
      // Only show thumbnails tab if enabled
      ...(showThumbnails ? [defaultTabs[0]] : []),
    ],
  });
  
  // Handle fullscreen toggle
  const handleFullscreenToggle = useCallback(() => {
    if (!viewerContainerRef.current) return;
    
    if (!isFullscreen) {
      if (viewerContainerRef.current.requestFullscreen) {
        viewerContainerRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);
  
  // Handle document download
  const handleDownload = useCallback(async () => {
    if (!documentUrl) return;
    
    try {
      // If custom download handler is provided, use it
      if (onDownload) {
        onDownload();
        return;
      }
      
      // Otherwise use default download behavior
      const link = document.createElement('a');
      link.href = documentUrl;
      link.download = document.name || 'document';
      link.target = '_blank';
      link.click();
    } catch (err) {
      console.error('Error downloading document:', err);
      setError('Failed to download document. Please try again.');
    }
  }, [documentUrl, document.name, onDownload]);
  
  // Listen for fullscreen change events
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);
  
  // Fetch document URL securely
  useEffect(() => {
    const fetchDocument = async () => {
      if (!document || !document.storagePath) {
        setError('Document information is missing or invalid.');
        setIsLoading(false);
        return;
      }
      
      try {
        setIsLoading(true);
        setError(null);
        
        // Get secure URL with AES-256 encryption from S3-compatible storage
        const url = await getSecureDocumentUrl(document.storagePath, document.id);
        setDocumentUrl(url);
        setIsLoading(false);
        
        // Call onLoad callback if provided
        if (onLoad) {
          onLoad();
        }
      } catch (err) {
        console.error('Error loading document:', err);
        setError('Failed to load document. Please try again later.');
        setIsLoading(false);
        
        // Call onError callback if provided
        if (onError && err instanceof Error) {
          onError(err);
        }
      }
    };
    
    fetchDocument();
  }, [document, onError, onLoad]);
  
  // Determine if the document is a PDF or an image
  const isPdf = document.type?.toLowerCase().includes('pdf');
  
  // Render loading state
  if (isLoading) {
    return (
      <Card
        sx={[
          {
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: 400,
            width: '100%',
            p: 3,
          },
          ...(Array.isArray(sx) ? sx : [sx]),
        ]}
      >
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          Loading document...
        </Typography>
      </Card>
    );
  }
  
  // Render error state
  if (error) {
    return (
      <Card
        sx={[
          {
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: 400,
            width: '100%',
            p: 3,
          },
          ...(Array.isArray(sx) ? sx : [sx]),
        ]}
      >
        <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
          {error}
        </Alert>
        <Iconify icon="eva:file-text-outline" width={64} height={64} sx={{ color: 'text.secondary', mb: 2 }} />
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Unable to display document. Please try again later or contact support.
        </Typography>
      </Card>
    );
  }
  
  // Render document not found state
  if (!documentUrl) {
    return (
      <Card
        sx={[
          {
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: 400,
            width: '100%',
            p: 3,
          },
          ...(Array.isArray(sx) ? sx : [sx]),
        ]}
      >
        <Iconify icon="eva:file-text-outline" width={64} height={64} sx={{ color: 'text.secondary', mb: 2 }} />
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Document not found or has been removed.
        </Typography>
      </Card>
    );
  }
  
  return (
    <Stack
      spacing={2}
      sx={[
        {
          width: '100%',
          height: '100%',
          minHeight: 400,
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {/* Document Viewer Container */}
      <Card
        ref={viewerContainerRef}
        sx={{
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
          height: isFullscreen ? '100vh' : 500,
          overflow: 'hidden',
          position: 'relative',
          ...(isFullscreen && {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: theme.zIndex.modal + 1,
            borderRadius: 0,
          }),
        }}
      >
        {/* Document Controls */}
        <DocumentControls
          document={document}
          zoom={zoom}
          rotation={rotation}
          currentPage={currentPage}
          totalPages={document.pageCount || 1}
          isFullscreen={isFullscreen}
          config={{
            enableDownload,
            enableFullscreen,
            enableKeyboardShortcuts,
            showPageNavigation,
            maxZoom,
          }}
          onZoomChange={setZoom}
          onRotationChange={setRotation}
          onPageChange={setCurrentPage}
          onFullscreenToggle={handleFullscreenToggle}
          onDownload={enableDownload ? handleDownload : undefined}
          sx={{
            borderBottom: `1px solid ${theme.palette.divider}`,
          }}
        />
        
        {/* Document Content */}
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            flexGrow: 1,
            overflow: 'hidden',
          }}
        >
          {/* Document Viewer */}
          <Box
            sx={{
              flexGrow: 1,
              height: '100%',
              overflow: 'auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              p: 2,
              transform: `rotate(${rotation}deg)`,
              transition: 'transform 0.3s ease',
            }}
          >
            {isPdf ? (
              // PDF Viewer
              <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">
                <Viewer
                  fileUrl={documentUrl}
                  defaultScale={zoom / 100}
                  plugins={[defaultLayoutPluginInstance]}
                  onPageChange={(e) => setCurrentPage(e.currentPage)}
                  renderError={(error) => (
                    <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
                      {error.message || 'Failed to load PDF document'}
                    </Alert>
                  )}
                />
              </Worker>
            ) : (
              // Image Viewer
              <Box
                component="img"
                src={documentUrl}
                alt={document.name || 'Document'}
                sx={{
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                  transform: `scale(${zoom / 100})`,
                  transition: 'transform 0.3s ease',
                }}
                onError={() => {
                  setError('Failed to load image. The format may be unsupported or the file may be corrupted.');
                }}
              />
            )}
          </Box>
          
          {/* Classification Info Panel - Only show if enabled and not in mobile view */}
          {showClassification && !isMobile && (
            <Box
              sx={{
                width: { xs: '100%', md: 320 },
                height: { xs: 'auto', md: '100%' },
                borderLeft: { xs: 'none', md: `1px solid ${theme.palette.divider}` },
                borderTop: { xs: `1px solid ${theme.palette.divider}`, md: 'none' },
                overflow: 'auto',
              }}
            >
              <DocumentClassificationInfo document={document} />
            </Box>
          )}
        </Box>
      </Card>
      
      {/* Classification Info Panel - Only show in mobile view */}
      {showClassification && isMobile && (
        <Card sx={{ width: '100%', overflow: 'hidden' }}>
          <DocumentClassificationInfo document={document} />
        </Card>
      )}
    </Stack>
  );
}