import { useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import LinearProgress from '@mui/material/LinearProgress';
import Collapse from '@mui/material/Collapse';
import Tooltip from '@mui/material/Tooltip';
import Chip from '@mui/material/Chip';

import { Iconify } from 'src/components/iconify';
import { fDateTime } from 'src/utils/format-time';

import type { IDocumentItem, IDocumentType, IExtractedField } from 'src/types/document';

// ----------------------------------------------------------------------

type Props = {
  /** Document with classification metadata */
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
 * indicators, and a detailed list of extracted fields with their respective confidence metrics.
 */
export function DocumentClassificationInfo({ document, sx }: Props) {
  const theme = useTheme();
  
  // State for collapsible sections
  const [showClassification, setShowClassification] = useState<boolean>(true);
  const [showExtractedFields, setShowExtractedFields] = useState<boolean>(true);
  
  // Get classification data from document
  const { classification, extractedFields } = document;
  
  // Helper function to get color based on confidence score
  const getConfidenceColor = (score: number) => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 75) return theme.palette.warning.main;
    return theme.palette.error.main;
  };
  
  // Helper function to format document type for display
  const formatDocumentType = (type: IDocumentType) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };
  
  // Helper function to group extracted fields by page
  const groupFieldsByPage = (fields: IExtractedField[] = []) => {
    const grouped: Record<number, IExtractedField[]> = {};
    
    fields.forEach((field) => {
      if (!grouped[field.pageNumber]) {
        grouped[field.pageNumber] = [];
      }
      grouped[field.pageNumber].push(field);
    });
    
    return Object.entries(grouped).map(([page, fields]) => ({
      page: parseInt(page, 10),
      fields,
    }));
  };
  
  // Group extracted fields by page
  const groupedFields = groupFieldsByPage(extractedFields);
  
  return (
    <Box
      sx={[
        {
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {/* Classification Section Header */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Typography variant="subtitle1">Document Classification</Typography>
        <IconButton
          size="small"
          onClick={() => setShowClassification(!showClassification)}
        >
          <Iconify
            icon={showClassification ? 'eva:chevron-up-fill' : 'eva:chevron-down-fill'}
            width={20}
          />
        </IconButton>
      </Box>
      
      {/* Classification Details */}
      <Collapse in={showClassification}>
        <Stack spacing={2} sx={{ p: 2 }}>
          {/* Document Type */}
          <Stack spacing={1}>
            <Typography variant="subtitle2">Document Type</Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                label={formatDocumentType(classification.primaryType)}
                color="primary"
                size="small"
              />
              
              {/* Show alternative types if available */}
              {classification.alternativeTypes?.slice(0, 2).map((alt) => (
                <Tooltip 
                  key={alt.type} 
                  title={`Alternative classification: ${alt.score}% confidence`}
                >
                  <Chip
                    label={formatDocumentType(alt.type)}
                    variant="outlined"
                    size="small"
                    sx={{ opacity: 0.7 }}
                  />
                </Tooltip>
              ))}
            </Stack>
          </Stack>
          
          {/* Confidence Score */}
          <Stack spacing={1}>
            <Stack direction="row" alignItems="center" justifyContent="space-between">
              <Typography variant="subtitle2">Classification Confidence</Typography>
              <Typography
                variant="subtitle2"
                sx={{ color: getConfidenceColor(classification.confidence.score) }}
              >
                {classification.confidence.score}%
              </Typography>
            </Stack>
            
            <LinearProgress
              variant="determinate"
              value={classification.confidence.score}
              sx={{
                height: 8,
                borderRadius: 1,
                bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 1,
                  bgcolor: getConfidenceColor(classification.confidence.score),
                },
              }}
            />
            
            {/* Review Status */}
            {classification.confidence.requiresReview && (
              <Box
                sx={{
                  mt: 1,
                  p: 1,
                  borderRadius: 1,
                  bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 193, 7, 0.16)' : 'rgba(255, 193, 7, 0.08)',
                  border: `1px solid ${theme.palette.warning.main}`,
                }}
              >
                <Stack direction="row" spacing={1} alignItems="center">
                  <Iconify icon="eva:alert-triangle-fill" color={theme.palette.warning.main} width={20} />
                  <Typography variant="caption">
                    This document requires human review due to low confidence score.
                  </Typography>
                </Stack>
              </Box>
            )}
            
            {/* Review Information */}
            {classification.confidence.reviewerId && classification.confidence.reviewedAt && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Reviewed by {classification.confidence.reviewerId} on{' '}
                  {fDateTime(classification.confidence.reviewedAt)}
                </Typography>
                
                {classification.confidence.reviewerNotes && (
                  <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'text.secondary' }}>
                    Note: {classification.confidence.reviewerNotes}
                  </Typography>
                )}
              </Box>
            )}
          </Stack>
          
          {/* Classification Metadata */}
          <Stack spacing={1}>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Classified using model version {classification.modelVersion} on{' '}
              {fDateTime(classification.classifiedAt)}
            </Typography>
          </Stack>
        </Stack>
      </Collapse>
      
      {/* Divider */}
      <Divider />
      
      {/* Extracted Fields Section Header */}
      {extractedFields && extractedFields.length > 0 && (
        <>
          <Box
            sx={{
              p: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Typography variant="subtitle1">Extracted Fields</Typography>
            <IconButton
              size="small"
              onClick={() => setShowExtractedFields(!showExtractedFields)}
            >
              <Iconify
                icon={showExtractedFields ? 'eva:chevron-up-fill' : 'eva:chevron-down-fill'}
                width={20}
              />
            </IconButton>
          </Box>
          
          {/* Extracted Fields Details */}
          <Collapse in={showExtractedFields}>
            <Box sx={{ p: 2, overflow: 'auto', flexGrow: 1 }}>
              {groupedFields.map(({ page, fields }) => (
                <Box key={`page-${page}`} sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Page {page}
                  </Typography>
                  
                  <Stack spacing={2}>
                    {fields.map((field) => (
                      <Card
                        key={`${field.name}-${field.pageNumber}`}
                        sx={{
                          p: 1.5,
                          boxShadow: theme.customShadows.z1,
                          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.02)',
                          ...(field.requiresVerification && {
                            border: `1px solid ${theme.palette.warning.main}`,
                          }),
                        }}
                      >
                        <Stack spacing={1}>
                          {/* Field Name and Confidence */}
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="subtitle2">{field.name}</Typography>
                            <Tooltip title={`Confidence: ${field.confidence}%`}>
                              <Box
                                sx={{
                                  width: 12,
                                  height: 12,
                                  borderRadius: '50%',
                                  bgcolor: getConfidenceColor(field.confidence),
                                }}
                              />
                            </Tooltip>
                          </Stack>
                          
                          {/* Field Value */}
                          <Typography variant="body2">{field.value}</Typography>
                          
                          {/* Verification Status */}
                          {field.requiresVerification && !field.verified && (
                            <Box
                              sx={{
                                mt: 0.5,
                                p: 0.5,
                                borderRadius: 0.5,
                                bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 193, 7, 0.16)' : 'rgba(255, 193, 7, 0.08)',
                              }}
                            >
                              <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <Iconify icon="eva:alert-triangle-fill" color={theme.palette.warning.main} width={16} />
                                Requires verification
                              </Typography>
                            </Box>
                          )}
                          
                          {/* Verification Information */}
                          {field.verified && field.verifiedAt && field.verifierId && (
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              Verified by {field.verifierId} on {fDateTime(field.verifiedAt)}
                            </Typography>
                          )}
                        </Stack>
                      </Card>
                    ))}
                  </Stack>
                </Box>
              ))}
              
              {/* No Fields Message */}
              {groupedFields.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    No fields were extracted from this document.
                  </Typography>
                </Box>
              )}
            </Box>
          </Collapse>
        </>
      )}
      
      {/* No Classification Message */}
      {(!classification || !extractedFields || extractedFields.length === 0) && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Iconify
            icon="eva:file-text-outline"
            width={40}
            height={40}
            sx={{ color: 'text.secondary', mb: 2 }}
          />
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {!classification
              ? 'This document has not been classified yet.'
              : 'No data has been extracted from this document yet.'}
          </Typography>
        </Box>
      )}
    </Box>
  );
}