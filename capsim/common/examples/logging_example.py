"""
Example of using CAPSIM 2.0 structured logging.
"""

import asyncio
from structlog import get_logger
from capsim.common.logging_config import setup_logging, bind_correlation_id
from capsim.common.metrics import track_event_processing, update_queue_metrics

# Setup logging
setup_logging(level="INFO", enable_json=True)
logger = get_logger(__name__)


@track_event_processing("simulation_step")
async def process_simulation_step(step_id: int, agents: list):
    """Example function with event processing metrics."""
    correlation_id = bind_correlation_id()
    
    logger.info(
        "Processing simulation step",
        step_id=step_id,
        agent_count=len(agents),
        correlation_id=correlation_id
    )
    
    # Simulate some work
    await asyncio.sleep(0.1)
    
    # Update queue metrics example
    queue_length = len(agents) * 2  # Simulate queue
    update_queue_metrics(queue_length, wait_time=0.05)
    
    logger.info(
        "Simulation step completed",
        step_id=step_id,
        processing_time_ms=100,
        correlation_id=correlation_id
    )
    
    return {"step_id": step_id, "processed_agents": len(agents)}


async def main():
    """Example main function."""
    logger.info("Starting simulation example")
    
    try:
        # Process multiple steps
        for step in range(1, 4):
            result = await process_simulation_step(step, [f"agent_{i}" for i in range(10)])
            logger.info("Step result", result=result)
            
    except Exception as e:
        logger.error("Simulation failed", error=str(e), exc_info=True)
    
    logger.info("Simulation example completed")


if __name__ == "__main__":
    asyncio.run(main()) 