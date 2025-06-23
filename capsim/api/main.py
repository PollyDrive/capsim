"""
FastAPI application for CAPSIM 2.0 REST API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="CAPSIM 2.0 API",
    description="Agent-based discrete event simulation platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    # TODO: Implement Prometheus metrics collection
    return {"message": "Metrics endpoint - TODO: implement"}


# TODO: Add simulation management routes
# TODO: Add agent management routes  
# TODO: Add trend management routes

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 