"""
Structured logging configuration for CAPSIM 2.0.
JSON format for stdout with proper log levels and correlation IDs.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from structlog import get_logger


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
            
        # Add extra fields
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    enable_json: bool = True,
    correlation_id: Optional[str] = None
) -> None:
    """Setup structured logging configuration."""
    
    # Clear existing handlers
    logging.root.handlers.clear()
    
    # Setup handler
    handler = logging.StreamHandler(sys.stdout)
    
    if enable_json:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    # Configure root logger
    logging.root.addHandler(handler)
    logging.root.setLevel(getattr(logging, level.upper()))
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if enable_json else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set correlation ID if provided
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def get_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid4())


def bind_correlation_id(correlation_id: str = None) -> str:
    """Bind correlation ID to current context."""
    if not correlation_id:
        correlation_id = get_correlation_id()
    
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    return correlation_id


# Initialize logger
logger = get_logger(__name__) 