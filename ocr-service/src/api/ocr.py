from fastapi import APIRouter, Path, Query, Body, HTTPException, Depends, status
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging

# Import services
from services import OCRService, StorageService, ConfidenceService
from services.ocr_service import OCRProcessingError

# Import types
from types.extraction import ExtractedData, ConfidenceScore, ExtractedField
from types.models import OCRModelType
from types.errors import ServiceError

# Create logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Request/Response models
class OCRProcessRequest(BaseModel):
    force_reprocess: bool = Field(False, description="Force reprocessing even if results already exist")
    model_type: Optional[OCRModelType] = Field(None, description="Specific OCR model to use for processing")
    confidence_threshold: Optional[float] = Field(None, description="Custom confidence threshold for this processing")


class BatchProcessRequest(BaseModel):
    document_ids: List[str] = Field(..., description="List of document IDs to process")
    force_reprocess: bool = Field(False, description="Force reprocessing even if results already exist")
    model_type: Optional[OCRModelType] = Field(None, description="Specific OCR model to use for processing")
    confidence_threshold: Optional[float] = Field(None, description="Custom confidence threshold for this processing")


class BatchProcessResponse(BaseModel):
    processed: List[str] = Field([], description="Successfully queued document IDs")
    failed: Dict[str, str] = Field({}, description="Failed document IDs with error messages")
    total: int = Field(0, description="Total number of documents in request")
    success_count: int = Field(0, description="Number of successfully queued documents")
    failure_count: int = Field(0, description="Number of failed documents")


class ConfidenceThresholdUpdate(BaseModel):
    global_threshold: Optional[float] = Field(None, description="Global confidence threshold (0.0-1.0)")
    document_type_thresholds: Optional[Dict[str, float]] = Field(None, description="Document type specific thresholds")
    field_type_thresholds: Optional[Dict[str, float]] = Field(None, description="Field type specific thresholds")


class ConfidenceThresholdResponse(BaseModel):
    global_threshold: float = Field(..., description="Global confidence threshold (0.0-1.0)")
    document_type_thresholds: Dict[str, float] = Field(..., description="Document type specific thresholds")
    field_type_thresholds: Dict[str, float] = Field(..., description="Field type specific thresholds")


# Helper functions
def get_ocr_service():
    """Dependency to get OCR service instance"""
    return OCRService()


def get_storage_service():
    """Dependency to get Storage service instance"""
    return StorageService()


def get_confidence_service():
    """Dependency to get Confidence service instance"""
    return ConfidenceService()


@router.get(
    "/{document_id}",
    response_model=ExtractedData,
    summary="Get OCR results for a document",
    description="Retrieves the OCR extraction results for a specific document, including all extracted fields with confidence scores.",
    responses={
        200: {"description": "OCR results retrieved successfully"},
        404: {"description": "Document not found or OCR results not available"},
        500: {"description": "Internal server error"}
    }
)
async def get_ocr_results(
    document_id: str = Path(..., description="Unique identifier of the document"),
    include_low_confidence: bool = Query(True, description="Include fields below confidence threshold"),
    ocr_service: OCRService = Depends(get_ocr_service),
    storage_service: StorageService = Depends(get_storage_service)
) -> ExtractedData:
    """Retrieve OCR results for a specific document.
    
    Args:
        document_id: Unique identifier of the document
        include_low_confidence: Whether to include fields below confidence threshold
        ocr_service: OCR service instance
        storage_service: Storage service instance
        
    Returns:
        ExtractedData: The OCR extraction results with confidence scores
        
    Raises:
        HTTPException: If document not found or OCR results not available
    """
    try:
        logger.info(f"Retrieving OCR results for document {document_id}")
        
        # Check if document exists
        if not storage_service.document_exists(document_id):
            logger.warning(f"Document {document_id} not found in storage")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Get OCR results
        ocr_results = ocr_service.get_ocr_results(document_id, include_low_confidence)
        
        if not ocr_results:
            logger.warning(f"OCR results not found for document {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OCR results not available for document {document_id}"
            )
        
        logger.info(f"Successfully retrieved OCR results for document {document_id}")
        return ocr_results
        
    except ServiceError as e:
        logger.error(f"Service error retrieving OCR results for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving OCR results for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving OCR results"
        )


@router.post(
    "/{document_id}/process",
    response_model=Dict[str, Any],
    summary="Process document with OCR",
    description="Manually triggers OCR processing for a specific document. This endpoint can be used to reprocess a document or process it with different parameters.",
    responses={
        202: {"description": "OCR processing initiated successfully"},
        404: {"description": "Document not found"},
        500: {"description": "Internal server error"}
    }
)
async def process_document(
    document_id: str = Path(..., description="Unique identifier of the document"),
    request: OCRProcessRequest = Body(..., description="Processing parameters"),
    ocr_service: OCRService = Depends(get_ocr_service),
    storage_service: StorageService = Depends(get_storage_service)
) -> Dict[str, Any]:
    """Manually trigger OCR processing for a specific document.
    
    Args:
        document_id: Unique identifier of the document
        request: Processing parameters
        ocr_service: OCR service instance
        storage_service: Storage service instance
        
    Returns:
        Dict: Processing status information
        
    Raises:
        HTTPException: If document not found or processing fails
    """
    try:
        logger.info(f"Manual OCR processing requested for document {document_id}")
        
        # Check if document exists
        if not storage_service.document_exists(document_id):
            logger.warning(f"Document {document_id} not found in storage")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Check if already processed and not forcing reprocess
        if ocr_service.has_ocr_results(document_id) and not request.force_reprocess:
            logger.info(f"Document {document_id} already processed, returning existing results")
            return {
                "status": "already_processed",
                "message": "Document already processed. Use force_reprocess=true to reprocess.",
                "document_id": document_id
            }
        
        # Process document
        processing_id = ocr_service.process_document(
            document_id,
            model_type=request.model_type,
            confidence_threshold=request.confidence_threshold
        )
        
        logger.info(f"OCR processing initiated for document {document_id} with processing ID {processing_id}")
        return {
            "status": "processing",
            "message": "OCR processing initiated",
            "document_id": document_id,
            "processing_id": processing_id
        }
        
    except OCRProcessingError as e:
        logger.error(f"OCR processing error for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Service error processing document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error processing document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the document"
        )


@router.post(
    "/batch",
    response_model=BatchProcessResponse,
    summary="Batch process multiple documents",
    description="Initiates OCR processing for multiple documents in a single request. This endpoint is useful for bulk processing operations.",
    responses={
        202: {"description": "Batch processing initiated"},
        500: {"description": "Internal server error"}
    }
)
async def batch_process(
    request: BatchProcessRequest = Body(..., description="Batch processing parameters"),
    ocr_service: OCRService = Depends(get_ocr_service),
    storage_service: StorageService = Depends(get_storage_service)
) -> BatchProcessResponse:
    """Process multiple documents in a batch operation.
    
    Args:
        request: Batch processing parameters including document IDs
        ocr_service: OCR service instance
        storage_service: Storage service instance
        
    Returns:
        BatchProcessResponse: Results of the batch processing request
        
    Raises:
        HTTPException: If batch processing fails
    """
    try:
        logger.info(f"Batch OCR processing requested for {len(request.document_ids)} documents")
        
        response = BatchProcessResponse(
            total=len(request.document_ids)
        )
        
        for doc_id in request.document_ids:
            try:
                # Check if document exists
                if not storage_service.document_exists(doc_id):
                    logger.warning(f"Document {doc_id} not found in storage")
                    response.failed[doc_id] = "Document not found"
                    continue
                
                # Check if already processed and not forcing reprocess
                if ocr_service.has_ocr_results(doc_id) and not request.force_reprocess:
                    logger.info(f"Document {doc_id} already processed, skipping")
                    response.failed[doc_id] = "Already processed (use force_reprocess=true to reprocess)"
                    continue
                
                # Process document
                ocr_service.process_document(
                    doc_id,
                    model_type=request.model_type,
                    confidence_threshold=request.confidence_threshold
                )
                
                response.processed.append(doc_id)
                logger.info(f"OCR processing initiated for document {doc_id}")
                
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {str(e)}")
                response.failed[doc_id] = str(e)
        
        # Update counts
        response.success_count = len(response.processed)
        response.failure_count = len(response.failed)
        
        logger.info(f"Batch processing completed: {response.success_count} succeeded, {response.failure_count} failed")
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error in batch processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during batch processing"
        )


@router.get(
    "/confidence/thresholds",
    response_model=ConfidenceThresholdResponse,
    summary="Get confidence thresholds",
    description="Retrieves the current confidence thresholds used for OCR extraction. These thresholds determine when fields are flagged for human verification.",
    responses={
        200: {"description": "Confidence thresholds retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def get_confidence_thresholds(
    confidence_service: ConfidenceService = Depends(get_confidence_service)
) -> ConfidenceThresholdResponse:
    """Get current confidence thresholds for OCR extraction.
    
    Args:
        confidence_service: Confidence service instance
        
    Returns:
        ConfidenceThresholdResponse: Current confidence thresholds
        
    Raises:
        HTTPException: If retrieving thresholds fails
    """
    try:
        logger.info("Retrieving confidence thresholds")
        
        thresholds = confidence_service.get_thresholds()
        
        return ConfidenceThresholdResponse(
            global_threshold=thresholds.global_threshold,
            document_type_thresholds=thresholds.document_type_thresholds,
            field_type_thresholds=thresholds.field_type_thresholds
        )
        
    except ServiceError as e:
        logger.error(f"Service error retrieving confidence thresholds: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving confidence thresholds: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving confidence thresholds"
        )


@router.put(
    "/confidence/thresholds",
    response_model=ConfidenceThresholdResponse,
    summary="Update confidence thresholds",
    description="Updates the confidence thresholds used for OCR extraction. These thresholds determine when fields are flagged for human verification.",
    responses={
        200: {"description": "Confidence thresholds updated successfully"},
        400: {"description": "Invalid threshold values"},
        500: {"description": "Internal server error"}
    }
)
async def update_confidence_thresholds(
    request: ConfidenceThresholdUpdate = Body(..., description="Threshold update parameters"),
    confidence_service: ConfidenceService = Depends(get_confidence_service)
) -> ConfidenceThresholdResponse:
    """Update confidence thresholds for OCR extraction.
    
    Args:
        request: Threshold update parameters
        confidence_service: Confidence service instance
        
    Returns:
        ConfidenceThresholdResponse: Updated confidence thresholds
        
    Raises:
        HTTPException: If updating thresholds fails
    """
    try:
        logger.info("Updating confidence thresholds")
        
        # Validate threshold values
        if request.global_threshold is not None and (request.global_threshold < 0.0 or request.global_threshold > 1.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Global threshold must be between 0.0 and 1.0"
            )
        
        if request.document_type_thresholds:
            for doc_type, threshold in request.document_type_thresholds.items():
                if threshold < 0.0 or threshold > 1.0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Threshold for document type {doc_type} must be between 0.0 and 1.0"
                    )
        
        if request.field_type_thresholds:
            for field_type, threshold in request.field_type_thresholds.items():
                if threshold < 0.0 or threshold > 1.0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Threshold for field type {field_type} must be between 0.0 and 1.0"
                    )
        
        # Update thresholds
        updated_thresholds = confidence_service.update_thresholds(
            global_threshold=request.global_threshold,
            document_type_thresholds=request.document_type_thresholds,
            field_type_thresholds=request.field_type_thresholds
        )
        
        logger.info("Confidence thresholds updated successfully")
        return ConfidenceThresholdResponse(
            global_threshold=updated_thresholds.global_threshold,
            document_type_thresholds=updated_thresholds.document_type_thresholds,
            field_type_thresholds=updated_thresholds.field_type_thresholds
        )
        
    except ServiceError as e:
        logger.error(f"Service error updating confidence thresholds: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating confidence thresholds: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating confidence thresholds"
        )


@router.get(
    "/status/{processing_id}",
    response_model=Dict[str, Any],
    summary="Get OCR processing status",
    description="Retrieves the status of an OCR processing job. This endpoint can be used to check if processing is complete.",
    responses={
        200: {"description": "Processing status retrieved successfully"},
        404: {"description": "Processing job not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_processing_status(
    processing_id: str = Path(..., description="Unique identifier of the processing job"),
    ocr_service: OCRService = Depends(get_ocr_service)
) -> Dict[str, Any]:
    """Get status of an OCR processing job.
    
    Args:
        processing_id: Unique identifier of the processing job
        ocr_service: OCR service instance
        
    Returns:
        Dict: Processing status information
        
    Raises:
        HTTPException: If processing job not found or status retrieval fails
    """
    try:
        logger.info(f"Retrieving status for OCR processing job {processing_id}")
        
        status_info = ocr_service.get_processing_status(processing_id)
        
        if not status_info:
            logger.warning(f"Processing job {processing_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job {processing_id} not found"
            )
        
        logger.info(f"Successfully retrieved status for processing job {processing_id}")
        return status_info
        
    except ServiceError as e:
        logger.error(f"Service error retrieving processing status for job {processing_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving processing status for job {processing_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving processing status"
        )