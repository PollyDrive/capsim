"""
Database operations logger for CAPSIM 2.0.
Tracks all INSERT operations for real-time monitoring.
"""

import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from structlog import get_logger
    STRUCTLOG_AVAILABLE = True
except ImportError:
    import logging
    STRUCTLOG_AVAILABLE = False

# Use structlog if available, otherwise standard logging
if STRUCTLOG_AVAILABLE:
    logger = get_logger(__name__)
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class DatabaseLogger:
    """Logger for database operations with special focus on INSERT operations."""
    
    def __init__(self, service_name: str = "capsim-db"):
        self.service_name = service_name
        
    def log_insert(
        self, 
        table_name: str, 
        entity_type: str, 
        entity_id: str, 
        data: Dict[str, Any], 
        correlation_id: Optional[str] = None,
        simulation_id: Optional[str] = None
    ):
        """Log INSERT operation with detailed metadata."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        log_data = {
            "timestamp": timestamp,
            "operation": "INSERT",
            "table_name": table_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "service": self.service_name,
            "correlation_id": correlation_id,
            "simulation_id": simulation_id,
            "data_size": len(json.dumps(data)) if data else 0,
            "fields": list(data.keys()) if data else []
        }
        
        if STRUCTLOG_AVAILABLE:
            logger.info(
                f"INSERT {entity_type} into {table_name}",
                **log_data
            )
        else:
            # Fallback to standard logging with JSON format
            log_message = json.dumps({
                "level": "INFO",
                "message": f"INSERT {entity_type} into {table_name}",
                **log_data
            })
            logger.info(log_message)
    
    def log_agent_action(
        self, 
        agent_id: str, 
        action_type: str, 
        action_data: Dict[str, Any],
        simulation_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Log agent action with detailed metadata."""
        self.log_insert(
            table_name="agent_actions",
            entity_type="agent_action",
            entity_id=f"{agent_id}_{int(time.time())}",
            data={
                "agent_id": agent_id,
                "action_type": action_type,
                "action_timestamp": datetime.utcnow().isoformat(),
                **action_data
            },
            correlation_id=correlation_id,
            simulation_id=simulation_id
        )
    
    def log_simulation_event(
        self,
        simulation_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """Log simulation event."""
        self.log_insert(
            table_name="simulation_events",
            entity_type="simulation_event", 
            entity_id=f"{simulation_id}_{event_type}_{int(time.time())}",
            data={
                "simulation_id": simulation_id,
                "event_type": event_type,
                "event_timestamp": datetime.utcnow().isoformat(),
                **event_data
            },
            correlation_id=correlation_id,
            simulation_id=simulation_id
        )
    
    def log_trend_update(
        self,
        trend_id: str,
        update_type: str,
        trend_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """Log trend update."""
        self.log_insert(
            table_name="trend_updates",
            entity_type="trend_update",
            entity_id=f"{trend_id}_{int(time.time())}",
            data={
                "trend_id": trend_id,
                "update_type": update_type,
                "update_timestamp": datetime.utcnow().isoformat(),
                **trend_data
            },
            correlation_id=correlation_id
        )
    
    def log_batch_operation(
        self,
        batch_id: str,
        operation_type: str,
        batch_size: int,
        affected_tables: list,
        correlation_id: Optional[str] = None
    ):
        """Log batch operation."""
        self.log_insert(
            table_name="batch_operations",
            entity_type="batch_operation",
            entity_id=batch_id,
            data={
                "batch_id": batch_id,
                "operation_type": operation_type,
                "batch_size": batch_size,
                "affected_tables": affected_tables,
                "operation_timestamp": datetime.utcnow().isoformat()
            },
            correlation_id=correlation_id
        )


# Global instance
db_logger = DatabaseLogger()


# Convenience functions
def log_agent_action(agent_id: str, action_type: str, action_data: Dict[str, Any], **kwargs):
    """Log agent action."""
    db_logger.log_agent_action(agent_id, action_type, action_data, **kwargs)


def log_simulation_event(simulation_id: str, event_type: str, event_data: Dict[str, Any], **kwargs):
    """Log simulation event."""
    db_logger.log_simulation_event(simulation_id, event_type, event_data, **kwargs)


def log_trend_update(trend_id: str, update_type: str, trend_data: Dict[str, Any], **kwargs):
    """Log trend update."""
    db_logger.log_trend_update(trend_id, update_type, trend_data, **kwargs)


def log_batch_operation(batch_id: str, operation_type: str, batch_size: int, affected_tables: list, **kwargs):
    """Log batch operation."""
    db_logger.log_batch_operation(batch_id, operation_type, batch_size, affected_tables, **kwargs) 