"""
FastAPI middleware for logging and metrics collection.
"""

import time
import psutil
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from capsim.common.logging_config import bind_correlation_id
from capsim.common.metrics import (
    REQUEST_COUNT, REQUEST_DURATION, update_resource_metrics
)

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation IDs."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID
        correlation_id = str(uuid4())
        bind_correlation_id(correlation_id)
        
        # Log request
        start_time = time.time()
        
        logger.info(
            "HTTP request started",
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
            correlation_id=correlation_id
        )
        
        try:
            response = await call_next(request)
            status = "success"
            
            # Log successful response
            duration = time.time() - start_time
            logger.info(
                "HTTP request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id
            )
            
        except Exception as e:
            status = "error"
            duration = time.time() - start_time
            
            # Log error response
            logger.error(
                "HTTP request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id
            )
            raise
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for Prometheus metrics collection."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics for metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
            
        start_time = time.time()
        method = request.method
        endpoint = request.url.path
        status = "success"
        
        try:
            response = await call_next(request)
            
            # Determine status based on response code
            if response.status_code >= 400:
                status = "error"
                
            return response
            
        except Exception:
            status = "error"
            raise
            
        finally:
            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)


class ResourceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to periodically update resource metrics."""
    
    def __init__(self, app, update_interval: int = 10):
        super().__init__(app)
        self.update_interval = update_interval
        self.last_update = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Update resource metrics periodically
        current_time = time.time()
        if current_time - self.last_update > self.update_interval:
            try:
                # Get memory info
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_metrics = {
                    'rss': memory_info.rss,
                    'vms': memory_info.vms
                }
                
                # Get CPU usage
                cpu_percent = process.cpu_percent()
                
                # Update metrics
                update_resource_metrics(memory_metrics, cpu_percent)
                self.last_update = current_time
                
            except Exception as e:
                logger.warning("Failed to update resource metrics", error=str(e))
        
        return await call_next(request) 