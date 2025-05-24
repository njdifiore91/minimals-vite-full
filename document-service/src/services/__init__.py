#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service Services Package

This package provides the core services for the Document Service microservice.
It imports and re-exports all service components to present a single, cohesive API surface,
simplifying service imports throughout the application and ensuring consistent service usage.

Services included:
- QueueService: Handles RabbitMQ message queue operations
- StorageService: Provides S3-compatible storage operations
- ClassificationService: Orchestrates document classification process
- DocumentRoutingService: Handles routing of classified documents to OCR processors

Usage examples:
    from services import QueueService
    from services import StorageService
    from services import ClassificationService
    from services import DocumentRoutingService

    # Or import all services at once
    from services import QueueService, StorageService, ClassificationService, DocumentRoutingService
"""

# Import all service components
from .queue_service import QueueService
from .storage_service import StorageService
from .classification_service import ClassificationService
from .document_routing_service import DocumentRoutingService

# Export all service components
__all__ = [
    'QueueService',
    'StorageService',
    'ClassificationService',
    'DocumentRoutingService'
]