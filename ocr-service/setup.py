#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# Define requirements directly since requirements.txt might not exist yet
requirements = [
    "tensorflow==2.15.0",  # TensorFlow for OCR models with GPU acceleration
    "fastapi>=0.95.0",     # API framework for health checks and diagnostics
    "uvicorn>=0.22.0",     # ASGI server for FastAPI
    "pika>=1.3.0",         # RabbitMQ client for message queue
    "boto3>=1.26.0",       # AWS SDK for S3-compatible storage
    "pillow>=9.5.0",       # Image processing library
    "numpy>=1.23.0",       # Numerical computing
    "scikit-image>=0.20.0", # Image processing algorithms
    "opencv-python>=4.7.0", # Computer vision library
    "pydantic>=1.10.0",    # Data validation and settings management
    "python-dotenv>=1.0.0", # Environment variable management
    "prometheus-client>=0.16.0", # Metrics for monitoring
    "cryptography>=40.0.0", # For AES-256 encryption
    "psutil>=5.9.0",       # For system resource monitoring
    "requests>=2.28.0",    # HTTP client
]

# Get the long description - create a placeholder if README.md doesn't exist yet
try:
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "OCR Service microservice for Merchant Cash Advance Application Processing System"

setup(
    name="ocr-service",
    version="0.1.0",
    description="OCR Service microservice for Merchant Cash Advance Application Processing System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Dollar Funding",
    author_email="tech@dollarfunding.com",
    url="https://github.com/dollarfunding/ocr-service",
    packages=find_packages(where="src"),
    package_dir={"":"src"},
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "isort>=5.12.0",
            "mypy>=1.3.0",
            "flake8>=6.0.0",
        ],
        "gpu": [
            "tensorflow-gpu==2.15.0",  # GPU-specific TensorFlow package
        ],
    },
    entry_points={
        "console_scripts": [
            "ocr-service=ocr_service.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
    ],
    keywords="ocr, tensorflow, machine-learning, document-processing, microservice, merchant-cash-advance",
    project_urls={
        "Bug Reports": "https://github.com/dollarfunding/ocr-service/issues",
        "Source": "https://github.com/dollarfunding/ocr-service",
        "Documentation": "https://github.com/dollarfunding/ocr-service/docs",
    },
)