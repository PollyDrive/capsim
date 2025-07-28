"""
Prometheus metrics for CAPSIM 2.0 monitoring.
Includes request metrics, queue metrics, simulation metrics.
"""

import time
from functools import wraps
from typing import Callable, Dict, Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

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

# v2.0: Economic balance metrics
ECONOMIC_BALANCE_METRICS = {
    'avg_financial_capability': Gauge(
        'capsim_avg_financial_capability_by_profession',
        'Average financial capability by profession',
        ['profession']
    ),
    'daily_income_total': Counter(
        'capsim_daily_income_total',
        'Total daily income distributed',
        ['profession']
    ),
    'daily_expenses_total': Counter(
        'capsim_daily_expenses_total', 
        'Total daily expenses deducted',
        ['profession']
    ),
    'energy_recovery_events': Counter(
        'capsim_energy_recovery_events_total',
        'Total energy recovery events processed'
    ),
    'night_recovery_success': Counter(
        'capsim_night_recovery_success_total',
        'Successful night recovery operations',
        ['recovery_type']
    ),
    'social_status_changes': Counter(
        'capsim_social_status_changes_total',
        'Social status changes tracked',
        ['change_type', 'profession']
    ),
    'economic_balance_errors': Counter(
        'capsim_economic_balance_errors_total',
        'Economic balance system errors',
        ['error_type']
    )
}

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

# Agent activity limit metrics
AGENT_DAILY_ACTIONS = Gauge(
    'capsim_agent_daily_actions',
    'Number of daily actions per agent',
    ['simulation_id', 'agent_id']
)

AGENT_HOURLY_ACTIONS = Gauge(
    'capsim_agent_hourly_actions', 
    'Number of hourly actions per agent',
    ['simulation_id', 'agent_id']
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

# v1.8: New action tracking metrics
ACTIONS_TOTAL = Counter(
    'capsim_actions_total',
    'Total actions performed by agents',
    ['action_type', 'level', 'profession']
)

AGENT_ATTRIBUTE = Gauge(
    'capsim_agent_attribute',
    'Agent attribute P95 values',
    ['attribute', 'profession']
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
    """Return metrics content type."""
    return CONTENT_TYPE_LATEST


def record_action(action_type: str, level: str = "", profession: str = ""):
    """
    Record an action performed by an agent.
    
    Args:
        action_type: Type of action (Post, Purchase, SelfDev)
        level: Purchase level (L1, L2, L3) or empty for other actions
        profession: Agent profession
    """
    ACTIONS_TOTAL.labels(
        action_type=action_type,
        level=level,
        profession=profession
    ).inc()


def update_agent_attributes(persons):
    """
    Update P95 metrics for all agent attributes.
    
    Args:
        persons: List of Person objects
    """
    import numpy as np
    from collections import defaultdict
    
    by_profession = defaultdict(lambda: defaultdict(list))
    
    for person in persons:
        prof = person.profession
        by_profession[prof]['energy_level'].append(person.energy_level)
        by_profession[prof]['financial_capability'].append(person.financial_capability)
        by_profession[prof]['trend_receptivity'].append(person.trend_receptivity)
        by_profession[prof]['social_status'].append(person.social_status)
        by_profession[prof]['time_budget'].append(person.time_budget)
        by_profession[prof]['purchases_today'].append(person.purchases_today)
    
    for prof, attributes in by_profession.items():
        for attr_name, values in attributes.items():
            if values:  # Проверяем что есть значения
                p95_value = np.percentile(values, 95)
                AGENT_ATTRIBUTE.labels(attribute=attr_name, profession=prof).set(p95_value)


# v2.0: Economic balance metrics functions
def record_daily_income(profession: str, amount: float):
    """Record daily income distributed to agents."""
    ECONOMIC_BALANCE_METRICS['daily_income_total'].labels(profession=profession).inc(amount)


def record_daily_expenses(profession: str, amount: float):
    """Record daily expenses deducted from agents."""
    ECONOMIC_BALANCE_METRICS['daily_expenses_total'].labels(profession=profession).inc(amount)


def record_energy_recovery():
    """Record energy recovery event."""
    ECONOMIC_BALANCE_METRICS['energy_recovery_events'].inc()


def record_night_recovery(recovery_type: str):
    """Record successful night recovery operation."""
    ECONOMIC_BALANCE_METRICS['night_recovery_success'].labels(recovery_type=recovery_type).inc()


def record_social_status_change(change_type: str, profession: str):
    """Record social status change."""
    ECONOMIC_BALANCE_METRICS['social_status_changes'].labels(
        change_type=change_type, 
        profession=profession
    ).inc()


def record_economic_balance_error(error_type: str):
    """Record economic balance system error."""
    ECONOMIC_BALANCE_METRICS['economic_balance_errors'].labels(error_type=error_type).inc()


def update_financial_capability_by_profession(persons):
    """Update average financial capability metrics by profession."""
    from collections import defaultdict
    
    by_profession = defaultdict(list)
    
    for person in persons:
        by_profession[person.profession].append(person.financial_capability)
    
    for profession, values in by_profession.items():
        if values:
            avg_value = sum(values) / len(values)
            ECONOMIC_BALANCE_METRICS['avg_financial_capability'].labels(
                profession=profession
            ).set(avg_value) 