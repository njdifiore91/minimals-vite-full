import { useState, useEffect, useCallback } from 'react';
import type { SxProps, Theme } from '@mui/material/styles';

import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';

import { Iconify } from 'src/components/iconify';
import type { IDocumentItem, IDocumentViewerConfig } from 'src/types/document';

// ----------------------------------------------------------------------

type Props = {
  /** Document being viewed */
  document: IDocumentItem;
  /** Current zoom level (percentage) */
  zoom: number;
  /** Current rotation angle (degrees) */
  rotation: number;
  /** Current page number */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Whether fullscreen mode is active */
  isFullscreen: boolean;
  /** Viewer configuration options */
  config?: Partial<IDocumentViewerConfig>;
  /** Callback when zoom level changes */
  onZoomChange: (newZoom: number) => void;
  /** Callback when rotation angle changes */
  onRotationChange: (newRotation: number) => void;
  /** Callback when page changes */
  onPageChange: (newPage: number) => void;
  /** Callback when fullscreen toggle is clicked */
  onFullscreenToggle: () => void;
  /** Callback when download is requested */
  onDownload?: () => void;
  /** Optional custom styling */
  sx?: SxProps<Theme>;
};

/**
 * DocumentControls component
 * 
 * Provides a toolbar of interactive controls for document navigation and manipulation.
 * Includes buttons for zooming in/out, rotating, downloading, navigating between pages,
 * and toggling fullscreen mode.
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
  const [showControls, setShowControls] = useState(true);

  // Default configuration values
  const {
    enableDownload = true,
    enableFullscreen = true,
    enableKeyboardShortcuts = true,
    showPageNavigation = true,
    maxZoom = 300,
  } = config || {};

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enableKeyboardShortcuts) return;

      // Prevent handling if user is typing in an input field
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA'
      ) {
        return;
      }

      switch (event.key) {
        case '+': // Zoom in
          event.preventDefault();
          onZoomChange(Math.min(zoom + 10, maxZoom));
          break;
        case '-': // Zoom out
          event.preventDefault();
          onZoomChange(Math.max(zoom - 10, 50));
          break;
        case 'r': // Rotate
          event.preventDefault();
          onRotationChange((rotation + 90) % 360);
          break;
        case 'f': // Fullscreen
          if (enableFullscreen) {
            event.preventDefault();
            onFullscreenToggle();
          }
          break;
        case 'ArrowRight': // Next page
          if (showPageNavigation && currentPage < totalPages) {
            event.preventDefault();
            onPageChange(currentPage + 1);
          }
          break;
        case 'ArrowLeft': // Previous page
          if (showPageNavigation && currentPage > 1) {
            event.preventDefault();
            onPageChange(currentPage - 1);
          }
          break;
        case 'd': // Download
          if (enableDownload && onDownload) {
            event.preventDefault();
            onDownload();
          }
          break;
        default:
          break;
      }
    },
    [zoom, rotation, currentPage, totalPages, isFullscreen, enableKeyboardShortcuts, enableDownload, enableFullscreen, showPageNavigation, maxZoom, onZoomChange, onRotationChange, onPageChange, onFullscreenToggle, onDownload]
  );

  // Register and unregister keyboard event listeners
  useEffect(() => {
    if (enableKeyboardShortcuts) {
      window.addEventListener('keydown', handleKeyDown);
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
    return undefined;
  }, [enableKeyboardShortcuts, handleKeyDown]);

  // Toggle controls visibility on mobile
  const toggleControls = () => {
    setShowControls((prev) => !prev);
  };

  return (
    <Box
      sx={[
        {
          display: 'flex',
          flexDirection: 'column',
          bgcolor: (theme) => theme.palette.background.neutral,
          borderRadius: 1,
          p: 1,
          boxShadow: (theme) => theme.customShadows.z8,
          transition: (theme) => theme.transitions.create(['width', 'height']),
          ...(isMobile && {
            position: 'fixed',
            bottom: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 9,
            width: showControls ? 'auto' : '40px',
            height: showControls ? 'auto' : '40px',
            overflow: 'hidden',
          }),
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {isMobile && (
        <IconButton
          size="small"
          onClick={toggleControls}
          sx={{
            position: 'absolute',
            top: 4,
            right: 4,
            ...(showControls ? {} : { position: 'static' }),
          }}
        >
          <Iconify
            icon={showControls ? 'eva:chevron-down-fill' : 'eva:chevron-up-fill'}
            width={20}
          />
        </IconButton>
      )}

      <Stack
        direction={isMobile ? 'column' : 'row'}
        spacing={1}
        alignItems="center"
        sx={{
          ...(isMobile && !showControls && { display: 'none' }),
        }}
      >
        {/* Zoom controls */}
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Tooltip title="Zoom out (-)">
            <IconButton
              size="small"
              onClick={() => onZoomChange(Math.max(zoom - 10, 50))}
              disabled={zoom <= 50}
            >
              <Iconify icon="eva:minus-circle-outline" width={20} />
            </IconButton>
          </Tooltip>

          <Typography
            variant="caption"
            sx={{ minWidth: 40, textAlign: 'center' }}
          >
            {zoom}%
          </Typography>

          <Tooltip title="Zoom in (+)">
            <IconButton
              size="small"
              onClick={() => onZoomChange(Math.min(zoom + 10, maxZoom))}
              disabled={zoom >= maxZoom}
            >
              <Iconify icon="eva:plus-circle-outline" width={20} />
            </IconButton>
          </Tooltip>
        </Stack>

        {/* Rotation control */}
        <Tooltip title="Rotate (r)">
          <IconButton size="small" onClick={() => onRotationChange((rotation + 90) % 360)}>
            <Iconify icon="eva:flip-outline" width={20} />
          </IconButton>
        </Tooltip>

        {/* Page navigation */}
        {showPageNavigation && totalPages > 1 && (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Tooltip title="Previous page (←)">
              <span>
                <IconButton
                  size="small"
                  onClick={() => onPageChange(Math.max(currentPage - 1, 1))}
                  disabled={currentPage <= 1}
                >
                  <Iconify icon="eva:arrow-ios-back-fill" width={20} />
                </IconButton>
              </span>
            </Tooltip>

            <Typography
              variant="caption"
              sx={{ minWidth: 60, textAlign: 'center' }}
            >
              {currentPage} / {totalPages}
            </Typography>

            <Tooltip title="Next page (→)">
              <span>
                <IconButton
                  size="small"
                  onClick={() => onPageChange(Math.min(currentPage + 1, totalPages))}
                  disabled={currentPage >= totalPages}
                >
                  <Iconify icon="eva:arrow-ios-forward-fill" width={20} />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>
        )}

        {/* Download button */}
        {enableDownload && onDownload && (
          <Tooltip title="Download document (d)">
            <IconButton
              size="small"
              onClick={onDownload}
              sx={{
                color: 'primary.main',
              }}
            >
              <Iconify icon="eva:cloud-download-fill" width={20} />
            </IconButton>
          </Tooltip>
        )}

        {/* Fullscreen toggle */}
        {enableFullscreen && (
          <Tooltip title={isFullscreen ? "Exit fullscreen (f)" : "Enter fullscreen (f)"}>
            <IconButton size="small" onClick={onFullscreenToggle}>
              <Iconify
                icon={isFullscreen ? "eva:collapse-outline" : "eva:expand-outline"}
                width={20}
              />
            </IconButton>
          </Tooltip>
        )}

        {/* Document info */}
        <Tooltip title={document.name}>
          <Typography
            variant="caption"
            noWrap
            sx={{
              maxWidth: 150,
              display: { xs: 'none', sm: 'block' },
              color: 'text.secondary',
            }}
          >
            {document.name}
          </Typography>
        </Tooltip>
      </Stack>

      {/* Keyboard shortcuts help */}
      {enableKeyboardShortcuts && showControls && (
        <Typography
          variant="caption"
          sx={{
            mt: 1,
            color: 'text.secondary',
            display: { xs: 'none', md: 'block' },
            fontSize: '0.7rem',
          }}
        >
          Shortcuts: +/- (zoom), r (rotate), f (fullscreen), ←/→ (pages), d (download)
        </Typography>
      )}
    </Box>
  );
}