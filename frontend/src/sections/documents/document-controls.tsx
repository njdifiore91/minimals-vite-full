import { useEffect, useCallback } from 'react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import useMediaQuery from '@mui/material/useMediaQuery';

import { Iconify } from 'src/components/iconify';

import type { IDocumentItem, IDocumentViewerConfig } from 'src/types/document';

// ----------------------------------------------------------------------

type Props = {
  /** Document being displayed */
  document: IDocumentItem;
  /** Current zoom level (percentage) */
  zoom: number;
  /** Current rotation angle (degrees) */
  rotation: number;
  /** Current page number */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Whether the viewer is in fullscreen mode */
  isFullscreen: boolean;
  /** Viewer configuration options */
  config?: Partial<Pick<IDocumentViewerConfig, 
    'enableDownload' | 
    'enableFullscreen' | 
    'enableKeyboardShortcuts' | 
    'showPageNavigation' | 
    'maxZoom'
  >>;
  /** Callback when zoom level changes */
  onZoomChange: (zoom: number) => void;
  /** Callback when rotation angle changes */
  onRotationChange: (rotation: number) => void;
  /** Callback when page number changes */
  onPageChange: (page: number) => void;
  /** Callback when fullscreen mode is toggled */
  onFullscreenToggle: () => void;
  /** Callback when document download is initiated */
  onDownload?: () => void;
  /** Optional custom styling */
  sx?: object;
};

/**
 * DocumentControls component
 * 
 * Provides a toolbar of interactive controls for document navigation and manipulation.
 * Includes buttons for zooming in/out, rotating, downloading, navigating between pages,
 * and toggling fullscreen mode. Designed to work seamlessly with the DocumentViewer.
 */
export function DocumentControls({
  document,
  zoom,
  rotation,
  currentPage,
  totalPages,
  isFullscreen,
  config,
  onZoomChange,
  onRotationChange,
  onPageChange,
  onFullscreenToggle,
  onDownload,
  sx,
}: Props) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  // Default configuration values
  const {
    enableDownload = true,
    enableFullscreen = true,
    enableKeyboardShortcuts = true,
    showPageNavigation = true,
    maxZoom = 300,
  } = config || {};
  
  // Zoom controls
  const handleZoomIn = () => {
    if (zoom < maxZoom) {
      onZoomChange(Math.min(zoom + 10, maxZoom));
    }
  };
  
  const handleZoomOut = () => {
    if (zoom > 50) {
      onZoomChange(Math.max(zoom - 10, 50));
    }
  };
  
  const handleZoomReset = () => {
    onZoomChange(100);
  };
  
  // Rotation controls
  const handleRotateClockwise = () => {
    onRotationChange((rotation + 90) % 360);
  };
  
  const handleRotateCounterClockwise = () => {
    onRotationChange((rotation - 90 + 360) % 360);
  };
  
  // Page navigation controls
  const handlePreviousPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };
  
  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };
  
  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enableKeyboardShortcuts) return;
    
    // Prevent default behavior for these keys
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '-', 'r'].includes(event.key)) {
      event.preventDefault();
    }
    
    switch (event.key) {
      // Page navigation
      case 'ArrowLeft':
      case 'p':
        handlePreviousPage();
        break;
      case 'ArrowRight':
      case 'n':
        handleNextPage();
        break;
      
      // Zoom controls
      case '+':
      case '=':
        handleZoomIn();
        break;
      case '-':
      case '_':
        handleZoomOut();
        break;
      case '0':
        handleZoomReset();
        break;
      
      // Rotation
      case 'r':
        if (event.shiftKey) {
          handleRotateCounterClockwise();
        } else {
          handleRotateClockwise();
        }
        break;
      
      // Fullscreen
      case 'f':
        if (enableFullscreen) {
          onFullscreenToggle();
        }
        break;
      
      // Download
      case 'd':
        if (enableDownload && onDownload) {
          onDownload();
        }
        break;
      
      default:
        break;
    }
  }, [
    enableKeyboardShortcuts,
    enableFullscreen,
    enableDownload,
    onDownload,
    handlePreviousPage,
    handleNextPage,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
    handleRotateClockwise,
    handleRotateCounterClockwise,
    onFullscreenToggle,
  ]);
  
  // Add and remove keyboard event listener
  useEffect(() => {
    if (enableKeyboardShortcuts) {
      window.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
      if (enableKeyboardShortcuts) {
        window.removeEventListener('keydown', handleKeyDown);
      }
    };
  }, [enableKeyboardShortcuts, handleKeyDown]);
  
  return (
    <Box
      sx={[
        {
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
          width: '100%',
          p: 1,
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {/* Left Controls Group */}
      <Stack direction="row" spacing={1} alignItems="center">
        {/* Zoom Controls */}
        <Tooltip title="Zoom Out (-)">
          <IconButton
            onClick={handleZoomOut}
            disabled={zoom <= 50}
            size="small"
            color="primary"
          >
            <Iconify icon="eva:minus-circle-outline" />
          </IconButton>
        </Tooltip>
        
        <Tooltip title="Reset Zoom (0)">
          <Box
            onClick={handleZoomReset}
            sx={{
              px: 1,
              py: 0.5,
              borderRadius: 1,
              cursor: 'pointer',
              typography: 'body2',
              fontWeight: 'medium',
              bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
              '&:hover': {
                bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)',
              },
            }}
          >
            {zoom}%
          </Box>
        </Tooltip>
        
        <Tooltip title="Zoom In (+)">
          <IconButton
            onClick={handleZoomIn}
            disabled={zoom >= maxZoom}
            size="small"
            color="primary"
          >
            <Iconify icon="eva:plus-circle-outline" />
          </IconButton>
        </Tooltip>
        
        <Divider orientation="vertical" flexItem sx={{ height: 24, mx: 1 }} />
        
        {/* Rotation Controls */}
        <Tooltip title="Rotate Counterclockwise (Shift+R)">
          <IconButton onClick={handleRotateCounterClockwise} size="small">
            <Iconify icon="eva:rotate-left-outline" />
          </IconButton>
        </Tooltip>
        
        <Tooltip title="Rotate Clockwise (R)">
          <IconButton onClick={handleRotateClockwise} size="small">
            <Iconify icon="eva:rotate-right-outline" />
          </IconButton>
        </Tooltip>
      </Stack>
      
      {/* Center Controls Group - Page Navigation */}
      {showPageNavigation && document.pageCount && document.pageCount > 1 && (
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          sx={{
            order: { xs: 3, sm: 2 },
            width: { xs: '100%', sm: 'auto' },
            justifyContent: { xs: 'center', sm: 'flex-start' },
            mt: { xs: 1, sm: 0 },
          }}
        >
          <Tooltip title="Previous Page (←)">
            <span>
              <IconButton
                onClick={handlePreviousPage}
                disabled={currentPage <= 1}
                size="small"
              >
                <Iconify icon="eva:arrow-ios-back-fill" />
              </IconButton>
            </span>
          </Tooltip>
          
          <Typography variant="body2">
            Page {currentPage} of {totalPages}
          </Typography>
          
          <Tooltip title="Next Page (→)">
            <span>
              <IconButton
                onClick={handleNextPage}
                disabled={currentPage >= totalPages}
                size="small"
              >
                <Iconify icon="eva:arrow-ios-forward-fill" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      )}
      
      {/* Right Controls Group */}
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{
          order: { xs: 2, sm: 3 },
          ml: { xs: 0, sm: 'auto' },
        }}
      >
        {/* Download Button */}
        {enableDownload && onDownload && (
          <Tooltip title="Download Document (D)">
            <IconButton onClick={onDownload} size="small" color="primary">
              <Iconify icon="eva:cloud-download-fill" />
            </IconButton>
          </Tooltip>
        )}
        
        {/* Fullscreen Toggle */}
        {enableFullscreen && (
          <Tooltip title={isFullscreen ? "Exit Fullscreen (F)" : "Enter Fullscreen (F)"}>
            <IconButton onClick={onFullscreenToggle} size="small">
              <Iconify
                icon={isFullscreen ? "eva:collapse-fill" : "eva:expand-fill"}
              />
            </IconButton>
          </Tooltip>
        )}
        
        {/* Keyboard Shortcuts Info */}
        {enableKeyboardShortcuts && !isMobile && (
          <Tooltip
            title={
              <Box sx={{ p: 1 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Keyboard Shortcuts
                </Typography>
                <Typography variant="caption" component="div">
                  ← / P: Previous page
                </Typography>
                <Typography variant="caption" component="div">
                  → / N: Next page
                </Typography>
                <Typography variant="caption" component="div">
                  + / =: Zoom in
                </Typography>
                <Typography variant="caption" component="div">
                  - / _: Zoom out
                </Typography>
                <Typography variant="caption" component="div">
                  0: Reset zoom
                </Typography>
                <Typography variant="caption" component="div">
                  R: Rotate clockwise
                </Typography>
                <Typography variant="caption" component="div">
                  Shift+R: Rotate counterclockwise
                </Typography>
                {enableFullscreen && (
                  <Typography variant="caption" component="div">
                    F: Toggle fullscreen
                  </Typography>
                )}
                {enableDownload && onDownload && (
                  <Typography variant="caption" component="div">
                    D: Download document
                  </Typography>
                )}
              </Box>
            }
            placement="bottom-end"
          >
            <IconButton size="small">
              <Iconify icon="eva:info-outline" />
            </IconButton>
          </Tooltip>
        )}
      </Stack>
    </Box>
  );
}