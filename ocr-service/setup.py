#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for OCR Service.

This file defines the package metadata, dependencies, and entry points for the OCR Service microservice.
It enables the service to be installed as a Python package with pip for development and deployment.
"""

from setuptools import setup, find_packages

setup(
    name="ocr-service",
    version="0.1.0",
    description="OCR Service for Merchant Cash Advance Application Processing System",
    long_description="""OCR Service microservice that uses TensorFlow for text extraction from documents.
    Part of the Merchant Cash Advance Application Processing System.""",
    author="Dollar Funding",
    author_email="tech@dollarfunding.com",
    url="https://github.com/dollarfunding/ocr-service",
    license="Proprietary",
    python_requires=">=3.9",
    packages=find_packages(where="src"),
    package_dir={"":"src"},
    install_requires=[
        "tensorflow==2.15.0",  # Specified in section 3.2.2
        "numpy>=1.19.5",
        "pika>=1.2.0",  # RabbitMQ client
        "boto3>=1.26.0",  # AWS SDK for S3 storage
        "fastapi>=0.95.0",  # For API endpoints
        "uvicorn>=0.22.0",  # ASGI server for FastAPI
        "pydantic>=2.0.0",  # Data validation
        "python-multipart>=0.0.6",  # For handling multipart/form-data
        "pillow>=9.5.0",  # Image processing
        "opencv-python>=4.7.0",  # Computer vision
        "scikit-learn>=1.2.2",  # Machine learning utilities
        "PyYAML>=6.0",  # Configuration file parsing
        "python-dotenv>=1.0.0",  # Environment variable management
        "cryptography>=41.0.0",  # For AES-256 encryption
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "isort>=5.12.0",
            "mypy>=1.3.0",
            "flake8>=6.0.0",
            "pre-commit>=3.3.2",
        ],
        "gpu": [
            "tensorflow-gpu==2.15.0",  # GPU-accelerated TensorFlow
            "nvidia-cudnn-cu11>=8.6.0",  # CUDA Deep Neural Network library
        ],
    },
    entry_points={
        "console_scripts": [
            "ocr-service=ocr_service.main:main",
            "ocr-worker=ocr_service.worker:main",
            "ocr-api=ocr_service.api:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: Other/Proprietary License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Image Recognition",
    ],
    keywords="ocr, tensorflow, document-processing, machine-learning, microservice",
    project_urls={
        "Documentation": "https://github.com/dollarfunding/ocr-service/docs",
        "Source": "https://github.com/dollarfunding/ocr-service",
        "Issues": "https://github.com/dollarfunding/ocr-service/issues",
    },
    include_package_data=True,
    package_data={
        "ocr_service": ["models/*.h5", "config/*.yaml", "templates/*.html"],
    },
    zip_safe=False,
)