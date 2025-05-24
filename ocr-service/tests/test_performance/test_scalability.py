#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scalability tests for the OCR Service.

This module tests how the OCR Service scales with increasing load and resources.
It verifies that the service can handle growing document volumes by adding resources,
and measures performance under constrained resources to understand scaling limitations.

The tests validate:
1. Linear scaling with additional resources
2. Performance under constrained resources
3. Recovery after resource exhaustion
4. Optimal resource allocation
5. System scalability to meet varying demand levels
"""

import os
import time
import json
import pytest
import numpy as np
import concurrent.futures
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, List, Any, Tuple, Optional

# Import application modules
from src.app import Application
from src.services.ocr_service import OCRService
from src.services.queue_service import QueueService
from src.services.storage_service import StorageService
from src.models.model_factory import ModelFactory
from src.types.documents import Document, DocumentType, DocumentMetadata, ProcessingStatus
from src.types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from src.types.models import OCRModelType, ModelResult, ModelParameters
from src.types.messages import MessagePayload, MessageHeaders
from src.types.errors import ServiceError, ErrorCategory, Result
from src.utils.tensorflow_utils import is_gpu_available, get_gpu_info, get_available_memory


class TestScalability:
    """Test the scalability of the OCR Service under various load conditions."""
    
    @pytest.mark.parametrize("num_workers", [1, 2, 4, 8])
    def test_linear_scaling_with_workers(self, num_workers, document_collection, mock_application):
        """
        Test that the OCR service scales linearly with additional worker processes.
        
        This test verifies that adding more worker processes improves throughput
        proportionally, up to the point of diminishing returns.
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 10:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Process documents with different numbers of workers and measure throughput
        start_time = time.time()
        processed_docs = self._process_documents_with_workers(document_collection, num_workers, mock_application)
        end_time = time.time()
        
        # Calculate throughput (docs/second)
        processing_time = end_time - start_time
        throughput = len(processed_docs) / processing_time if processing_time > 0 else 0
        
        # Log results for analysis
        print(f"Workers: {num_workers}, Throughput: {throughput:.2f} docs/sec, Time: {processing_time:.2f} sec")
        
        # Verify that all documents were processed successfully
        assert len(processed_docs) == len(document_collection)
        assert all(result.is_success for result in processed_docs)
        
        # Store throughput for comparison across worker counts
        if not hasattr(self, '_throughput_data'):
            self._throughput_data = {}
        self._throughput_data[num_workers] = throughput
        
        # If we have at least two data points, check for scaling
        if len(self._throughput_data) >= 2 and num_workers > 1:
            # Calculate scaling efficiency (should be close to 1.0 for perfect linear scaling)
            baseline_workers = 1
            baseline_throughput = self._throughput_data.get(baseline_workers, 0)
            if baseline_throughput > 0:
                scaling_efficiency = (throughput / num_workers) / (baseline_throughput / baseline_workers)
                
                # Scaling efficiency should be at least 0.7 (70% efficient) for reasonable scaling
                # This threshold might need adjustment based on the specific system
                assert scaling_efficiency >= 0.7, f"Poor scaling efficiency: {scaling_efficiency:.2f}"
                
                print(f"Scaling efficiency with {num_workers} workers: {scaling_efficiency:.2f}")
    
    @pytest.mark.parametrize("memory_limit_mb", [1024, 512, 256])
    def test_performance_under_memory_constraints(self, memory_limit_mb, typed_document, mock_application):
        """
        Test OCR service performance under memory constraints.
        
        This test verifies that the service can operate effectively even with
        limited memory resources, and gracefully handles memory pressure.
        """
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Mock the memory limit
        with patch('src.utils.tensorflow_utils.get_available_memory', return_value=memory_limit_mb * 1024 * 1024):
            # Process the document and measure performance
            start_time = time.time()
            result = mock_application.process_document(typed_document)
            processing_time = time.time() - start_time
            
            # Log results
            print(f"Memory limit: {memory_limit_mb} MB, Processing time: {processing_time:.2f} sec")
            
            # Verify that the document was processed successfully
            assert result.is_success, f"Processing failed with memory limit {memory_limit_mb} MB"
            
            # Verify that processing time is reasonable (adjust threshold as needed)
            assert processing_time < 300, f"Processing time exceeded 5 minutes with memory limit {memory_limit_mb} MB"
    
    @pytest.mark.parametrize("cpu_limit", [1, 2, 4])
    def test_performance_under_cpu_constraints(self, cpu_limit, document_collection, mock_application):
        """
        Test OCR service performance under CPU constraints.
        
        This test verifies that the service can operate effectively even with
        limited CPU resources, and gracefully handles CPU pressure.
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 5:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Process documents with limited CPU cores and measure throughput
        start_time = time.time()
        processed_docs = self._process_documents_with_workers(
            document_collection[:5],  # Use a subset for faster testing
            min(cpu_limit, len(document_collection)),
            mock_application
        )
        end_time = time.time()
        
        # Calculate throughput (docs/second)
        processing_time = end_time - start_time
        throughput = len(processed_docs) / processing_time if processing_time > 0 else 0
        
        # Log results for analysis
        print(f"CPU limit: {cpu_limit}, Throughput: {throughput:.2f} docs/sec, Time: {processing_time:.2f} sec")
        
        # Verify that all documents were processed successfully
        assert len(processed_docs) == min(5, len(document_collection))
        assert all(result.is_success for result in processed_docs)
        
        # Store throughput for comparison across CPU limits
        if not hasattr(self, '_cpu_throughput_data'):
            self._cpu_throughput_data = {}
        self._cpu_throughput_data[cpu_limit] = throughput
    
    def test_gpu_acceleration_scaling(self, document_collection, mock_application):
        """
        Test scaling with GPU acceleration.
        
        This test verifies that the service can effectively utilize GPU resources
        when available, and scales appropriately with GPU capabilities.
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 5:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Test with and without GPU acceleration
        scenarios = [
            {"gpu_available": False, "gpu_memory": 0, "gpu_info": None},
            {"gpu_available": True, "gpu_memory": 4096, "gpu_info": "Tesla T4"},  # 4GB VRAM
            {"gpu_available": True, "gpu_memory": 8192, "gpu_info": "Tesla V100"},  # 8GB VRAM
            {"gpu_available": True, "gpu_memory": 16384, "gpu_info": "Tesla A100"}  # 16GB VRAM
        ]
        
        results = {}
        
        for scenario in scenarios:
            # Mock GPU environment
            with patch('src.utils.tensorflow_utils.is_gpu_available', return_value=scenario["gpu_available"]), \
                 patch('src.utils.tensorflow_utils.get_gpu_info', return_value=scenario["gpu_info"]), \
                 patch('src.utils.tensorflow_utils.get_gpu_memory', return_value=scenario["gpu_memory"]):
                
                # Process documents and measure throughput
                start_time = time.time()
                processed_docs = self._process_documents_with_workers(
                    document_collection[:5],  # Use a subset for faster testing
                    4,  # Use fixed number of workers for consistent comparison
                    mock_application
                )
                end_time = time.time()
                
                # Calculate throughput (docs/second)
                processing_time = end_time - start_time
                throughput = len(processed_docs) / processing_time if processing_time > 0 else 0
                
                # Store results
                scenario_name = scenario["gpu_info"] if scenario["gpu_available"] else "CPU only"
                results[scenario_name] = throughput
                
                # Log results
                print(f"Scenario: {scenario_name}, Throughput: {throughput:.2f} docs/sec")
                
                # Verify that all documents were processed successfully
                assert len(processed_docs) == 5
                assert all(result.is_success for result in processed_docs)
        
        # Verify that GPU acceleration improves throughput
        if "CPU only" in results and "Tesla T4" in results:
            assert results["Tesla T4"] > results["CPU only"], "GPU acceleration did not improve throughput"
        
        # Verify that more GPU memory improves throughput (if we have multiple GPU scenarios)
        if "Tesla T4" in results and "Tesla V100" in results:
            assert results["Tesla V100"] >= results["Tesla T4"], "More GPU memory did not improve throughput"
    
    def test_recovery_after_resource_exhaustion(self, document_collection, mock_application):
        """
        Test recovery after resource exhaustion.
        
        This test verifies that the service can recover and continue processing
        after experiencing resource exhaustion (memory, CPU, etc.).
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 10:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Simulate resource exhaustion during processing
        # First, process half the documents normally
        first_half = document_collection[:len(document_collection)//2]
        first_half_results = []
        for doc in first_half:
            result = mock_application.process_document(doc)
            first_half_results.append(result)
        
        # Now simulate resource exhaustion for one document
        exhaustion_doc = document_collection[len(document_collection)//2]
        mock_application.ocr_service.process_document.side_effect = ServiceError(
            "Out of memory", ErrorCategory.RESOURCE, {"resource": "memory"}
        )
        exhaustion_result = mock_application.process_document(exhaustion_doc)
        
        # Verify that the exhaustion document failed with a resource error
        assert not exhaustion_result.is_success
        assert exhaustion_result.error.category == ErrorCategory.RESOURCE
        
        # Reset the mock to simulate recovery
        mock_application.ocr_service.process_document.side_effect = None
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Process the remaining documents after "recovery"
        second_half = document_collection[len(document_collection)//2 + 1:]
        second_half_results = []
        for doc in second_half:
            result = mock_application.process_document(doc)
            second_half_results.append(result)
        
        # Verify that processing continued successfully after recovery
        assert all(result.is_success for result in first_half_results)
        assert all(result.is_success for result in second_half_results)
        
        # Verify that the service processed the expected number of documents
        assert len(first_half_results) + len(second_half_results) == len(document_collection) - 1
    
    def test_optimal_resource_allocation(self, document_collection, mock_application):
        """
        Test to determine optimal resource allocation.
        
        This test measures performance across different resource allocations
        to identify the optimal configuration for the OCR service.
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 5:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Define different resource configurations to test
        configurations = [
            {"workers": 1, "memory_mb": 1024, "gpu_available": False},
            {"workers": 2, "memory_mb": 2048, "gpu_available": False},
            {"workers": 4, "memory_mb": 4096, "gpu_available": False},
            {"workers": 2, "memory_mb": 2048, "gpu_available": True},
            {"workers": 4, "memory_mb": 4096, "gpu_available": True}
        ]
        
        results = {}
        
        for config in configurations:
            # Mock resource environment
            with patch('src.utils.tensorflow_utils.is_gpu_available', return_value=config["gpu_available"]), \
                 patch('src.utils.tensorflow_utils.get_available_memory', return_value=config["memory_mb"] * 1024 * 1024):
                
                # Process documents with the current configuration
                start_time = time.time()
                processed_docs = self._process_documents_with_workers(
                    document_collection[:5],  # Use a subset for faster testing
                    config["workers"],
                    mock_application
                )
                end_time = time.time()
                
                # Calculate throughput (docs/second)
                processing_time = end_time - start_time
                throughput = len(processed_docs) / processing_time if processing_time > 0 else 0
                
                # Calculate resource efficiency (throughput per resource unit)
                # This is a simplified metric - in real scenarios, you might use a more complex formula
                resource_units = config["workers"] * (config["memory_mb"] / 1024)
                if config["gpu_available"]:
                    resource_units *= 2  # GPU resources are weighted more heavily
                
                efficiency = throughput / resource_units if resource_units > 0 else 0
                
                # Store results
                config_name = f"W{config['workers']}_M{config['memory_mb']}{'_GPU' if config['gpu_available'] else ''}"
                results[config_name] = {
                    "throughput": throughput,
                    "efficiency": efficiency,
                    "processing_time": processing_time
                }
                
                # Log results
                print(f"Config: {config_name}, Throughput: {throughput:.2f} docs/sec, Efficiency: {efficiency:.4f}")
                
                # Verify that all documents were processed successfully
                assert len(processed_docs) == 5
                assert all(result.is_success for result in processed_docs)
        
        # Find the most efficient configuration
        most_efficient_config = max(results.items(), key=lambda x: x[1]["efficiency"])[0]
        print(f"Most efficient configuration: {most_efficient_config}")
        
        # Find the highest throughput configuration
        highest_throughput_config = max(results.items(), key=lambda x: x[1]["throughput"])[0]
        print(f"Highest throughput configuration: {highest_throughput_config}")
    
    def test_scaling_with_varying_demand(self, document_collection, mock_application):
        """
        Test scaling with varying demand levels.
        
        This test verifies that the service can scale to meet varying demand levels,
        efficiently handling both low and high load conditions.
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 20:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Define different demand levels (number of documents to process)
        demand_levels = [1, 5, 10, 20]
        
        results = {}
        
        for demand in demand_levels:
            # Process documents for the current demand level
            start_time = time.time()
            processed_docs = self._process_documents_with_workers(
                document_collection[:demand],
                min(4, demand),  # Use appropriate number of workers for the demand
                mock_application
            )
            end_time = time.time()
            
            # Calculate throughput (docs/second)
            processing_time = end_time - start_time
            throughput = len(processed_docs) / processing_time if processing_time > 0 else 0
            
            # Store results
            results[demand] = {
                "throughput": throughput,
                "processing_time": processing_time,
                "avg_time_per_doc": processing_time / demand if demand > 0 else 0
            }
            
            # Log results
            print(f"Demand: {demand} docs, Throughput: {throughput:.2f} docs/sec, "  
                  f"Avg time per doc: {results[demand]['avg_time_per_doc']:.2f} sec")
            
            # Verify that all documents were processed successfully
            assert len(processed_docs) == demand
            assert all(result.is_success for result in processed_docs)
        
        # Verify that the service maintains reasonable performance across demand levels
        # The average time per document should not increase dramatically with higher demand
        # This indicates good scaling with demand
        if 1 in results and 20 in results:
            # Allow for some increase in per-document time at higher loads, but not excessive
            # A factor of 2x is reasonable for most systems under higher load
            assert results[20]["avg_time_per_doc"] < results[1]["avg_time_per_doc"] * 2, \
                "Performance degraded significantly under high demand"
    
    def test_concurrent_processing_scalability(self, document_collection, mock_application):
        """
        Test scalability of concurrent document processing.
        
        This test verifies that the service can efficiently process multiple documents
        concurrently, and scales appropriately with the number of concurrent requests.
        """
        # Skip if not enough documents for meaningful test
        if len(document_collection) < 10:
            pytest.skip("Not enough documents for meaningful scalability test")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Define different concurrency levels to test
        concurrency_levels = [1, 2, 4, 8]
        
        results = {}
        
        for concurrency in concurrency_levels:
            # Process documents with the current concurrency level
            start_time = time.time()
            
            # Use ProcessPoolExecutor to simulate concurrent processing
            with concurrent.futures.ProcessPoolExecutor(max_workers=concurrency) as executor:
                # Create a list of documents to process (use the same document multiple times for simplicity)
                docs_to_process = document_collection[:min(10, len(document_collection))]
                
                # Submit document processing tasks to the executor
                future_to_doc = {}
                for doc in docs_to_process:
                    future = executor.submit(self._process_single_document, doc, mock_application)
                    future_to_doc[future] = doc
                
                # Collect results as they complete
                processed_docs = []
                for future in concurrent.futures.as_completed(future_to_doc):
                    doc = future_to_doc[future]
                    try:
                        result = future.result()
                        processed_docs.append(result)
                    except Exception as e:
                        print(f"Document processing failed: {e}")
            
            end_time = time.time()
            
            # Calculate throughput (docs/second)
            processing_time = end_time - start_time
            throughput = len(processed_docs) / processing_time if processing_time > 0 else 0
            
            # Store results
            results[concurrency] = {
                "throughput": throughput,
                "processing_time": processing_time
            }
            
            # Log results
            print(f"Concurrency: {concurrency}, Throughput: {throughput:.2f} docs/sec, "  
                  f"Time: {processing_time:.2f} sec")
            
            # Verify that all documents were processed successfully
            assert len(processed_docs) == len(docs_to_process)
            assert all(result.is_success for result in processed_docs)
        
        # Verify that throughput increases with concurrency (up to a point)
        # This indicates good scaling with concurrent processing
        if 1 in results and 4 in results:
            assert results[4]["throughput"] > results[1]["throughput"], \
                "Throughput did not increase with higher concurrency"
    
    # Helper methods
    
    def _configure_mocks_for_successful_processing(self, mock_application):
        """Configure the mock application for successful document processing."""
        # Configure the OCR service to return successful results
        mock_application.ocr_service.process_document.return_value = Result.success(({"text": "Sample extracted text for testing", "confidence": 0.95}, 1.0))
        
        # Configure the field extraction service to return successful results
        mock_application.field_extraction_service.extract_fields.return_value = Result.success({
            "fields": {
                "name": {"value": "John Doe", "confidence": 0.98},
                "address": {"value": "123 Main St", "confidence": 0.95},
                "phone": {"value": "555-123-4567", "confidence": 0.92},
                "email": {"value": "john.doe@example.com", "confidence": 0.97},
                "business_name": {"value": "Acme Corporation", "confidence": 0.99},
                "tax_id": {"value": "12-3456789", "confidence": 0.96}
            }
        })
        
        # Configure the confidence service to return high confidence scores
        mock_application.confidence_service.evaluate_confidence.return_value = Result.success({
            "overall_confidence": 0.99,
            "requires_verification": False
        })
        
        # Configure the storage service to return successful results
        mock_application.storage_service.upload_extracted_data.return_value = Result.success(
            "s3://mca-documents-test/extracted/doc-123.json"
        )
        
        # Configure the queue service to return successful results
        mock_application.queue_service.publish_message.return_value = Result.success(True)
    
    def _process_documents_with_workers(self, documents, num_workers, mock_application):
        """Process a collection of documents using multiple worker processes."""
        results = []
        
        # Use ProcessPoolExecutor to simulate multiple workers
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit document processing tasks to the executor
            future_to_doc = {}
            for doc in documents:
                future = executor.submit(self._process_single_document, doc, mock_application)
                future_to_doc[future] = doc
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Document processing failed: {e}")
                    # Create a failure result
                    results.append(Result.failure(ServiceError(
                        f"Processing failed: {str(e)}", ErrorCategory.UNKNOWN, {}
                    )))
        
        return results
    
    def _process_single_document(self, document, mock_application):
        """Process a single document and return the result."""
        # This is a helper method that will be called by the ProcessPoolExecutor
        # In a real implementation, this would process the document directly
        # For testing, we'll just call the mock application's process_document method
        return mock_application.process_document(document)