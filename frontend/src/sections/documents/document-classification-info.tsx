import { useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Collapse from '@mui/material/Collapse';
import LinearProgress from '@mui/material/LinearProgress';
import Tooltip from '@mui/material/Tooltip';
import Chip from '@mui/material/Chip';

import Iconify from 'src/components/iconify';

import type { IDocumentItem, IExtractedField, IDocumentType } from 'src/types/document';

// ----------------------------------------------------------------------

type Props = {
  /** Document with classification metadata to display */
  document: IDocumentItem;
  /** Optional custom styling */
  sx?: object;
};

/**
 * DocumentClassificationInfo component
 * 
 * Displays AI-generated document classification metadata including document type,
 * confidence scores, and extracted field data. Renders a collapsible panel showing
 * the document's classification category, confidence percentage with color-coded
 * indicators, and a detailed list of extracted fields with their respective
 * confidence metrics.
 */
export function DocumentClassificationInfo({ document, sx }: Props) {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(true);

  const { classification, extractedFields = [] } = document;
  const { primaryType, confidence, alternativeTypes = [] } = classification;

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  // Get color based on confidence score
  const getConfidenceColor = (score: number) => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 75) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  // Format document type for display
  const formatDocumentType = (type: IDocumentType) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Card sx={{ ...sx }}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ p: 2, cursor: 'pointer' }}
        onClick={handleToggle}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <Iconify icon="mdi:file-document-outline" width={24} />
          <Typography variant="subtitle1">Document Classification</Typography>
        </Stack>
        <IconButton size="small">
          <Iconify
            icon={expanded ? 'eva:arrow-ios-upward-fill' : 'eva:arrow-ios-downward-fill'}
            width={16}
          />
        </IconButton>
      </Stack>

      <Collapse in={expanded} unmountOnExit>
        <Divider sx={{ borderStyle: 'dashed' }} />

        <Stack spacing={2.5} sx={{ p: 2.5 }}>
          {/* Primary Classification */}
          <Stack spacing={1.5}>
            <Typography variant="subtitle2">Document Type</Typography>
            <Stack direction="row" alignItems="center" spacing={2}>
              <Chip
                label={formatDocumentType(primaryType)}
                color="primary"
                variant="soft"
                size="medium"
              />
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="body2">Confidence:</Typography>
                <Typography
                  variant="subtitle2"
                  sx={{ color: getConfidenceColor(confidence.score) }}
                >
                  {confidence.score}%
                </Typography>
              </Stack>
            </Stack>

            {/* Confidence Progress Bar */}
            <Box sx={{ width: '100%', mt: 1 }}>
              <LinearProgress
                variant="determinate"
                value={confidence.score}
                sx={{
                  height: 8,
                  borderRadius: 1,
                  bgcolor: theme.palette.background.neutral,
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 1,
                    bgcolor: getConfidenceColor(confidence.score),
                  },
                }}
              />
            </Box>

            {/* Review Status */}
            {confidence.requiresReview && (
              <Chip
                label="Requires Human Review"
                color="warning"
                variant="soft"
                size="small"
                icon={<Iconify icon="mdi:eye-check-outline" />}
              />
            )}

            {/* Reviewer Notes if available */}
            {confidence.reviewerNotes && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Reviewer Notes:
                </Typography>
                <Typography variant="body2">{confidence.reviewerNotes}</Typography>
              </Box>
            )}
          </Stack>

          {/* Alternative Classifications if available */}
          {alternativeTypes.length > 0 && (
            <Stack spacing={1.5}>
              <Typography variant="subtitle2">Alternative Classifications</Typography>
              <Stack spacing={1}>
                {alternativeTypes.map((alt) => (
                  <Stack
                    key={alt.type}
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{
                      py: 1,
                      px: 1.5,
                      borderRadius: 1,
                      bgcolor: theme.palette.background.neutral,
                    }}
                  >
                    <Typography variant="body2">{formatDocumentType(alt.type)}</Typography>
                    <Typography
                      variant="subtitle2"
                      sx={{ color: getConfidenceColor(alt.score) }}
                    >
                      {alt.score}%
                    </Typography>
                  </Stack>
                ))}
              </Stack>
            </Stack>
          )}

          {/* Extracted Fields */}
          {extractedFields.length > 0 && (
            <Stack spacing={1.5}>
              <Typography variant="subtitle2">Extracted Fields</Typography>
              <Divider sx={{ borderStyle: 'dashed' }} />

              <Stack spacing={1.5}>
                {extractedFields.map((field) => (
                  <ExtractedFieldItem key={field.name} field={field} />
                ))}
              </Stack>
            </Stack>
          )}

          {/* Classification Metadata */}
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ pt: 1 }}
          >
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Model Version: {classification.modelVersion}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Classified: {new Date(classification.classifiedAt).toLocaleString()}
            </Typography>
          </Stack>
        </Stack>
      </Collapse>
    </Card>
  );
}

// ----------------------------------------------------------------------

type ExtractedFieldItemProps = {
  /** Extracted field data with confidence metrics */
  field: IExtractedField;
};

/**
 * ExtractedFieldItem component
 * 
 * Displays a single field extracted from a document by the OCR service,
 * including the field name, value, confidence score, and verification status.
 * Uses color-coded indicators to show confidence levels.
 */
function ExtractedFieldItem({ field }: ExtractedFieldItemProps) {
  const theme = useTheme();

  // Get color based on confidence score
  const getConfidenceColor = (score: number) => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 75) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  // Format field name for display
  const formatFieldName = (name: string) => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Stack spacing={1}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ width: '100%' }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {formatFieldName(field.name)}
          </Typography>
          {field.requiresVerification && (
            <Tooltip title="Requires verification">
              <Iconify
                icon="mdi:alert-circle-outline"
                sx={{ color: theme.palette.warning.main, width: 16, height: 16 }}
              />
            </Tooltip>
          )}
          {field.verified && (
            <Tooltip title="Verified">
              <Iconify
                icon="mdi:check-circle-outline"
                sx={{ color: theme.palette.success.main, width: 16, height: 16 }}
              />
            </Tooltip>
          )}
        </Stack>
        <Typography
          variant="caption"
          sx={{ color: getConfidenceColor(field.confidence) }}
        >
          {field.confidence}%
        </Typography>
      </Stack>

      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        sx={{
          p: 1.5,
          borderRadius: 1,
          bgcolor: theme.palette.background.neutral,
        }}
      >
        <Typography variant="body2" sx={{ wordBreak: 'break-word', flex: 1 }}>
          {field.value}
        </Typography>
        {field.pageNumber && (
          <Tooltip title={`Found on page ${field.pageNumber}`}>
            <Chip
              label={`P${field.pageNumber}`}
              size="small"
              variant="soft"
              color="info"
            />
          </Tooltip>
        )}
      </Stack>

      {/* Confidence indicator */}
      <Box sx={{ width: '100%', mt: 0.5 }}>
        <LinearProgress
          variant="determinate"
          value={field.confidence}
          sx={{
            height: 4,
            borderRadius: 0.5,
            bgcolor: theme.palette.background.neutral,
            '& .MuiLinearProgress-bar': {
              borderRadius: 0.5,
              bgcolor: getConfidenceColor(field.confidence),
            },
          }}
        />
      </Box>
    </Stack>
  );
}