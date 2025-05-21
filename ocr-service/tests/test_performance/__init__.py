# OCR Service Performance Tests Package
# Version: 1.0.0
"""
OCR Service Performance Tests

This package contains performance tests for the OCR Service, measuring:
- Processing speed for different document types
- Throughput capacity under various load conditions
- Latency of OCR operations
- Resource usage (CPU, memory, GPU)
- Accuracy under load conditions
- Scalability with increasing resources

These tests ensure the OCR Service meets the performance requirements
specified in the technical specification, including:
- Processing applications in under 5 minutes (section 0.1.1)
- Maintaining 99% data extraction accuracy (section 0.1.1)
- Supporting 99.9% system uptime (section 0.2.5)
- Utilizing GPU acceleration efficiently (section 3.2.3)
"""

# Version information
__version__ = '1.0.0'