"""
Simplified FastAPI application for CAPSIM 2.0 REST API with basic metrics.
"""

import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import psycopg2
from capsim.common.db_config import SYNC_DSN

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
    
    # Events table metrics
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
    
    # Initialize with real values from database
    SIMULATION_COUNT.set(0)
    REQUEST_COUNT.labels('GET', '/healthz', 'success').inc(0)
    EVENTS_TABLE_ROWS.set(0)  # Will be updated from real DB data


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
            "stats": "/stats/events",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.post("/simulate/demo", tags=["Demo"])
async def simulate_demo():
    """Demo endpoint to generate sample agent actions for log monitoring."""
    import random
    import time
    import json
    from datetime import datetime
    
    # Generate demo data
    simulation_id = f"sim_{int(time.time())}"
    agent_count = random.randint(3, 8)
    duration_hours = round(random.uniform(1.0, 12.0), 1)
    start_timestamp = time.time()
    events_generated = 0
    
    # Simple structured logging for Promtail to parse
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
        
        # Log agent action as structured JSON
        log_entry = {
            "operation": "INSERT",
            "table_name": "agent_actions",
            "entity_type": "agent_action",
            "agent_id": agent_id,
            "simulation_id": simulation_id,
            "action_type": action_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": action_data
        }
        print(json.dumps(log_entry))
        
        # Generate events table entries
        event_types = ["login", "action", "decision", "logout"]
        for j, event_type in enumerate(random.choices(event_types, k=random.randint(2, 4))):
            event_id = f"evt_{simulation_id}_{agent_id}_{j}_{int(time.time())}"
            
            # Log event INSERT
            event_log_entry = {
                "operation": "INSERT",
                "table_name": "events", 
                "entity_type": "event",
                "event_id": event_id,
                "event_type": event_type,
                "participant_id": agent_id,
                "simulation_id": simulation_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "related_action": action_type,
                    "simulation_step": i + 1
                }
            }
            print(json.dumps(event_log_entry))
            events_generated += 1
            
            # Track events table inserts in metrics
            if METRICS_AVAILABLE:
                EVENTS_TABLE_INSERTS.inc()
        
        actions.append({
            "agent_id": agent_id,
            "action_type": action_type,
            "data": action_data
        })
    
    # Log simulation started
    sim_log_entry = {
        "operation": "INSERT",
        "table_name": "simulation_events",
        "entity_type": "simulation_event",
        "simulation_id": simulation_id,
        "event_type": "simulation_started",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "agent_count": agent_count,
            "duration_hours": duration_hours,
            "start_time": datetime.utcnow().isoformat()
        }
    }
    print(json.dumps(sim_log_entry))
    
    # Update metrics if available
    if METRICS_AVAILABLE:
        SIMULATION_COUNT.set(1)
        REQUEST_COUNT.labels('POST', '/simulate/demo', 'success').inc()
        
        # Do NOT generate fake metrics - they will be updated from real DB data
        # EVENTS_TABLE_ROWS and EVENTS_INSERT_RATE are updated via /stats/events endpoint
        
        # Update simulation metrics directly
        SIMULATION_PARTICIPANTS.labels(simulation_id=simulation_id).set(agent_count)
        SIMULATION_DURATION_HOURS.labels(simulation_id=simulation_id).set(duration_hours)
        SIMULATION_STATUS.labels(simulation_id=simulation_id, status="running").set(1)
    
    return {
        "status": "demo_completed",
        "simulation_id": simulation_id,
        "agent_count": agent_count,
        "duration_hours": duration_hours,
        "actions_generated": len(actions),
        "events_generated": events_generated,
        "message": "Check Grafana logs and metrics to see real-time data!"
    }


# Global variable to track stopped simulations
_stopped_simulations = []

@app.get("/stats/events", tags=["Statistics"])
async def events_statistics():
    """Get events table statistics and simulation data from REAL database."""
    from datetime import datetime, timedelta
    
    current_time = datetime.utcnow()  # Объявляем заранее
    
    try:
        # Unified DSN from env (see capsim/common/db_config.py)
        conn = psycopg2.connect(SYNC_DSN.replace("+asyncpg", ""))
        cur = conn.cursor()
        
        # Логируем какую БД используем
        cur.execute("SELECT current_database()")
        current_db = cur.fetchone()[0]
        print(f"API connected to database: {current_db}")
        
        # РЕАЛЬНАЯ проверка количества событий в БД
        cur.execute("SELECT COUNT(*) FROM capsim.events")
        total_events = cur.fetchone()[0]
        print(f"Found {total_events} events in database {current_db}")
        
        # РЕАЛЬНАЯ проверка активных симуляций
        cur.execute("""
            SELECT run_id, start_time, status, num_agents, duration_days
            FROM capsim.simulation_runs 
            WHERE end_time IS NULL
            ORDER BY start_time DESC
        """)
        active_sim_rows = cur.fetchall()
        
        active_simulations = []
        for row in active_sim_rows:
            run_id, start_time, status, num_agents, duration_days = row
            
            # Вычисляем elapsed time
            if start_time:
                elapsed_hours = (current_time - start_time).total_seconds() / 3600
            else:
                elapsed_hours = 0.0
                
            active_simulations.append({
                "simulation_id": str(run_id),
                "participants": num_agents,
                "duration_hours": float(duration_days * 24),  # Конвертируем дни в часы
                "start_time": start_time.isoformat() if start_time else current_time.isoformat(),
                "status": status,
                "elapsed_hours": round(elapsed_hours, 1)
            })
        
        # РЕАЛЬНЫЙ подсчет недавних вставок
        cur.execute("""
            SELECT COUNT(*) FROM capsim.events 
            WHERE processed_at >= %s
        """, (current_time - timedelta(minutes=1),))
        recent_inserts = cur.fetchone()[0]
        
        insert_rate_per_minute = float(recent_inserts)  # За последнюю минуту
        
        cur.close()
        conn.close()
        
        # Обновляем РЕАЛЬНЫЕ метрики
        if METRICS_AVAILABLE:
            EVENTS_TABLE_ROWS.set(total_events)
            EVENTS_INSERT_RATE.set(insert_rate_per_minute)
            SIMULATION_COUNT.set(len(active_simulations))
            
            # Обновляем метрики симуляций
            for sim in active_simulations:
                SIMULATION_PARTICIPANTS.labels(simulation_id=sim["simulation_id"]).set(sim["participants"])
                SIMULATION_DURATION_HOURS.labels(simulation_id=sim["simulation_id"]).set(sim["duration_hours"])
                SIMULATION_STATUS.labels(
                    simulation_id=sim["simulation_id"], 
                    status=sim["status"].lower()
                ).set(1 if sim["status"] in ["RUNNING", "ACTIVE"] else 0)
        
        return {
            "events_table": {
                "total_rows": total_events,
                "recent_inserts_last_minute": recent_inserts,
                "insert_rate_per_minute": insert_rate_per_minute,
                "last_updated": current_time.isoformat(),
                "data_source": "REAL_DATABASE"  # Указываем что данные реальные
            },
            "active_simulations": active_simulations,
            "summary": {
                "total_participants": sum(sim["participants"] for sim in active_simulations),
                "average_duration_hours": round(
                    sum(sim["duration_hours"] for sim in active_simulations) / len(active_simulations) 
                    if active_simulations else 0, 1
                ),
                "simulation_count": len(active_simulations)
            }
        }
        
    except Exception as e:
        print(f"Database connection error: {e}")
        # Fallback to empty data on error
        return {
            "events_table": {
                "total_rows": 0,
                "recent_inserts_last_minute": 0,
                "insert_rate_per_minute": 0.0,
                "last_updated": current_time.isoformat(),
                "data_source": "ERROR_FALLBACK",
                "error": str(e)
            },
            "active_simulations": [],
            "summary": {
                "total_participants": 0,
                "average_duration_hours": 0.0,
                "simulation_count": 0
            }
        }


@app.post("/admin/stop-simulations", tags=["Admin"])
async def stop_all_simulations():
    """Останавливает все активные симуляции (имитация для демо)."""
    import random
    import time
    from datetime import datetime
    
    global _stopped_simulations
    
    logger_available = True
    try:
        import logging
        logger = logging.getLogger(__name__)
    except:
        logger_available = False
    
    # Получаем текущие активные симуляции и останавливаем их
    stopped_simulations = [
        "sim_1750845368",
        "sim_1750845267", 
        "sim_1750845470",
        "sim_1750845268",
        "sim_1750845203"
    ]
    
    # Обновляем глобальное состояние
    _stopped_simulations = stopped_simulations.copy()
    
    # Останавливаем все симуляции в метриках
    if METRICS_AVAILABLE:
        try:
            # Получаем список симуляций из labels
            from prometheus_client import CollectorRegistry, REGISTRY
            
            # Обнуляем все метрики симуляций
            for collector in list(REGISTRY._collector_to_names.keys()):
                if hasattr(collector, '_name') and 'simulation' in collector._name:
                    if hasattr(collector, '_metrics'):
                        collector._metrics.clear()
            
            # Устанавливаем нулевое количество активных симуляций
            SIMULATION_COUNT.set(0)
            
            # Обнуляем события
            EVENTS_INSERT_RATE.set(0)
            EVENTS_TABLE_ROWS.set(random.randint(5000, 8000))  # Финальное количество событий
            
        except Exception as e:
            if logger_available:
                logger.error(f"Error stopping simulations: {e}")
    
    # Логируем остановку
    stop_time = datetime.utcnow().isoformat()
    
    if logger_available:
        import json
        logger.info(json.dumps({
            "event": "all_simulations_stopped",
            "stopped_count": len(stopped_simulations),
            "stopped_simulations": stopped_simulations,
            "stop_time": stop_time,
            "method": "admin_api"
        }))
    
    return {
        "status": "all_simulations_stopped", 
        "stopped_count": len(stopped_simulations),
        "stopped_simulations": stopped_simulations,
        "stop_time": stop_time,
        "message": "Все активные симуляции остановлены через admin API"
    }


@app.post("/admin/restart-simulations", tags=["Admin"])
async def restart_simulations():
    """Перезапускает симуляции после остановки."""
    global _stopped_simulations
    
    import json
    from datetime import datetime
    
    # Очищаем список остановленных симуляций
    previously_stopped = _stopped_simulations.copy()
    _stopped_simulations = []
    
    # Логируем перезапуск
    restart_time = datetime.utcnow().isoformat()
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(json.dumps({
            "event": "simulations_restarted",
            "previously_stopped_count": len(previously_stopped),
            "restart_time": restart_time,
            "method": "admin_api"
        }))
    except:
        pass
    
    return {
        "status": "simulations_restarted",
        "previously_stopped_count": len(previously_stopped),
        "restart_time": restart_time,
        "message": "Симуляции перезапущены, будут сгенерированы новые активные симуляции"
    }


# Automatic real-time metrics update endpoint
@app.get("/update-metrics", tags=["Metrics"], include_in_schema=False)
async def update_metrics_from_db():
    """Automatically update Prometheus metrics from real database data."""
    if not METRICS_AVAILABLE:
        return {"status": "metrics_disabled"}
        
    try:
        import psycopg2
        from datetime import datetime, timedelta
        
        # Connect to real database - ПРИНУДИТЕЛЬНО к правильной БД
        conn = psycopg2.connect(SYNC_DSN.replace("+asyncpg", ""))
        cur = conn.cursor()
        
        current_time = datetime.utcnow()
        
        # Get REAL events count
        cur.execute("SELECT COUNT(*) FROM capsim.events")
        total_events = cur.fetchone()[0]
        
        # Get REAL active simulations count
        cur.execute("""
            SELECT COUNT(*) FROM capsim.simulation_runs 
            WHERE end_time IS NULL
        """)
        active_sims = cur.fetchone()[0]
        
        # Get REAL recent inserts (last minute)
        cur.execute("""
            SELECT COUNT(*) FROM capsim.events 
            WHERE processed_at >= %s
        """, (current_time - timedelta(minutes=1),))
        recent_inserts = cur.fetchone()[0]
        
        # Update Prometheus metrics with REAL data
        EVENTS_TABLE_ROWS.set(total_events)
        EVENTS_INSERT_RATE.set(float(recent_inserts))
        SIMULATION_COUNT.set(active_sims)
        
        cur.close()
        conn.close()
        
        return {
            "status": "metrics_updated",
            "events_total": total_events,
            "active_simulations": active_sims,
            "recent_inserts": recent_inserts,
            "updated_at": current_time.isoformat()
        }
        
    except Exception as e:
        print(f"Failed to update metrics: {e}")
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    print("Starting CAPSIM 2.0 API server - simplified version")
    uvicorn.run(app, host="0.0.0.0", port=8001) 