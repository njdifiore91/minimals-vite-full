#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test module for measuring OCR processing speed for different document types.

This module contains performance tests that measure the processing speed of the OCR Service
for different document types (typed, handwritten, mixed) and complexities. It verifies that
the service can process all document types within the required 5-minute time limit.

Requirements tested:
- OCR Service must process applications in under 5 minutes from receipt to completion
- Service must extract data from documents using machine learning models
- Service must apply appropriate OCR model based on document type
- TensorFlow OCR processing requires CUDA-compatible GPU acceleration
"""

import os
import time
import json
import logging
import pytest
from pathlib import Path
from typing import Dict, List, Any

# Import OCR service components for testing
from ocr_service.services import OCRService
from ocr_service.models import ModelFactory
from ocr_service.config import OCRConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_PROCESSING_TIME_SECONDS = 300  # 5 minutes max processing time


@pytest.mark.performance
class TestProcessingSpeed:
    """Test suite for measuring OCR processing speed."""

    def test_typed_document_processing_speed(self, test_documents, performance_metrics, 
                                            gpu_monitor, performance_report, gpu_requirements):
        """Test processing speed for typed documents.
        
        This test measures the processing speed of the OCR Service for typed documents
        of different sizes and complexities. It verifies that all typed documents are
        processed within the required 5-minute time limit.
        
        Args:
            test_documents: Fixture providing test documents
            performance_metrics: Fixture for collecting performance metrics
            gpu_monitor: Fixture for monitoring GPU usage
            performance_report: Fixture for generating performance reports
            gpu_requirements: Fixture that validates GPU requirements
        """
        # Filter for typed documents only
        typed_docs = [doc for doc in test_documents if doc["metadata"]["type"] == "typed"]
        if not typed_docs:
            pytest.skip("No typed documents available for testing")
        
        # Initialize OCR service with appropriate configuration
        config = OCRConfig()
        config.model_type = "typed"
        ocr_service = OCRService(config)
        
        # Start performance measurement
        performance_metrics.start_measurement()
        
        # Start GPU monitoring
        with gpu_monitor:
            # Process each document and measure time
            for doc in typed_docs:
                start_time = time.time()
                
                # Process the document
                result = ocr_service.process_document(doc["path"])
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Record metrics
                performance_metrics.add_processing_time(processing_time)
                logger.info(f"Processed typed document {doc['id']} in {processing_time:.2f} seconds")
                
                # Assert that processing time is within limits
                assert processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                    f"Document {doc['id']} processing time ({processing_time:.2f}s) exceeds limit ({MAX_PROCESSING_TIME_SECONDS}s)"
        
        # End performance measurement
        performance_metrics.end_measurement()
        
        # Generate performance report
        report = performance_report(
            "typed_document_processing_speed",
            performance_metrics=performance_metrics,
            gpu_metrics=gpu_monitor.get_metrics()
        )
        
        # Log summary
        logger.info(f"Typed document processing summary:")
        logger.info(f"  Average processing time: {performance_metrics.get_avg_processing_time():.2f}s")
        logger.info(f"  Maximum processing time: {max(performance_metrics.processing_times):.2f}s")
        logger.info(f"  Documents processed: {len(typed_docs)}")
        
        # Verify performance requirements
        performance_metrics.assert_performance_requirements()

    def test_handwritten_document_processing_speed(self, test_documents, performance_metrics, 
                                                 gpu_monitor, performance_report, gpu_requirements):
        """Test processing speed for handwritten documents.
        
        This test measures the processing speed of the OCR Service for handwritten documents
        of different sizes and complexities. It verifies that all handwritten documents are
        processed within the required 5-minute time limit.
        
        Args:
            test_documents: Fixture providing test documents
            performance_metrics: Fixture for collecting performance metrics
            gpu_monitor: Fixture for monitoring GPU usage
            performance_report: Fixture for generating performance reports
            gpu_requirements: Fixture that validates GPU requirements
        """
        # Filter for handwritten documents only
        handwritten_docs = [doc for doc in test_documents if doc["metadata"]["type"] == "handwritten"]
        if not handwritten_docs:
            pytest.skip("No handwritten documents available for testing")
        
        # Initialize OCR service with appropriate configuration
        config = OCRConfig()
        config.model_type = "handwritten"
        ocr_service = OCRService(config)
        
        # Start performance measurement
        performance_metrics.start_measurement()
        
        # Start GPU monitoring
        with gpu_monitor:
            # Process each document and measure time
            for doc in handwritten_docs:
                start_time = time.time()
                
                # Process the document
                result = ocr_service.process_document(doc["path"])
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Record metrics
                performance_metrics.add_processing_time(processing_time)
                logger.info(f"Processed handwritten document {doc['id']} in {processing_time:.2f} seconds")
                
                # Assert that processing time is within limits
                assert processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                    f"Document {doc['id']} processing time ({processing_time:.2f}s) exceeds limit ({MAX_PROCESSING_TIME_SECONDS}s)"
        
        # End performance measurement
        performance_metrics.end_measurement()
        
        # Generate performance report
        report = performance_report(
            "handwritten_document_processing_speed",
            performance_metrics=performance_metrics,
            gpu_metrics=gpu_monitor.get_metrics()
        )
        
        # Log summary
        logger.info(f"Handwritten document processing summary:")
        logger.info(f"  Average processing time: {performance_metrics.get_avg_processing_time():.2f}s")
        logger.info(f"  Maximum processing time: {max(performance_metrics.processing_times):.2f}s")
        logger.info(f"  Documents processed: {len(handwritten_docs)}")
        
        # Verify performance requirements
        performance_metrics.assert_performance_requirements()

    def test_mixed_document_processing_speed(self, test_documents, performance_metrics, 
                                           gpu_monitor, performance_report, gpu_requirements):
        """Test processing speed for mixed content documents.
        
        This test measures the processing speed of the OCR Service for documents containing
        both typed and handwritten content. It verifies that all mixed documents are
        processed within the required 5-minute time limit.
        
        Args:
            test_documents: Fixture providing test documents
            performance_metrics: Fixture for collecting performance metrics
            gpu_monitor: Fixture for monitoring GPU usage
            performance_report: Fixture for generating performance reports
            gpu_requirements: Fixture that validates GPU requirements
        """
        # Filter for mixed documents only
        mixed_docs = [doc for doc in test_documents if doc["metadata"]["type"] == "mixed"]
        if not mixed_docs:
            pytest.skip("No mixed documents available for testing")
        
        # Initialize OCR service with appropriate configuration
        config = OCRConfig()
        config.model_type = "hybrid"
        ocr_service = OCRService(config)
        
        # Start performance measurement
        performance_metrics.start_measurement()
        
        # Start GPU monitoring
        with gpu_monitor:
            # Process each document and measure time
            for doc in mixed_docs:
                start_time = time.time()
                
                # Process the document
                result = ocr_service.process_document(doc["path"])
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Record metrics
                performance_metrics.add_processing_time(processing_time)
                logger.info(f"Processed mixed document {doc['id']} in {processing_time:.2f} seconds")
                
                # Assert that processing time is within limits
                assert processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                    f"Document {doc['id']} processing time ({processing_time:.2f}s) exceeds limit ({MAX_PROCESSING_TIME_SECONDS}s)"
        
        # End performance measurement
        performance_metrics.end_measurement()
        
        # Generate performance report
        report = performance_report(
            "mixed_document_processing_speed",
            performance_metrics=performance_metrics,
            gpu_metrics=gpu_monitor.get_metrics()
        )
        
        # Log summary
        logger.info(f"Mixed document processing summary:")
        logger.info(f"  Average processing time: {performance_metrics.get_avg_processing_time():.2f}s")
        logger.info(f"  Maximum processing time: {max(performance_metrics.processing_times):.2f}s")
        logger.info(f"  Documents processed: {len(mixed_docs)}")
        
        # Verify performance requirements
        performance_metrics.assert_performance_requirements()

    def test_complex_layout_processing_speed(self, test_documents, performance_metrics, 
                                            gpu_monitor, performance_report, gpu_requirements):
        """Test processing speed for documents with complex layouts.
        
        This test measures the processing speed of the OCR Service for documents with complex
        layouts such as tables, multi-column text, and forms. It verifies that all complex
        documents are processed within the required 5-minute time limit.
        
        Args:
            test_documents: Fixture providing test documents
            performance_metrics: Fixture for collecting performance metrics
            gpu_monitor: Fixture for monitoring GPU usage
            performance_report: Fixture for generating performance reports
            gpu_requirements: Fixture that validates GPU requirements
        """
        # Filter for complex layout documents
        complex_docs = [doc for doc in test_documents if doc["metadata"].get("complexity", "") == "complex"]
        if not complex_docs:
            pytest.skip("No complex layout documents available for testing")
        
        # Initialize OCR service with appropriate configuration
        config = OCRConfig()
        config.enable_structure_recognition = True  # Enable structure recognition for complex layouts
        ocr_service = OCRService(config)
        
        # Start performance measurement
        performance_metrics.start_measurement()
        
        # Start GPU monitoring
        with gpu_monitor:
            # Process each document and measure time
            for doc in complex_docs:
                start_time = time.time()
                
                # Process the document
                result = ocr_service.process_document(doc["path"])
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Record metrics
                performance_metrics.add_processing_time(processing_time)
                logger.info(f"Processed complex document {doc['id']} in {processing_time:.2f} seconds")
                
                # Assert that processing time is within limits
                assert processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                    f"Document {doc['id']} processing time ({processing_time:.2f}s) exceeds limit ({MAX_PROCESSING_TIME_SECONDS}s)"
        
        # End performance measurement
        performance_metrics.end_measurement()
        
        # Generate performance report
        report = performance_report(
            "complex_layout_processing_speed",
            performance_metrics=performance_metrics,
            gpu_metrics=gpu_monitor.get_metrics()
        )
        
        # Log summary
        logger.info(f"Complex layout document processing summary:")
        logger.info(f"  Average processing time: {performance_metrics.get_avg_processing_time():.2f}s")
        logger.info(f"  Maximum processing time: {max(performance_metrics.processing_times):.2f}s")
        logger.info(f"  Documents processed: {len(complex_docs)}")
        
        # Verify performance requirements
        performance_metrics.assert_performance_requirements()

    def test_batch_processing_speed(self, batch_test_documents, performance_metrics, 
                                  gpu_monitor, performance_report, gpu_requirements):
        """Test processing speed for batch document processing.
        
        This test measures the processing speed of the OCR Service when processing a batch
        of documents of different types. It verifies that batch processing completes within
        time limits proportional to the batch size.
        
        Args:
            batch_test_documents: Fixture providing a batch of test documents
            performance_metrics: Fixture for collecting performance metrics
            gpu_monitor: Fixture for monitoring GPU usage
            performance_report: Fixture for generating performance reports
            gpu_requirements: Fixture that validates GPU requirements
        """
        if not batch_test_documents:
            pytest.skip("No documents available for batch testing")
        
        # Initialize OCR service with appropriate configuration
        config = OCRConfig()
        config.enable_batch_processing = True
        ocr_service = OCRService(config)
        
        # Start performance measurement
        performance_metrics.start_measurement()
        
        # Start GPU monitoring
        with gpu_monitor:
            # Prepare batch input
            batch_paths = [doc["path"] for doc in batch_test_documents]
            
            # Process batch and measure time
            start_time = time.time()
            batch_results = ocr_service.process_document_batch(batch_paths)
            processing_time = time.time() - start_time
            
            # Record metrics
            performance_metrics.add_processing_time(processing_time)
            performance_metrics.add_throughput(len(batch_paths), processing_time)
            
            logger.info(f"Processed batch of {len(batch_paths)} documents in {processing_time:.2f} seconds")
            logger.info(f"Average time per document: {processing_time / len(batch_paths):.2f} seconds")
            
            # Assert that processing time is within limits (adjusted for batch size)
            # We allow a proportional time based on batch size, but with some efficiency expected
            max_allowed_time = min(MAX_PROCESSING_TIME_SECONDS * len(batch_paths) * 0.8, 
                                MAX_PROCESSING_TIME_SECONDS * 10)  # Cap at 10x single doc limit
            
            assert processing_time <= max_allowed_time, \
                f"Batch processing time ({processing_time:.2f}s) exceeds adjusted limit ({max_allowed_time:.2f}s)"
        
        # End performance measurement
        performance_metrics.end_measurement()
        
        # Generate performance report
        report = performance_report(
            "batch_processing_speed",
            performance_metrics=performance_metrics,
            gpu_metrics=gpu_monitor.get_metrics()
        )
        
        # Log summary
        logger.info(f"Batch processing summary:")
        logger.info(f"  Total processing time: {processing_time:.2f}s")
        logger.info(f"  Documents processed: {len(batch_paths)}")
        logger.info(f"  Throughput: {len(batch_paths) / processing_time:.2f} docs/second")
        
        # Verify performance requirements
        assert performance_metrics.get_avg_processing_time() <= max_allowed_time, \
            f"Average batch processing time ({performance_metrics.get_avg_processing_time():.2f}s) exceeds limit"

    def test_document_size_impact_on_speed(self, test_documents, performance_metrics, 
                                          gpu_monitor, performance_report, gpu_requirements):
        """Test the impact of document size on processing speed.
        
        This test measures how document size affects OCR processing speed. It processes
        documents of different sizes and analyzes the relationship between document size
        and processing time.
        
        Args:
            test_documents: Fixture providing test documents
            performance_metrics: Fixture for collecting performance metrics
            gpu_monitor: Fixture for monitoring GPU usage
            performance_report: Fixture for generating performance reports
            gpu_requirements: Fixture that validates GPU requirements
        """
        if not test_documents:
            pytest.skip("No documents available for testing")
        
        # Group documents by size
        size_groups = {}
        for doc in test_documents:
            size = doc["metadata"].get("size", "unknown")
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(doc)
        
        # Initialize OCR service
        config = OCRConfig()
        ocr_service = OCRService(config)
        
        # Start performance measurement
        performance_metrics.start_measurement()
        
        # Process documents by size group and measure time
        size_metrics = {}
        
        # Start GPU monitoring
        with gpu_monitor:
            for size, docs in size_groups.items():
                if not docs:
                    continue
                
                size_processing_times = []
                
                for doc in docs:
                    # Process the document and measure time
                    start_time = time.time()
                    result = ocr_service.process_document(doc["path"])
                    processing_time = time.time() - start_time
                    
                    # Record metrics
                    performance_metrics.add_processing_time(processing_time)
                    size_processing_times.append(processing_time)
                    
                    # Assert that processing time is within limits
                    assert processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                        f"Document {doc['id']} processing time ({processing_time:.2f}s) exceeds limit ({MAX_PROCESSING_TIME_SECONDS}s)"
                
                # Calculate average processing time for this size group
                avg_time = sum(size_processing_times) / len(size_processing_times)
                size_metrics[size] = {
                    "avg_processing_time": avg_time,
                    "min_processing_time": min(size_processing_times),
                    "max_processing_time": max(size_processing_times),
                    "document_count": len(docs)
                }
                
                logger.info(f"Size {size} documents: Avg processing time = {avg_time:.2f}s")
        
        # End performance measurement
        performance_metrics.end_measurement()
        
        # Generate performance report
        report = performance_report(
            "document_size_impact",
            performance_metrics=performance_metrics,
            gpu_metrics=gpu_monitor.get_metrics(),
            accuracy_results={"size_metrics": size_metrics}
        )
        
        # Log summary
        logger.info(f"Document size impact summary:")
        for size, metrics in size_metrics.items():
            logger.info(f"  Size {size}: {metrics['avg_processing_time']:.2f}s avg, {metrics['document_count']} documents")
        
        # Verify performance requirements
        performance_metrics.assert_performance_requirements()


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])