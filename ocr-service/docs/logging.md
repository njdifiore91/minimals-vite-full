# OCR Service Logging

## Overview

The OCR Service implements comprehensive logging to track events, errors, and performance metrics throughout the document processing pipeline. This document describes the logging system and how to use it effectively.

## Logging Levels

The OCR Service uses the following log levels, as specified in section 0.2.5 of the technical specification:

- **ERROR**: Processing failures and critical issues that require immediate attention
- **WARN**: Potential issues that might lead to problems if not addressed
- **INFO**: Normal operations and significant events
- **DEBUG**: Detailed information for troubleshooting (development only)

## Structured Logging

All logs are formatted as JSON objects with the following standard fields:

- `timestamp`: ISO 8601 timestamp with UTC timezone (e.g., `2023-05-21T12:34:56.789Z`)
- `level`: Log level (ERROR, WARN, INFO, DEBUG)
- `message`: The log message
- `logger`: The name of the logger
- `module`: The module where the log was generated
- `function`: The function where the log was generated
- `line`: The line number where the log was generated
- `service`: The service name (`ocr-service`)
- `request_id`: The request ID for distributed tracing (if available)

Additional context-specific fields may be included depending on the log entry.

## Request ID Tracking

The OCR Service uses request IDs to track requests across multiple services. This enables distributed tracing and makes it easier to correlate logs from different components.

Request IDs are automatically included in all log entries when available. They can be set using the `set_request_id()` function or the `request_context()` context manager.

## Logging Configuration

Logging is configured in `src/config/logging_config.py`. The configuration includes:

- Log levels for different environments (development, staging, production)
- Log formats and handlers
- Context enrichment for request tracking

## Logging Utilities

The OCR Service provides a set of logging utilities in `src/utils/logging_utils.py` to make logging easier and more consistent:

- `configure_logger()`: Configure a logger with the specified settings
- `get_logger()`: Get a logger with context information
- `log_exception()`: Log an exception with full traceback
- `log_with_context()`: Log a message with additional context
- `set_request_id()`: Set the request ID for distributed tracing
- `get_request_id()`: Get the current request ID
- `clear_request_id()`: Clear the request ID
- `request_context()`: Context manager for setting and clearing request ID
- `log_function_call()`: Decorator to log function calls with arguments and return values
- `log_execution_time()`: Decorator to log function execution time
- `log_critical_error()`: Log a critical error with full context and notify monitoring systems

## Best Practices

1. **Use the appropriate log level**: Use ERROR for failures, WARN for potential issues, INFO for normal operations, and DEBUG for troubleshooting.

2. **Include context information**: Add relevant context to log entries to make them more useful for troubleshooting.

3. **Use request IDs**: Always use request IDs to correlate logs across services.

4. **Log exceptions properly**: Use `log_exception()` to log exceptions with full tracebacks.

5. **Be consistent**: Use the provided logging utilities consistently throughout the service.

6. **Don't log sensitive information**: Never log sensitive information like passwords, API keys, or personal data.

7. **Use structured logging**: Always use structured logging to make logs easier to parse and analyze.

## Example

```python
from src.utils.logging_utils import configure_logger, request_context, log_exception

# Configure the logger
logger = configure_logger("ocr_service.document_processor")

# Process a document with request ID tracking
with request_context("req-abc-123"):
    logger.info("Processing document", extra={"document_id": "doc-123"})
    
    try:
        # Process the document
        result = process_document("doc-123")
        logger.info("Document processed successfully", extra={"result": result})
    except Exception as e:
        log_exception(logger, "Error processing document", extra={"document_id": "doc-123"})
```

## Monitoring and Alerting

Critical errors logged with `log_critical_error()` are flagged for monitoring systems. These logs include an `alert` field set to `true` and can be used to trigger alerts in monitoring systems like Datadog.

## Log Storage and Retention

Logs are stored according to the following policy:

- Development: Console output only
- Staging: Console output and log files with 7-day retention
- Production: Console output and log files with 30-day retention, plus archival storage for 7 years

## Troubleshooting

If you're having trouble with logging:

1. Check the log level: Make sure the log level is set appropriately for your environment.
2. Check the logger name: Make sure you're using the correct logger name.
3. Check the log format: Make sure the log format is configured correctly.
4. Check the log handlers: Make sure the log handlers are configured correctly.

## References

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Structured Logging Best Practices](https://www.datadoghq.com/blog/python-logging-best-practices/)