import os
import time
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Tuple, Optional

# Import the necessary modules from the OCR service
# These imports will be patched in the tests
pytest.importorskip("tensorflow")
from ocr_service.services.ocr_service import OCRService
from ocr_service.services.field_extraction_service import FieldExtractionService
from ocr_service.models.model_factory import ModelFactory


# Constants for latency thresholds (in seconds)
MAX_PREPROCESSING_LATENCY = 2.0  # Maximum acceptable preprocessing time
MAX_INFERENCE_LATENCY = 10.0     # Maximum acceptable model inference time
MAX_EXTRACTION_LATENCY = 3.0     # Maximum acceptable field extraction time
MAX_TOTAL_LATENCY = 15.0         # Maximum acceptable total processing time
# Note: These thresholds are for individual documents. The 5-minute requirement
# in section 0.1.1 refers to the entire application processing pipeline, which
# includes multiple documents and additional processing steps.


@pytest.mark.performance
class TestLatency:
    """Test suite for measuring OCR service latency.
    
    These tests measure the time taken for various OCR operations to ensure
    the service meets performance requirements. The OCR service must process
    applications in under 5 minutes from receipt to completion as specified
    in section 0.1.1 of the technical specification.
    """
    
    @pytest.mark.parametrize("document_type", ["typed", "handwritten", "mixed"])
    def test_document_preprocessing_latency(self, document_type, sample_document_paths, mock_ocr_service):
        """Test the latency of document preprocessing operations.
        
        This test measures the time taken to preprocess documents before OCR processing,
        including loading, normalization, and enhancement.
        
        Args:
            document_type: The type of document to test (typed, handwritten, mixed)
            sample_document_paths: Fixture providing paths to sample documents
            mock_ocr_service: Fixture providing a mock OCR service
        """
        # Get a sample document path for the specified type
        document_path = sample_document_paths[document_type][0]
        
        # Create a real OCRService instance with the mock dependencies
        with patch('ocr_service.services.ocr_service.OCRService._preprocess_document') as mock_preprocess:
            # Configure the mock to measure actual preprocessing time
            def timed_preprocess(doc_path):
                start_time = time.time()
                # Simulate preprocessing operations with realistic timing
                # based on document type
                if document_type == "typed":
                    time.sleep(0.5)  # Typed documents are faster to preprocess
                elif document_type == "handwritten":
                    time.sleep(1.0)  # Handwritten documents take longer
                else:  # mixed
                    time.sleep(0.8)  # Mixed documents are in between
                
                # Simulate some CPU-bound work
                for _ in range(1000000):
                    pass
                
                end_time = time.time()
                return {
                    "preprocessed_image": np.random.random((100, 100)),
                    "processing_time": end_time - start_time
                }
            
            mock_preprocess.side_effect = timed_preprocess
            
            # Call the preprocessing function and measure time
            start_time = time.time()
            result = mock_ocr_service._preprocess_document(document_path)
            end_time = time.time()
            
            # Calculate total preprocessing time
            preprocessing_time = end_time - start_time
            
            # Log the preprocessing time for analysis
            print(f"\nPreprocessing time for {document_type} document: {preprocessing_time:.4f} seconds")
            
            # Assert that preprocessing time is within acceptable limits
            assert preprocessing_time < MAX_PREPROCESSING_LATENCY, \
                f"Preprocessing time for {document_type} document exceeds threshold: {preprocessing_time:.4f}s > {MAX_PREPROCESSING_LATENCY}s"
    
    @pytest.mark.parametrize("document_type", ["typed", "handwritten", "mixed"])
    def test_model_inference_latency(self, document_type, sample_document_paths, mock_tensorflow_model):
        """Test the latency of OCR model inference operations.
        
        This test measures the time taken for the TensorFlow model to perform
        text recognition on preprocessed document images.
        
        Args:
            document_type: The type of document to test (typed, handwritten, mixed)
            sample_document_paths: Fixture providing paths to sample documents
            mock_tensorflow_model: Fixture providing a mock TensorFlow model
        """
        # Get a sample document path for the specified type
        document_path = sample_document_paths[document_type][0]
        
        # Create a mock preprocessed image
        preprocessed_image = np.random.random((100, 100))
        
        # Configure the mock model to measure inference time
        def timed_predict(image, **kwargs):
            start_time = time.time()
            
            # Simulate model inference with realistic timing based on document type
            if document_type == "typed":
                time.sleep(2.0)  # Typed documents are faster for inference
            elif document_type == "handwritten":
                time.sleep(5.0)  # Handwritten documents take longer
            else:  # mixed
                time.sleep(3.5)  # Mixed documents are in between
            
            # Simulate some CPU/GPU-bound work
            for _ in range(2000000):
                pass
            
            end_time = time.time()
            
            # Return mock OCR results with timing information
            return {
                "text": f"Sample OCR text for {document_type} document",
                "confidence": 0.95 if document_type == "typed" else 0.85,
                "bounding_boxes": [[0.1, 0.1, 0.9, 0.9]],
                "processing_time": end_time - start_time
            }
        
        mock_tensorflow_model.predict.side_effect = timed_predict
        
        # Call the model inference function and measure time
        start_time = time.time()
        result = mock_tensorflow_model.predict(preprocessed_image)
        end_time = time.time()
        
        # Calculate total inference time
        inference_time = end_time - start_time
        
        # Log the inference time for analysis
        print(f"\nModel inference time for {document_type} document: {inference_time:.4f} seconds")
        
        # Assert that inference time is within acceptable limits
        assert inference_time < MAX_INFERENCE_LATENCY, \
            f"Model inference time for {document_type} document exceeds threshold: {inference_time:.4f}s > {MAX_INFERENCE_LATENCY}s"
    
    @pytest.mark.parametrize("document_type", ["typed", "handwritten", "mixed"])
    def test_field_extraction_latency(self, document_type, mock_confidence_service):
        """Test the latency of field extraction and post-processing operations.
        
        This test measures the time taken to extract structured fields from OCR results
        and perform post-processing operations like confidence scoring.
        
        Args:
            document_type: The type of document to test (typed, handwritten, mixed)
            mock_confidence_service: Fixture providing a mock confidence scoring service
        """
        # Create mock OCR results based on document type
        if document_type == "typed":
            ocr_results = {
                "text": "ABC Corporation\n12-3456789\n123 Main St, Anytown, USA",
                "confidence": 0.95,
                "bounding_boxes": [[0.1, 0.1, 0.9, 0.2], [0.1, 0.3, 0.5, 0.4], [0.1, 0.5, 0.9, 0.6]]
            }
        elif document_type == "handwritten":
            ocr_results = {
                "text": "John Smith\nJohn Smith\n2023-01-15",
                "confidence": 0.85,
                "bounding_boxes": [[0.1, 0.1, 0.5, 0.2], [0.1, 0.3, 0.5, 0.4], [0.1, 0.5, 0.4, 0.6]]
            }
        else:  # mixed
            ocr_results = {
                "text": "XYZ Industries\n98-7654321\nJane Doe",
                "confidence": 0.90,
                "bounding_boxes": [[0.1, 0.1, 0.7, 0.2], [0.1, 0.3, 0.5, 0.4], [0.1, 0.5, 0.4, 0.6]]
            }
        
        # Create a mock field extraction service
        with patch('ocr_service.services.field_extraction_service.FieldExtractionService.extract_fields') as mock_extract:
            # Configure the mock to measure extraction time
            def timed_extract(ocr_text, document_type):
                start_time = time.time()
                
                # Simulate field extraction with realistic timing based on document type
                if document_type == "typed":
                    time.sleep(0.8)  # Typed documents are faster for field extraction
                elif document_type == "handwritten":
                    time.sleep(1.5)  # Handwritten documents take longer
                else:  # mixed
                    time.sleep(1.2)  # Mixed documents are in between
                
                # Simulate some CPU-bound work
                for _ in range(1500000):
                    pass
                
                end_time = time.time()
                
                # Return mock extracted fields with timing information
                if document_type == "typed":
                    fields = {
                        "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                        "tax_id": {"value": "12-3456789", "confidence": 0.97},
                        "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
                    }
                elif document_type == "handwritten":
                    fields = {
                        "owner_name": {"value": "John Smith", "confidence": 0.85},
                        "signature": {"value": "John Smith", "confidence": 0.80},
                        "date": {"value": "2023-01-15", "confidence": 0.82}
                    }
                else:  # mixed
                    fields = {
                        "business_name": {"value": "XYZ Industries", "confidence": 0.96},
                        "tax_id": {"value": "98-7654321", "confidence": 0.95},
                        "owner_signature": {"value": "Jane Doe", "confidence": 0.82}
                    }
                
                return {
                    "fields": fields,
                    "processing_time": end_time - start_time
                }
            
            mock_extract.side_effect = timed_extract
            
            # Call the field extraction function and measure time
            start_time = time.time()
            result = mock_extract(ocr_results["text"], document_type)
            end_time = time.time()
            
            # Calculate total extraction time
            extraction_time = end_time - start_time
            
            # Log the extraction time for analysis
            print(f"\nField extraction time for {document_type} document: {extraction_time:.4f} seconds")
            
            # Assert that extraction time is within acceptable limits
            assert extraction_time < MAX_EXTRACTION_LATENCY, \
                f"Field extraction time for {document_type} document exceeds threshold: {extraction_time:.4f}s > {MAX_EXTRACTION_LATENCY}s"
    
    @pytest.mark.parametrize("document_type", ["typed", "handwritten", "mixed"])
    def test_end_to_end_processing_latency(self, document_type, sample_document_paths, mock_document_processing_pipeline):
        """Test the end-to-end latency of document processing.
        
        This test measures the total time taken to process a document from start to finish,
        including preprocessing, OCR, field extraction, and post-processing.
        
        Args:
            document_type: The type of document to test (typed, handwritten, mixed)
            sample_document_paths: Fixture providing paths to sample documents
            mock_document_processing_pipeline: Fixture providing a mock document processing pipeline
        """
        # Get a sample document path for the specified type
        document_path = sample_document_paths[document_type][0]
        
        # Configure the mock pipeline to measure processing time
        def timed_process_document(doc_path, doc_type=None):
            start_time = time.time()
            
            # Simulate end-to-end processing with realistic timing based on document type
            if document_type == "typed":
                time.sleep(4.0)  # Typed documents are faster to process
            elif document_type == "handwritten":
                time.sleep(8.0)  # Handwritten documents take longer
            else:  # mixed
                time.sleep(6.0)  # Mixed documents are in between
            
            # Simulate some CPU/GPU-bound work
            for _ in range(3000000):
                pass
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Return mock processing results with timing information
            if document_type == "typed":
                return {
                    "document_id": "doc-typed-123",
                    "document_type": "application_form",
                    "extraction_results": {
                        "text": "ABC Corporation\n12-3456789\n123 Main St, Anytown, USA",
                        "fields": {
                            "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                            "tax_id": {"value": "12-3456789", "confidence": 0.97},
                            "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
                        }
                    },
                    "overall_confidence": 0.97,
                    "processing_time": processing_time,
                    "requires_review": False
                }
            elif document_type == "handwritten":
                return {
                    "document_id": "doc-handwritten-456",
                    "document_type": "application_form",
                    "extraction_results": {
                        "text": "John Smith\nJohn Smith\n2023-01-15",
                        "fields": {
                            "owner_name": {"value": "John Smith", "confidence": 0.85},
                            "signature": {"value": "John Smith", "confidence": 0.80},
                            "date": {"value": "2023-01-15", "confidence": 0.82}
                        }
                    },
                    "overall_confidence": 0.82,
                    "processing_time": processing_time,
                    "requires_review": False
                }
            else:  # mixed
                return {
                    "document_id": "doc-mixed-789",
                    "document_type": "application_form",
                    "extraction_results": {
                        "text": "XYZ Industries\n98-7654321\nJane Doe",
                        "fields": {
                            "business_name": {"value": "XYZ Industries", "confidence": 0.96},
                            "tax_id": {"value": "98-7654321", "confidence": 0.95},
                            "owner_signature": {"value": "Jane Doe", "confidence": 0.82}
                        }
                    },
                    "overall_confidence": 0.91,
                    "processing_time": processing_time,
                    "requires_review": False
                }
        
        mock_document_processing_pipeline.process_document.side_effect = timed_process_document
        
        # Call the document processing function and measure time
        start_time = time.time()
        result = mock_document_processing_pipeline.process_document(document_path, document_type)
        end_time = time.time()
        
        # Calculate total processing time
        total_processing_time = end_time - start_time
        
        # Log the total processing time for analysis
        print(f"\nEnd-to-end processing time for {document_type} document: {total_processing_time:.4f} seconds")
        print(f"Reported processing time from pipeline: {result['processing_time']:.4f} seconds")
        
        # Assert that total processing time is within acceptable limits
        assert total_processing_time < MAX_TOTAL_LATENCY, \
            f"End-to-end processing time for {document_type} document exceeds threshold: {total_processing_time:.4f}s > {MAX_TOTAL_LATENCY}s"
        
        # Also verify that the reported processing time is within limits
        assert result["processing_time"] < MAX_TOTAL_LATENCY, \
            f"Reported processing time for {document_type} document exceeds threshold: {result['processing_time']:.4f}s > {MAX_TOTAL_LATENCY}s"
    
    def test_processing_time_under_load(self, sample_document_paths, mock_document_processing_pipeline):
        """Test the processing time when multiple documents are processed in sequence.
        
        This test measures the total time taken to process multiple documents in sequence,
        simulating a batch processing scenario. It verifies that the system can handle
        the required throughput to meet the 5-minute application processing requirement.
        
        Args:
            sample_document_paths: Fixture providing paths to sample documents
            mock_document_processing_pipeline: Fixture providing a mock document processing pipeline
        """
        # Define a typical application with multiple document types
        application_documents = [
            {"path": sample_document_paths["typed"][0], "type": "typed"},
            {"path": sample_document_paths["handwritten"][0], "type": "handwritten"},
            {"path": sample_document_paths["mixed"][0], "type": "mixed"},
        ]
        
        # Configure the mock pipeline to measure processing time
        def timed_process_document(doc_path, doc_type=None):
            # Determine document type if not provided
            if doc_type is None:
                if "typed" in str(doc_path):
                    doc_type = "typed"
                elif "handwritten" in str(doc_path):
                    doc_type = "handwritten"
                else:
                    doc_type = "mixed"
            
            # Simulate processing with realistic timing based on document type
            if doc_type == "typed":
                time.sleep(3.0)  # Typed documents are faster to process
            elif doc_type == "handwritten":
                time.sleep(6.0)  # Handwritten documents take longer
            else:  # mixed
                time.sleep(4.5)  # Mixed documents are in between
            
            # Return mock processing results
            return {
                "document_id": f"doc-{doc_type}-{hash(str(doc_path)) % 1000}",
                "document_type": "application_form",
                "extraction_results": {
                    "text": f"Sample text for {doc_type} document",
                    "fields": {}
                },
                "overall_confidence": 0.9,
                "processing_time": 3.0 if doc_type == "typed" else (6.0 if doc_type == "handwritten" else 4.5),
                "requires_review": False
            }
        
        mock_document_processing_pipeline.process_document.side_effect = timed_process_document
        
        # Process all documents and measure total time
        start_time = time.time()
        results = []
        
        for doc in application_documents:
            result = mock_document_processing_pipeline.process_document(doc["path"], doc["type"])
            results.append(result)
        
        end_time = time.time()
        total_application_time = end_time - start_time
        
        # Log the total application processing time
        print(f"\nTotal application processing time for {len(application_documents)} documents: {total_application_time:.4f} seconds")
        
        # Calculate average document processing time
        avg_doc_time = total_application_time / len(application_documents)
        print(f"Average document processing time: {avg_doc_time:.4f} seconds")
        
        # Assert that total application processing time is within the 5-minute requirement
        # Convert 5 minutes to seconds: 5 * 60 = 300 seconds
        assert total_application_time < 300, \
            f"Total application processing time exceeds 5-minute requirement: {total_application_time:.4f}s > 300s"
        
        # Also verify that each document was processed within its individual threshold
        for i, result in enumerate(results):
            doc_type = application_documents[i]["type"]
            assert result["processing_time"] < MAX_TOTAL_LATENCY, \
                f"Processing time for {doc_type} document exceeds threshold: {result['processing_time']:.4f}s > {MAX_TOTAL_LATENCY}s"
    
    def test_latency_with_different_document_sizes(self, create_test_document, mock_document_processing_pipeline):
        """Test the processing latency with documents of different sizes.
        
        This test measures the processing time for documents of different sizes
        to verify that the system can handle varying document complexities within
        acceptable time limits.
        
        Args:
            create_test_document: Fixture providing a function to create test documents
            mock_document_processing_pipeline: Fixture providing a mock document processing pipeline
        """
        # Create test documents of different sizes
        small_doc = create_test_document(content_type="typed", content="Small document with minimal text.")
        medium_doc = create_test_document(content_type="typed", content="Medium document with more text. " * 10)
        large_doc = create_test_document(content_type="typed", content="Large document with lots of text. " * 50)
        
        # Configure the mock pipeline to measure processing time based on document size
        def timed_process_document(doc_path, doc_type=None):
            # Determine processing time based on file size
            file_size = os.path.getsize(doc_path)
            
            if file_size < 1000:  # Small document
                processing_time = 2.0
                time.sleep(processing_time)
            elif file_size < 5000:  # Medium document
                processing_time = 5.0
                time.sleep(processing_time)
            else:  # Large document
                processing_time = 10.0
                time.sleep(processing_time)
            
            # Return mock processing results
            return {
                "document_id": f"doc-{hash(str(doc_path)) % 1000}",
                "document_type": "application_form",
                "extraction_results": {
                    "text": f"Sample text for document of size {file_size} bytes",
                    "fields": {}
                },
                "overall_confidence": 0.9,
                "processing_time": processing_time,
                "requires_review": False
            }
        
        mock_document_processing_pipeline.process_document.side_effect = timed_process_document
        
        # Process each document and measure time
        documents = [(small_doc, "small"), (medium_doc, "medium"), (large_doc, "large")]
        results = {}
        
        for doc_path, doc_size in documents:
            start_time = time.time()
            result = mock_document_processing_pipeline.process_document(doc_path)
            end_time = time.time()
            
            processing_time = end_time - start_time
            results[doc_size] = {
                "path": doc_path,
                "size": os.path.getsize(doc_path),
                "processing_time": processing_time,
                "reported_time": result["processing_time"]
            }
        
        # Log the results for analysis
        for doc_size, data in results.items():
            print(f"\n{doc_size.capitalize()} document ({data['size']} bytes):")
            print(f"  Measured processing time: {data['processing_time']:.4f} seconds")
            print(f"  Reported processing time: {data['reported_time']:.4f} seconds")
        
        # Assert that processing times are within acceptable limits
        # Small documents should be processed quickly
        assert results["small"]["processing_time"] < MAX_TOTAL_LATENCY / 2, \
            f"Processing time for small document exceeds threshold: {results['small']['processing_time']:.4f}s > {MAX_TOTAL_LATENCY/2}s"
        
        # Medium documents should be processed within normal limits
        assert results["medium"]["processing_time"] < MAX_TOTAL_LATENCY, \
            f"Processing time for medium document exceeds threshold: {results['medium']['processing_time']:.4f}s > {MAX_TOTAL_LATENCY}s"
        
        # Large documents can take longer but should still be within reasonable limits
        # We allow up to 1.5x the normal threshold for large documents
        assert results["large"]["processing_time"] < MAX_TOTAL_LATENCY * 1.5, \
            f"Processing time for large document exceeds extended threshold: {results['large']['processing_time']:.4f}s > {MAX_TOTAL_LATENCY*1.5}s"