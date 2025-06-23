"""
Simplified FastAPI application for CAPSIM 2.0 REST API with basic metrics.
"""

import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

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

# Basic metrics if available
if METRICS_AVAILABLE:
    # Request metrics
    REQUEST_COUNT = Counter(
        'capsim_http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    REQUEST_DURATION = Histogram(
        'capsim_http_request_duration_seconds',
        'HTTP request duration',
        ['method', 'endpoint']
    )
    
    # Basic simulation metrics
    SIMULATION_COUNT = Gauge(
        'capsim_simulations_active',
        'Number of active simulations'
    )
    
    # Initialize with some test values
    SIMULATION_COUNT.set(0)
    REQUEST_COUNT.labels('GET', '/healthz', 'success').inc(0)


@app.on_event("startup")
async def startup_event():
    """Application startup handler."""
    print("CAPSIM 2.0 API starting up - simplified version")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    print("CAPSIM 2.0 API shutting down")


@app.get("/healthz", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    if METRICS_AVAILABLE:
        REQUEST_COUNT.labels('GET', '/healthz', 'success').inc()
    
    return {"status": "ok", "version": "2.0.0", "service": "capsim-api", "metrics": METRICS_AVAILABLE}


@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    if not METRICS_AVAILABLE:
        return {"error": "Prometheus client not available"}
    
    # Update some test metrics
    SIMULATION_COUNT.set(1)  # Test value
    REQUEST_COUNT.labels('GET', '/metrics', 'success').inc()
    
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with basic service info."""
    return {
        "service": "CAPSIM 2.0 API",
        "version": "2.0.0",
        "description": "Agent-based discrete event simulation platform",
        "status": "simplified version",
        "metrics_available": METRICS_AVAILABLE,
        "endpoints": {
            "health": "/healthz",
            "metrics": "/metrics",
            "simulate": "/simulate/demo",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.post("/simulate/demo", tags=["Demo"])
async def simulate_demo():
    """Demo endpoint to generate sample agent actions for log monitoring."""
    import random
    import time
    from datetime import datetime
    
    # Import db_logger
    try:
        from capsim.common.db_logger import log_agent_action, log_simulation_event, log_batch_operation
        DB_LOGGER_AVAILABLE = True
    except ImportError:
        DB_LOGGER_AVAILABLE = False
    
    if not DB_LOGGER_AVAILABLE:
        return {"error": "Database logger not available"}
    
    # Generate demo data
    simulation_id = f"sim_{int(time.time())}"
    agent_count = random.randint(3, 8)
    
    # Log simulation start
    log_simulation_event(
        simulation_id=simulation_id,
        event_type="simulation_started",
        event_data={
            "agent_count": agent_count,
            "start_time": datetime.utcnow().isoformat()
        }
    )
    
    # Generate agent actions
    actions = []
    for i in range(agent_count):
        agent_id = f"agent_{i+1}"
        action_type = random.choice(["move", "interact", "decide", "communicate"])
        
        action_data = {
            "position": {"x": random.randint(0, 100), "y": random.randint(0, 100)},
            "energy": random.randint(10, 100),
            "score": round(random.uniform(0, 1), 3),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        log_agent_action(
            agent_id=agent_id,
            action_type=action_type,
            action_data=action_data,
            simulation_id=simulation_id
        )
        
        actions.append({
            "agent_id": agent_id,
            "action_type": action_type,
            "data": action_data
        })
    
    # Log batch operation
    log_batch_operation(
        batch_id=f"batch_{simulation_id}",
        operation_type="agent_actions_batch",
        batch_size=agent_count,
        affected_tables=["agent_actions", "simulation_events"]
    )
    
    # Update metrics if available
    if METRICS_AVAILABLE:
        SIMULATION_COUNT.set(1)
        REQUEST_COUNT.labels('POST', '/simulate/demo', 'success').inc()
    
    return {
        "status": "demo_completed",
        "simulation_id": simulation_id,
        "agent_count": agent_count,
        "actions_generated": len(actions),
        "message": "Check Grafana logs to see real-time agent actions!"
    }


if __name__ == "__main__":
    print("Starting CAPSIM 2.0 API server - simplified version")
    uvicorn.run(app, host="0.0.0.0", port=8000) 