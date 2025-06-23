"""
FastAPI application for CAPSIM 2.0 REST API.
"""

import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from structlog import get_logger

from capsim.common.logging_config import setup_logging
from capsim.common.metrics import get_metrics, get_metrics_content_type, update_db_connections
from capsim.api.middleware import LoggingMiddleware, MetricsMiddleware, ResourceMonitoringMiddleware

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
enable_json_logs = os.getenv("ENABLE_JSON_LOGS", "true").lower() == "true"
setup_logging(level=log_level, enable_json=enable_json_logs)

logger = get_logger(__name__)

app = FastAPI(
    title="CAPSIM 2.0 API",
    description="Agent-based discrete event simulation platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware (order matters - last added runs first)
app.add_middleware(ResourceMonitoringMiddleware, update_interval=10)
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup handler."""
    logger.info("CAPSIM 2.0 API starting up", version="2.0.0")
    
    # Initialize database connection metrics
    update_db_connections(1)  # Placeholder - will be updated by actual DB pool


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    logger.info("CAPSIM 2.0 API shutting down")


@app.get("/healthz", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    logger.debug("Health check requested")
    return {"status": "ok", "version": "2.0.0", "service": "capsim-api"}


@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    logger.debug("Metrics requested")
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type()
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with basic service info."""
    return {
        "service": "CAPSIM 2.0 API",
        "version": "2.0.0",
        "description": "Agent-based discrete event simulation platform",
        "endpoints": {
            "health": "/healthz",
            "metrics": "/metrics",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


# TODO: Add simulation management routes
# TODO: Add agent management routes  
# TODO: Add trend management routes

if __name__ == "__main__":
    logger.info("Starting CAPSIM 2.0 API server")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None  # Use our custom logging
    ) 