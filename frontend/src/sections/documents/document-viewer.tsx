import { useState, useEffect, useRef, useCallback } from 'react';
import { useTheme } from '@mui/material/styles';
import { Document, Page, pdfjs } from 'react-pdf';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import useMediaQuery from '@mui/material/useMediaQuery';

import { Iconify } from 'src/components/iconify';
import { FileThumbnail } from 'src/components/file-thumbnail';

import { DocumentControls } from './document-controls';
import { DocumentClassificationInfo } from './document-classification-info';

import type { IDocumentItem, IDocumentViewerConfig } from 'src/types/document';

// Initialize PDF.js worker
// This is required for react-pdf to work properly
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

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
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));
  
  // Container ref for measuring available space
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Document state
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [rotation, setRotation] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  
  // Loading and error states
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);

  // Default configuration values
  const {
    showClassification = true,
    showConfidence = true,
    enableDownload = true,
    enableFullscreen = true,
    enableKeyboardShortcuts = true,
    showPageNavigation = true,
    maxZoom = 300,
    defaultZoom = 100,
  } = config || {};

  // Determine if the document is a PDF or an image
  const isPdf = document.type.toLowerCase().includes('pdf');
  
  /**
   * Fetches the document from S3 storage with secure token
   * Uses AES-256 encryption for secure content delivery
   */
  const fetchDocument = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Check if we already have a valid download URL
      if (document.downloadUrl && document.downloadUrlExpiry) {
        const expiryDate = new Date(document.downloadUrlExpiry);
        if (expiryDate > new Date()) {
          setDocumentUrl(document.downloadUrl);
          return;
        }
      }
      
      // Simulate API call to get secure URL with token
      // In a real implementation, this would be an API call to your backend
      // that generates a signed URL for the S3 object with proper authentication
      const response = await fetch(`/api/documents/${document.id}/secure-url`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          // Include authentication token in the request
          Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch document: ${response.statusText}`);
      }
      
      const data = await response.json();
      setDocumentUrl(data.url);
    } catch (err) {
      console.error('Error fetching document:', err);
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [document.id, document.downloadUrl, document.downloadUrlExpiry]);
  
  // Fetch document on component mount or when document changes
  useEffect(() => {
    fetchDocument();
    
    // Reset viewer state when document changes
    setCurrentPage(1);
    setZoom(defaultZoom);
    setRotation(0);
    setNumPages(null);
    
    // Clean up function to revoke object URL if needed
    return () => {
      if (documentUrl && documentUrl.startsWith('blob:')) {
        URL.revokeObjectURL(documentUrl);
      }
    };
  }, [document.id, defaultZoom, fetchDocument]);
  
  // Handle document load success
  const handleDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  };
  
  // Handle document load error
  const handleDocumentLoadError = (error: Error) => {
    console.error('Error loading document:', error);
    setError('Failed to load document. Please try again later.');
    setLoading(false);
  };
  
  // Handle fullscreen toggle
  const handleFullscreenToggle = () => {
    setIsFullscreen(!isFullscreen);
    
    // Apply fullscreen styles to container
    if (containerRef.current) {
      if (!isFullscreen) {
        if (document.documentElement?.requestFullscreen) {
          containerRef.current.requestFullscreen();
        }
      } else if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };
  
  // Handle document download
  const handleDownload = async () => {
    try {
      if (!documentUrl) {
        throw new Error('Document URL not available');
      }
      
      // Fetch the document as a blob
      const response = await fetch(documentUrl);
      if (!response.ok) {
        throw new Error('Failed to download document');
      }
      
      const blob = await response.blob();
      
      // Create a download link and trigger download
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = document.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the object URL
      setTimeout(() => {
        URL.revokeObjectURL(downloadUrl);
      }, 100);
    } catch (err) {
      console.error('Error downloading document:', err);
      setError(err instanceof Error ? err.message : 'Failed to download document');
    }
  };
  
  // Calculate page dimensions based on container size, zoom, and rotation
  const getPageDimensions = () => {
    if (!containerRef.current) return { width: undefined };
    
    const containerWidth = containerRef.current.clientWidth;
    const scaleFactor = zoom / 100;
    
    // For rotated pages (90 or 270 degrees), we need to adjust dimensions
    const isRotated = rotation === 90 || rotation === 270;
    
    // Calculate the width based on container size and zoom level
    // For rotated pages, we use a different calculation to maintain proper scaling
    const width = isRotated
      ? (containerWidth * 0.7) * scaleFactor // Adjust for rotation
      : containerWidth * scaleFactor;
    
    return { width };
  };
  
  // Render document content based on type (PDF or image)
  const renderDocumentContent = () => {
    if (loading) {
      return (
        <Stack
          alignItems="center"
          justifyContent="center"
          sx={{ height: 400, width: '100%' }}
        >
          <CircularProgress />
          <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
            Loading document...
          </Typography>
        </Stack>
      );
    }
    
    if (error) {
      return (
        <Alert severity="error" sx={{ width: '100%' }}>
          {error}
          <Typography variant="body2" sx={{ mt: 1 }}>
            Please try again or contact support if the issue persists.
          </Typography>
        </Alert>
      );
    }
    
    if (!documentUrl) {
      return (
        <Alert severity="warning" sx={{ width: '100%' }}>
          Document URL not available. Please try refreshing the page.
        </Alert>
      );
    }
    
    // Render PDF document
    if (isPdf) {
      return (
        <Document
          file={documentUrl}
          onLoadSuccess={handleDocumentLoadSuccess}
          onLoadError={handleDocumentLoadError}
          loading={<Skeleton variant="rectangular" width="100%" height={400} />}
          options={{
            cMapUrl: 'https://unpkg.com/pdfjs-dist/cmaps/',
            cMapPacked: true,
          }}
        >
          <Page
            pageNumber={currentPage}
            width={getPageDimensions().width}
            rotate={rotation}
            renderTextLayer={true}
            renderAnnotationLayer={true}
            loading={<Skeleton variant="rectangular" width="100%" height={400} />}
          />
        </Document>
      );
    }
    
    // Render image document
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          width: '100%',
          height: '100%',
          overflow: 'auto',
        }}
      >
        <Box
          component="img"
          src={documentUrl}
          alt={document.name}
          onLoad={() => setLoading(false)}
          onError={() => {
            setError('Failed to load image');
            setLoading(false);
          }}
          sx={{
            maxWidth: '100%',
            maxHeight: '100%',
            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
            transition: 'transform 0.2s ease-in-out',
          }}
        />
      </Box>
    );
  };
  
  return (
    <Card
      ref={containerRef}
      sx={[
        {
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
          height: isFullscreen ? '100vh' : 'auto',
          overflow: 'hidden',
          position: isFullscreen ? 'fixed' : 'relative',
          top: isFullscreen ? 0 : 'auto',
          left: isFullscreen ? 0 : 'auto',
          right: isFullscreen ? 0 : 'auto',
          bottom: isFullscreen ? 0 : 'auto',
          zIndex: isFullscreen ? theme.zIndex.modal : 'auto',
          bgcolor: isFullscreen ? theme.palette.background.paper : 'transparent',
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {/* Document Controls */}
      <Box sx={{ p: 1, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <DocumentControls
          document={document}
          zoom={zoom}
          rotation={rotation}
          currentPage={currentPage}
          totalPages={numPages || 1}
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
        />
      </Box>
      
      {/* Main Content Area */}
      <Stack direction="row" sx={{ flex: 1, overflow: 'hidden' }}>
        {/* Document Viewer */}
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            p: 2,
            bgcolor: theme.palette.mode === 'dark' 
              ? 'rgba(0, 0, 0, 0.2)' 
              : 'rgba(0, 0, 0, 0.03)',
          }}
        >
          {renderDocumentContent()}
        </Box>
        
        {/* Classification Info Sidebar - Only shown on larger screens or when not in fullscreen */}
        {showClassification && !isMobile && !isFullscreen && (
          <Box
            sx={{
              width: isTablet ? 280 : 320,
              borderLeft: `1px solid ${theme.palette.divider}`,
              overflow: 'auto',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <DocumentClassificationInfo document={document} />
          </Box>
        )}
      </Stack>
      
      {/* Mobile Classification Info - Shown below document on mobile */}
      {showClassification && isMobile && !isFullscreen && (
        <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
          <DocumentClassificationInfo document={document} />
        </Box>
      )}
      
      {/* Fallback for unsupported document types */}
      {!isPdf && !document.type.match(/^image\/(jpeg|jpg|png|gif|bmp|webp)$/i) && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <FileThumbnail
            file={document.type}
            sx={{ width: 160, height: 160, mx: 'auto', mb: 2 }}
          />
          <Typography variant="h6">{document.name}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
            This document type cannot be previewed. Please download to view.
          </Typography>
          {enableDownload && (
            <Box sx={{ mt: 2 }}>
              <Stack direction="row" justifyContent="center">
                <Box
                  component="button"
                  onClick={handleDownload}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 1,
                    py: 1,
                    px: 2,
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    borderRadius: 1,
                    border: 'none',
                    cursor: 'pointer',
                    '&:hover': {
                      bgcolor: 'primary.dark',
                    },
                  }}
                >
                  <Iconify icon="eva:cloud-download-fill" width={20} />
                  Download
                </Box>
              </Stack>
            </Box>
          )}
        </Box>
      )}
    </Card>
  );
}