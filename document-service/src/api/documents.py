from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
from uuid import UUID

from ..services.classification_service import ClassificationService
from ..services.document_routing_service import DocumentRoutingService
from ..services.storage_service import StorageService
from ..types.documents import Document, DocumentType, ProcessingStatus
from ..types.classification import ClassificationResult, ConfidenceScore
from ..types.errors import ServiceError, ErrorCategory

# Configure logger
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Document not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    }
)


# Dependency to get required services
def get_classification_service():
    return ClassificationService()


def get_document_routing_service():
    return DocumentRoutingService()


def get_storage_service():
    return StorageService()


@router.get(
    "/{document_id}",
    response_model=Dict[str, Any],
    summary="Get document classification status",
    description="Retrieves the classification status and metadata for a specific document"
)
async def get_document(
    document_id: UUID = Path(..., description="The ID of the document to retrieve"),
    classification_service: ClassificationService = Depends(get_classification_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        logger.info(f"Retrieving document classification status for document_id: {document_id}")
        
        # Check if document exists
        document = await storage_service.get_document_metadata(document_id)
        if not document:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Get classification results if available
        classification_result = await classification_service.get_classification_result(document_id)
        
        # Prepare response
        response = {
            "document_id": str(document_id),
            "metadata": document.metadata,
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat()
        }
        
        # Add classification data if available
        if classification_result:
            response["classification"] = {
                "document_type": classification_result.document_type.value,
                "confidence": classification_result.confidence.value,
                "requires_review": classification_result.confidence.value < 0.75,
                "classified_at": classification_result.classified_at.isoformat()
            }
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the document"
        )


@router.post(
    "/{document_id}/classify",
    response_model=Dict[str, Any],
    summary="Manually trigger document classification",
    description="Manually triggers the classification process for a specific document"
)
async def classify_document(
    document_id: UUID = Path(..., description="The ID of the document to classify"),
    force: bool = Query(False, description="Force reclassification even if already classified"),
    classification_service: ClassificationService = Depends(get_classification_service),
    document_routing_service: DocumentRoutingService = Depends(get_document_routing_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        logger.info(f"Manually triggering classification for document_id: {document_id}, force: {force}")
        
        # Check if document exists
        document = await storage_service.get_document(document_id)
        if not document:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Check if already classified and not forcing reclassification
        existing_classification = await classification_service.get_classification_result(document_id)
        if existing_classification and not force:
            logger.info(f"Document {document_id} already classified and force=False")
            return {
                "document_id": str(document_id),
                "status": "already_classified",
                "classification": {
                    "document_type": existing_classification.document_type.value,
                    "confidence": existing_classification.confidence.value,
                    "requires_review": existing_classification.confidence.value < 0.75,
                    "classified_at": existing_classification.classified_at.isoformat()
                }
            }
        
        # Perform classification
        classification_result = await classification_service.classify_document(document)
        
        # Route document based on classification
        routing_result = await document_routing_service.route_document(document, classification_result)
        
        # Update document status
        document.status = ProcessingStatus.CLASSIFIED
        await storage_service.update_document_metadata(document)
        
        # Prepare response
        response = {
            "document_id": str(document_id),
            "status": "classification_complete",
            "classification": {
                "document_type": classification_result.document_type.value,
                "confidence": classification_result.confidence.value,
                "requires_review": classification_result.confidence.value < 0.75,
                "classified_at": classification_result.classified_at.isoformat()
            },
            "routing": {
                "destination": routing_result.destination,
                "routed_at": routing_result.routed_at.isoformat()
            }
        }
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ServiceError as se:
        logger.error(f"Service error during classification: {str(se)}", exc_info=True)
        if se.category == ErrorCategory.VALIDATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(se)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(se)
            )
    except Exception as e:
        logger.error(f"Error classifying document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while classifying the document"
        )


@router.post(
    "/batch",
    response_model=Dict[str, Any],
    summary="Batch document classification",
    description="Triggers classification for multiple documents in a single request"
)
async def batch_classify(
    document_ids: List[UUID] = Body(..., description="List of document IDs to classify"),
    force: bool = Query(False, description="Force reclassification even if already classified"),
    classification_service: ClassificationService = Depends(get_classification_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        logger.info(f"Batch classification requested for {len(document_ids)} documents, force: {force}")
        
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No document IDs provided"
            )
        
        # Limit batch size for performance reasons
        if len(document_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size exceeds maximum limit of 100 documents"
            )
        
        # Process batch
        results = {
            "successful": [],
            "failed": [],
            "skipped": []
        }
        
        for doc_id in document_ids:
            try:
                # Check if document exists
                document = await storage_service.get_document(doc_id)
                if not document:
                    results["failed"].append({
                        "document_id": str(doc_id),
                        "error": "Document not found"
                    })
                    continue
                
                # Check if already classified and not forcing reclassification
                existing_classification = await classification_service.get_classification_result(doc_id)
                if existing_classification and not force:
                    results["skipped"].append({
                        "document_id": str(doc_id),
                        "reason": "Already classified and force=False"
                    })
                    continue
                
                # Queue document for classification (async processing)
                await classification_service.queue_for_classification(doc_id)
                
                results["successful"].append({
                    "document_id": str(doc_id),
                    "status": "queued_for_classification"
                })
                
            except Exception as e:
                logger.error(f"Error processing document {doc_id} in batch: {str(e)}", exc_info=True)
                results["failed"].append({
                    "document_id": str(doc_id),
                    "error": str(e)
                })
        
        # Prepare summary
        summary = {
            "total": len(document_ids),
            "successful": len(results["successful"]),
            "failed": len(results["failed"]),
            "skipped": len(results["skipped"])
        }
        
        return {
            "summary": summary,
            "results": results
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in batch classification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during batch classification"
        )


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="List documents",
    description="Retrieves a paginated list of documents with optional filtering"
)
async def list_documents(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    confidence_min: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence score"),
    confidence_max: Optional[float] = Query(None, ge=0, le=1, description="Maximum confidence score"),
    requires_review: Optional[bool] = Query(None, description="Filter documents requiring human review"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    storage_service: StorageService = Depends(get_storage_service),
    classification_service: ClassificationService = Depends(get_classification_service)
):
    try:
        logger.info(f"Listing documents with filters: type={document_type}, status={status}, 
                    confidence_min={confidence_min}, confidence_max={confidence_max}, 
                    requires_review={requires_review}, page={page}, page_size={page_size}")
        
        # Convert string parameters to enums if provided
        doc_type_enum = None
        if document_type:
            try:
                doc_type_enum = DocumentType[document_type.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document type: {document_type}"
                )
        
        status_enum = None
        if status:
            try:
                status_enum = ProcessingStatus[status.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
        
        # Get documents with pagination and filtering
        documents, total_count = await storage_service.list_documents(
            document_type=doc_type_enum,
            status=status_enum,
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            requires_review=requires_review,
            page=page,
            page_size=page_size
        )
        
        # Format response
        document_list = []
        for doc in documents:
            doc_data = {
                "document_id": str(doc.id),
                "metadata": doc.metadata,
                "status": doc.status.value,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            }
            
            # Add classification data if available
            classification = await classification_service.get_classification_result(doc.id)
            if classification:
                doc_data["classification"] = {
                    "document_type": classification.document_type.value,
                    "confidence": classification.confidence.value,
                    "requires_review": classification.confidence.value < 0.75,
                    "classified_at": classification.classified_at.isoformat()
                }
            
            document_list.append(doc_data)
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "documents": document_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving documents"
        )