from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, Body, status
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Union
import logging
from uuid import UUID

from ..types.documents import DocumentType, ProcessingStatus
from ..types.extraction import ExtractedData, ConfidenceScore
from ..types.errors import ServiceError, ErrorCategory
from ..services.ocr_service import OCRService
from ..services.confidence_service import ConfidenceService
from ..services.field_extraction_service import FieldExtractionService
from ..services.storage_service import StorageService
from ..utils.logging_utils import get_logger
from ..utils.validation_utils import validate_document_id, validate_confidence_threshold

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/ocr",
    tags=["ocr"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Document not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)

# Dependency injection for services
def get_ocr_service():
    return OCRService()

def get_confidence_service():
    return ConfidenceService()

def get_field_extraction_service():
    return FieldExtractionService()

def get_storage_service():
    return StorageService()


@router.get(
    "/{document_id}",
    response_model=ExtractedData,
    summary="Get OCR results for a document",
    description="Retrieves the OCR extraction results for a specific document with confidence scores"
)
async def get_ocr_results(
    document_id: str = Path(..., description="The ID of the document to retrieve OCR results for"),
    include_raw_text: bool = Query(False, description="Whether to include raw extracted text in the response"),
    confidence_threshold: Optional[float] = Query(
        None, 
        description="Minimum confidence threshold for returned fields (0.0-1.0)",
        ge=0.0,
        le=1.0
    ),
    ocr_service: OCRService = Depends(get_ocr_service),
    confidence_service: ConfidenceService = Depends(get_confidence_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        # Validate document ID
        validate_document_id(document_id)
        
        # Log request
        logger.info(f"Retrieving OCR results for document: {document_id}")
        
        # Check if document exists and has been processed
        document_metadata = await storage_service.get_document_metadata(document_id)
        if not document_metadata:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
            
        # Check if document has been processed
        if document_metadata.get('processing_status') != ProcessingStatus.COMPLETED.value:
            logger.warning(f"Document not yet processed: {document_id}, status: {document_metadata.get('processing_status')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document with ID {document_id} has not been processed yet. Current status: {document_metadata.get('processing_status')}"
            )
        
        # Retrieve OCR results from storage
        ocr_results = await storage_service.get_ocr_results(document_id)
        if not ocr_results:
            logger.error(f"OCR results not found for processed document: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR results not found for document {document_id} despite completed status"
            )
        
        # Apply confidence threshold filtering if specified
        if confidence_threshold is not None:
            ocr_results = confidence_service.filter_by_confidence(ocr_results, confidence_threshold)
            
        # Remove raw text if not requested
        if not include_raw_text and 'raw_text' in ocr_results:
            del ocr_results['raw_text']
            
        return ocr_results
        
    except ServiceError as e:
        logger.error(f"Service error retrieving OCR results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving OCR results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/{document_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process a document with OCR",
    description="Manually triggers OCR processing for a specific document"
)
async def process_document(
    background_tasks: BackgroundTasks,
    document_id: str = Path(..., description="The ID of the document to process"),
    force_reprocess: bool = Query(False, description="Whether to force reprocessing even if already processed"),
    document_type: Optional[DocumentType] = Query(None, description="Override the document type for processing"),
    ocr_service: OCRService = Depends(get_ocr_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        # Validate document ID
        validate_document_id(document_id)
        
        # Log request
        logger.info(f"Manual OCR processing requested for document: {document_id}")
        
        # Check if document exists
        document_metadata = await storage_service.get_document_metadata(document_id)
        if not document_metadata:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
            
        # Check if document is already being processed
        current_status = document_metadata.get('processing_status')
        if current_status == ProcessingStatus.PROCESSING.value and not force_reprocess:
            logger.warning(f"Document already being processed: {document_id}")
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": f"Document {document_id} is already being processed",
                    "status": current_status
                }
            )
            
        # Check if document is already processed and reprocessing not forced
        if current_status == ProcessingStatus.COMPLETED.value and not force_reprocess:
            logger.info(f"Document already processed: {document_id}, skipping reprocessing")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"Document {document_id} has already been processed. Use force_reprocess=true to reprocess",
                    "status": current_status
                }
            )
        
        # Update document status to PROCESSING
        await storage_service.update_document_metadata(
            document_id, 
            {"processing_status": ProcessingStatus.PROCESSING.value}
        )
        
        # Add document processing to background tasks
        background_tasks.add_task(
            ocr_service.process_document,
            document_id,
            document_type.value if document_type else None
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": f"Document {document_id} queued for processing",
                "status": ProcessingStatus.PROCESSING.value
            }
        )
        
    except ServiceError as e:
        logger.error(f"Service error processing document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/batch",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process multiple documents with OCR",
    description="Triggers OCR processing for a batch of documents"
)
async def process_batch(
    background_tasks: BackgroundTasks,
    document_ids: List[str] = Body(..., description="List of document IDs to process"),
    force_reprocess: bool = Query(False, description="Whether to force reprocessing even if already processed"),
    ocr_service: OCRService = Depends(get_ocr_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        # Validate document IDs
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No document IDs provided"
            )
            
        if len(document_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size exceeds maximum limit of 100 documents"
            )
        
        # Log request
        logger.info(f"Batch OCR processing requested for {len(document_ids)} documents")
        
        # Process each document ID
        processed_count = 0
        skipped_count = 0
        not_found_count = 0
        results = []
        
        for document_id in document_ids:
            try:
                # Validate document ID
                validate_document_id(document_id)
                
                # Check if document exists
                document_metadata = await storage_service.get_document_metadata(document_id)
                if not document_metadata:
                    logger.warning(f"Document not found: {document_id}")
                    not_found_count += 1
                    results.append({
                        "document_id": document_id,
                        "status": "not_found",
                        "message": "Document not found"
                    })
                    continue
                    
                # Check if document is already processed and reprocessing not forced
                current_status = document_metadata.get('processing_status')
                if current_status == ProcessingStatus.COMPLETED.value and not force_reprocess:
                    logger.info(f"Document already processed: {document_id}, skipping reprocessing")
                    skipped_count += 1
                    results.append({
                        "document_id": document_id,
                        "status": "skipped",
                        "message": "Document already processed"
                    })
                    continue
                
                # Update document status to PROCESSING
                await storage_service.update_document_metadata(
                    document_id, 
                    {"processing_status": ProcessingStatus.PROCESSING.value}
                )
                
                # Add document processing to background tasks
                background_tasks.add_task(
                    ocr_service.process_document,
                    document_id
                )
                
                processed_count += 1
                results.append({
                    "document_id": document_id,
                    "status": "queued",
                    "message": "Document queued for processing"
                })
                
            except Exception as e:
                logger.error(f"Error processing document {document_id} in batch: {str(e)}", exc_info=True)
                results.append({
                    "document_id": document_id,
                    "status": "error",
                    "message": str(e)
                })
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": f"Batch processing initiated for {processed_count} documents. {skipped_count} skipped, {not_found_count} not found.",
                "processed": processed_count,
                "skipped": skipped_count,
                "not_found": not_found_count,
                "results": results
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during batch processing: {str(e)}"
        )


@router.get(
    "/confidence/threshold",
    response_model=Dict[str, float],
    summary="Get confidence thresholds",
    description="Retrieves the current confidence thresholds for OCR processing"
)
async def get_confidence_thresholds(
    confidence_service: ConfidenceService = Depends(get_confidence_service)
):
    try:
        # Get current confidence thresholds
        thresholds = confidence_service.get_confidence_thresholds()
        return thresholds
        
    except ServiceError as e:
        logger.error(f"Service error retrieving confidence thresholds: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving confidence thresholds: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.put(
    "/confidence/threshold/{document_type}",
    response_model=Dict[str, Union[str, float]],
    summary="Update confidence threshold",
    description="Updates the confidence threshold for a specific document type"
)
async def update_confidence_threshold(
    document_type: DocumentType = Path(..., description="The document type to update threshold for"),
    threshold: float = Body(..., description="The new confidence threshold value (0.0-1.0)", ge=0.0, le=1.0),
    confidence_service: ConfidenceService = Depends(get_confidence_service)
):
    try:
        # Validate threshold
        validate_confidence_threshold(threshold)
        
        # Update confidence threshold
        confidence_service.set_confidence_threshold(document_type, threshold)
        
        return {
            "document_type": document_type.value,
            "threshold": threshold,
            "message": f"Confidence threshold for {document_type.value} updated to {threshold}"
        }
        
    except ServiceError as e:
        logger.error(f"Service error updating confidence threshold: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Invalid confidence threshold value: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating confidence threshold: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/status/{document_id}",
    response_model=Dict[str, Any],
    summary="Get document processing status",
    description="Retrieves the current processing status of a document"
)
async def get_document_status(
    document_id: str = Path(..., description="The ID of the document to check status for"),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        # Validate document ID
        validate_document_id(document_id)
        
        # Get document metadata
        document_metadata = await storage_service.get_document_metadata(document_id)
        if not document_metadata:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
            
        # Extract relevant status information
        status_info = {
            "document_id": document_id,
            "status": document_metadata.get('processing_status'),
            "last_updated": document_metadata.get('updated_at'),
            "document_type": document_metadata.get('document_type'),
            "error": document_metadata.get('error')
        }
        
        # Add processing metrics if available
        if 'processing_metrics' in document_metadata:
            status_info["processing_metrics"] = document_metadata['processing_metrics']
            
        return status_info
        
    except ServiceError as e:
        logger.error(f"Service error retrieving document status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving document status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )