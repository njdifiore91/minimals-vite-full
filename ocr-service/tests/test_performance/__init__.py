# OCR Service Performance Test Package
# Version: 1.0.0
# Python 3.9+ Required
"""
OCR Service Performance Tests

This package contains performance test modules for the OCR Service. It makes the
test_performance directory a proper Python package, enabling proper imports between
test modules and ensuring test discovery by pytest.

The test modules in this package evaluate various performance aspects including:

- Latency: Response time for OCR operations
- Throughput: Document processing capacity per unit time
- Scalability: Performance under increasing load
- Resource Usage: Memory, CPU, and GPU utilization
- Accuracy Under Load: Maintaining 99% accuracy during high load
- Processing Speed: Time to process different document types

These tests ensure the OCR Service meets the performance requirements specified
in the technical specification, including processing applications in under 5 minutes
and maintaining 99% data extraction accuracy.

This package follows Python testing best practices and is designed to work with pytest.
"""

# Version information
__version__ = '1.0.0'
__test_package__ = True