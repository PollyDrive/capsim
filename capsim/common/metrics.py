"""
Prometheus metrics for CAPSIM 2.0 monitoring.
Includes request metrics, queue metrics, simulation metrics.
"""

import time
from functools import wraps
from typing import Callable, Dict, Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from structlog import get_logger

logger = get_logger(__name__)

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

# Event processing metrics
EVENT_LATENCY = Histogram(
    'capsim_event_latency_ms',
    'Event processing latency in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

EVENT_COUNT = Counter(
    'capsim_events_processed_total',
    'Total events processed',
    ['event_type', 'status']
)

# Database table metrics
EVENTS_TABLE_INSERTS = Counter(
    'capsim_events_table_inserts_total',
    'Total INSERT operations into events table'
)

EVENTS_TABLE_ROWS = Gauge(
    'capsim_events_table_rows_total',
    'Total number of rows in events table'
)

EVENTS_INSERT_RATE = Gauge(
    'capsim_events_insert_rate_per_minute',
    'INSERT operations per minute into events table'
)

# Simulation tracking metrics
SIMULATION_PARTICIPANTS = Gauge(
    'capsim_simulation_participants_total',
    'Total number of participants in active simulations',
    ['simulation_id']
)

SIMULATION_DURATION_HOURS = Gauge(
    'capsim_simulation_duration_hours',
    'Duration of simulations in hours',
    ['simulation_id']
)

SIMULATION_STATUS = Gauge(
    'capsim_simulation_status',
    'Status of simulations (1=running, 0=stopped)',
    ['simulation_id', 'status']
)

SIMULATION_START_TIME = Gauge(
    'capsim_simulation_start_timestamp',
    'Start timestamp of simulations',
    ['simulation_id']
)

# Queue metrics
QUEUE_LENGTH = Gauge(
    'capsim_queue_length',
    'Current event queue length'
)

QUEUE_WAIT_TIME = Histogram(
    'capsim_queue_wait_time_seconds',
    'Time events spend in queue'
)

# Batch processing metrics
BATCH_SIZE = Histogram(
    'capsim_batch_size',
    'Size of processed batches',
    buckets=[10, 25, 50, 100, 250, 500, 1000]
)

BATCH_COMMIT_ERRORS = Counter(
    'capsim_batch_commit_errors_total',
    'Total batch commit errors'
)

BATCH_PROCESSING_TIME = Histogram(
    'capsim_batch_processing_seconds',
    'Time to process batches'
)

# Database metrics
DB_CONNECTIONS_ACTIVE = Gauge(
    'capsim_db_connections_active',
    'Active database connections'
)

DB_QUERY_DURATION = Histogram(
    'capsim_db_query_duration_seconds',
    'Database query duration',
    ['query_type']
)

# Simulation metrics
SIMULATION_COUNT = Gauge(
    'capsim_simulations_active',
    'Number of active simulations'
)

AGENT_COUNT = Gauge(
    'capsim_agents_total',
    'Total number of agents',
    ['simulation_id']
)

STEP_DURATION = Histogram(
    'capsim_simulation_step_duration_seconds',
    'Simulation step duration',
    ['simulation_id']
)

# Memory and resource metrics
MEMORY_USAGE = Gauge(
    'capsim_memory_usage_bytes',
    'Memory usage in bytes',
    ['type']  # heap, rss, etc.
)

CPU_USAGE = Gauge(
    'capsim_cpu_usage_percent',
    'CPU usage percentage'
)


def track_request_metrics(func: Callable) -> Callable:
    """Decorator to track HTTP request metrics."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        method = kwargs.get('method', 'GET')
        endpoint = func.__name__
        
        start_time = time.time()
        status = 'success'
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = 'error'
            logger.error("Request failed", endpoint=endpoint, error=str(e))
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            
    return wrapper


def track_event_processing(event_type: str):
    """Decorator to track event processing metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                logger.error("Event processing failed", event_type=event_type, error=str(e))
                raise
            finally:
                duration = (time.time() - start_time) * 1000  # Convert to ms
                EVENT_LATENCY.observe(duration)
                EVENT_COUNT.labels(event_type=event_type, status=status).inc()
                
        return wrapper
    return decorator


def track_batch_processing(func: Callable) -> Callable:
    """Decorator to track batch processing metrics."""
    @wraps(func)
    async def wrapper(batch, *args, **kwargs):
        batch_size = len(batch) if hasattr(batch, '__len__') else 1
        start_time = time.time()
        
        try:
            result = await func(batch, *args, **kwargs)
            BATCH_SIZE.observe(batch_size)
            return result
        except Exception as e:
            BATCH_COMMIT_ERRORS.inc()
            logger.error("Batch processing failed", batch_size=batch_size, error=str(e))
            raise
        finally:
            duration = time.time() - start_time
            BATCH_PROCESSING_TIME.observe(duration)
            
    return wrapper


def track_db_query(query_type: str):
    """Decorator to track database query metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)
                
        return wrapper
    return decorator


def update_queue_metrics(queue_length: int, wait_time: float = None):
    """Update queue-related metrics."""
    QUEUE_LENGTH.set(queue_length)
    if wait_time is not None:
        QUEUE_WAIT_TIME.observe(wait_time)


def update_db_connections(active_count: int):
    """Update database connection metrics."""
    DB_CONNECTIONS_ACTIVE.set(active_count)


def update_simulation_metrics(
    active_simulations: int,
    agent_counts: Dict[str, int] = None,
    step_durations: Dict[str, float] = None
):
    """Update simulation-related metrics."""
    SIMULATION_COUNT.set(active_simulations)
    
    if agent_counts:
        for sim_id, count in agent_counts.items():
            AGENT_COUNT.labels(simulation_id=sim_id).set(count)
            
    if step_durations:
        for sim_id, duration in step_durations.items():
            STEP_DURATION.labels(simulation_id=sim_id).observe(duration)


def update_resource_metrics(memory_bytes: Dict[str, int], cpu_percent: float):
    """Update resource usage metrics."""
    for mem_type, value in memory_bytes.items():
        MEMORY_USAGE.labels(type=mem_type).set(value)
    CPU_USAGE.set(cpu_percent)


# New functions for events table tracking
def track_events_table_insert():
    """Track INSERT operation into events table."""
    EVENTS_TABLE_INSERTS.inc()


def update_events_table_metrics(total_rows: int, insert_rate_per_minute: float):
    """Update events table metrics."""
    EVENTS_TABLE_ROWS.set(total_rows)
    EVENTS_INSERT_RATE.set(insert_rate_per_minute)


def update_simulation_tracking(
    simulation_id: str,
    participants: int,
    duration_hours: float,
    status: str,
    start_timestamp: float = None
):
    """Update simulation tracking metrics."""
    SIMULATION_PARTICIPANTS.labels(simulation_id=simulation_id).set(participants)
    SIMULATION_DURATION_HOURS.labels(simulation_id=simulation_id).set(duration_hours)
    
    # Set status (1 for running, 0 for stopped)
    status_value = 1 if status == 'running' else 0
    SIMULATION_STATUS.labels(simulation_id=simulation_id, status=status).set(status_value)
    
    if start_timestamp:
        SIMULATION_START_TIME.labels(simulation_id=simulation_id).set(start_timestamp)


def get_metrics() -> str:
    """Generate Prometheus metrics output."""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Get the content type for metrics endpoint."""
    return CONTENT_TYPE_LATEST 