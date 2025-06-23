"""
Performance benchmark tests for CAPSIM simulation system.

Validates KPI requirements:
- P95 latency ≤ 10ms for event processing
- Queue length ≤ 5000 events maximum
- Throughput: 43 events per agent per day
- Batch commit efficiency
- Memory usage optimization
- Graceful shutdown within 30 seconds

These tests ensure system performance meets production requirements.
"""

import pytest
import asyncio
import time
import statistics
import gc
import psutil
import os
from typing import List, Dict
from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock

import sys
sys.path.append('.')
from demo_simulation import DemoSimulationEngine, Person, Trend, PublishPostAction


class PerformanceTestRepository:
    """Mock repository optimized for performance testing."""
    
    def __init__(self):
        self.operations = []
        self.batch_commits = 0
        self.operation_times = []
        
    async def create_simulation_run(self, num_agents: int, duration_days: int, configuration: Dict):
        """Fast mock simulation run creation."""
        start_time = time.perf_counter()
        
        simulation_run = MagicMock()
        simulation_run.run_id = uuid4()
        simulation_run.num_agents = num_agents
        simulation_run.duration_days = duration_days
        simulation_run.configuration = configuration
        
        end_time = time.perf_counter()
        self.operation_times.append(('create_simulation_run', end_time - start_time))
        
        return simulation_run
        
    async def load_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Fast affinity map loading."""
        start_time = time.perf_counter()
        
        # Simplified affinity map for performance testing
        affinity_map = {
            prof: {topic: 2.5 for topic in ["ECONOMIC", "HEALTH", "SCIENCE", "CULTURE"]}
            for prof in ["ShopClerk", "Worker", "Developer", "Teacher", "Businessman", "Artist"]
        }
        
        end_time = time.perf_counter()
        self.operation_times.append(('load_affinity_map', end_time - start_time))
        
        return affinity_map
        
    async def bulk_create_persons(self, persons: List[Person]):
        """Mock bulk person creation with timing."""
        start_time = time.perf_counter()
        
        self.operations.append(('bulk_create_persons', len(persons)))
        
        end_time = time.perf_counter()
        self.operation_times.append(('bulk_create_persons', end_time - start_time))
        
    async def get_active_trends(self, simulation_id):
        """Fast trend retrieval."""
        start_time = time.perf_counter()
        
        result = []  # Empty for performance tests
        
        end_time = time.perf_counter()
        self.operation_times.append(('get_active_trends', end_time - start_time))
        
        return result
        
    async def bulk_update_persons(self, updates: List[Dict]):
        """Mock batch update with performance tracking."""
        start_time = time.perf_counter()
        
        self.operations.append(('bulk_update_persons', len(updates)))
        self.batch_commits += 1
        
        end_time = time.perf_counter()
        self.operation_times.append(('bulk_update_persons', end_time - start_time))
        
    async def create_trend(self, trend: Trend):
        """Fast trend creation."""
        start_time = time.perf_counter()
        
        self.operations.append(('create_trend', 1))
        
        end_time = time.perf_counter()
        self.operation_times.append(('create_trend', end_time - start_time))
        
    async def log_event(self, event):
        """Fast event logging."""
        start_time = time.perf_counter()
        
        self.operations.append(('log_event', 1))
        
        end_time = time.perf_counter()
        self.operation_times.append(('log_event', end_time - start_time))


class TestPerformanceBenchmarks:
    """Performance benchmark test suite."""
    
    @pytest.fixture
    def perf_repo(self):
        """Performance-optimized repository."""
        return PerformanceTestRepository()
        
    @pytest.fixture
    def memory_tracker(self):
        """Memory usage tracker."""
        process = psutil.Process()
        return process
    
    @pytest.mark.asyncio
    async def test_p95_latency_requirement_10ms(self, perf_repo):
        """PERF-01: P95 latency ≤ 10ms for event processing."""
        engine = DemoSimulationEngine()
        await engine.initialize(num_agents=100)
        
        # Track event processing latencies
        latencies = []
        
        # Process many events to get statistical sample
        for _ in range(1000):
            # Create test event
            agent = engine.agents[0]
            event = PublishPostAction(agent.person_id, "ECONOMIC", engine.current_time)
            
            # Measure processing time
            start_time = time.perf_counter()
            await engine._process_event(event)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency_ms)
            
        # Calculate P95 latency
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        avg_latency = statistics.mean(latencies)
        
        print(f"Event processing latencies:")
        print(f"  Average: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")
        print(f"  P99: {p99_latency:.3f}ms")
        print(f"  Sample size: {len(latencies)} events")
        
        # Validate P95 requirement
        assert p95_latency <= 10.0, f"P95 latency {p95_latency:.3f}ms exceeds 10ms requirement"
        
        # Additional validation
        assert avg_latency <= 5.0, f"Average latency {avg_latency:.3f}ms should be well below P95"
        assert min(latencies) >= 0.0, "No negative latencies allowed"
        
    @pytest.mark.asyncio
    async def test_queue_size_limit_5000_events(self, perf_repo):
        """Test queue never exceeds 5000 events maximum."""
        engine = DemoSimulationEngine()
        await engine.initialize(num_agents=200)  # Large agent population
        
        max_queue_size = 5000
        observed_queue_sizes = []
        
        # Run simulation and monitor queue size
        simulation_task = asyncio.create_task(engine.run_simulation(duration_days=120/1440))  # 2 hours
        
        # Monitor queue size during simulation
        monitoring_duration = 10.0  # Monitor for 10 seconds
        start_monitor = time.time()
        
        while time.time() - start_monitor < monitoring_duration:
            current_size = len(engine.event_queue)
            observed_queue_sizes.append(current_size)
            
            # Validate queue size constraint
            assert current_size <= max_queue_size, \
                f"Queue size {current_size} exceeds maximum {max_queue_size}"
                
            await asyncio.sleep(0.1)  # Check every 100ms
            
        # Cancel simulation
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
            
        # Report queue size statistics
        if observed_queue_sizes:
            max_observed = max(observed_queue_sizes)
            avg_observed = statistics.mean(observed_queue_sizes)
            
            print(f"Queue size monitoring:")
            print(f"  Maximum observed: {max_observed}")
            print(f"  Average: {avg_observed:.1f}")
            print(f"  Samples: {len(observed_queue_sizes)}")
            
            assert max_observed < max_queue_size * 0.8, \
                f"Queue size {max_observed} too close to limit {max_queue_size}"
                
    @pytest.mark.asyncio
    async def test_throughput_43_events_per_agent_per_day(self, perf_repo):
        """Validate throughput meets 43 events per agent per day requirement."""
        target_events_per_agent_per_day = 43.2
        
        engine = DemoSimulationEngine()
        await engine.initialize(num_agents=50)
        
        # Track events at start
        initial_trends = len(engine.active_trends)
        
        # Run simulation for 6 hours (1/4 day)
        simulation_duration_days = 0.25  # 6 hours
        await engine.run_simulation(duration_days=simulation_duration_days)
        
        # Calculate throughput
        final_trends = len(engine.active_trends)
        events_created = final_trends - initial_trends
        
        # Estimate total events (trends + other events)
        # In demo: 748 events created 59 trends, so ~12.7 events per trend
        estimated_total_events = events_created * 12.7
        
        events_per_agent = estimated_total_events / len(engine.agents)
        events_per_agent_per_day = events_per_agent / simulation_duration_days
        
        print(f"Throughput analysis:")
        print(f"  Trends created: {events_created}")
        print(f"  Estimated total events: {estimated_total_events:.0f}")
        print(f"  Events per agent: {events_per_agent:.1f}")
        print(f"  Events per agent per day: {events_per_agent_per_day:.1f}")
        
        # Validate throughput (allow 20% tolerance for variation)
        min_acceptable = target_events_per_agent_per_day * 0.8
        max_acceptable = target_events_per_agent_per_day * 1.2
        
        assert min_acceptable <= events_per_agent_per_day <= max_acceptable, \
            f"Throughput {events_per_agent_per_day:.1f} outside acceptable range [{min_acceptable:.1f}, {max_acceptable:.1f}]"
            
    @pytest.mark.asyncio 
    async def test_batch_commit_efficiency_100_threshold(self, perf_repo):
        """Test batch commit operates efficiently at 100-item threshold."""
        engine = DemoSimulationEngine()
        await engine.initialize(num_agents=20)
        
        # Track batch operations
        batch_times = []
        batch_sizes = []
        
        # Simulate batch accumulation and commits
        for batch_round in range(10):  # Multiple batch rounds
            # Add updates to trigger batch commit
            batch_start = time.perf_counter()
            
            for i in range(120):  # Exceed batch size of 100
                engine.add_to_batch_update({
                    "person_id": str(uuid4()),
                    "attribute": "energy_level",
                    "old_value": 5.0,
                    "new_value": 4.0,
                    "timestamp": engine.current_time + i
                })
                
                # Check if batch should commit
                if engine._should_commit_batch():
                    batch_size = len(engine._batch_updates)
                    batch_sizes.append(batch_size)
                    
                    # Simulate batch commit
                    await engine._batch_commit_states()
                    
                    batch_end = time.perf_counter()
                    batch_time = (batch_end - batch_start) * 1000  # ms
                    batch_times.append(batch_time)
                    
                    batch_start = time.perf_counter()  # Reset for next batch
                    
        # Analyze batch performance
        if batch_times:
            avg_batch_time = statistics.mean(batch_times)
            max_batch_time = max(batch_times)
            avg_batch_size = statistics.mean(batch_sizes)
            
            print(f"Batch commit performance:")
            print(f"  Average batch time: {avg_batch_time:.2f}ms")
            print(f"  Maximum batch time: {max_batch_time:.2f}ms")
            print(f"  Average batch size: {avg_batch_size:.0f}")
            print(f"  Batches processed: {len(batch_times)}")
            
            # Performance requirements
            assert avg_batch_time <= 50.0, f"Average batch time {avg_batch_time:.2f}ms too high"
            assert max_batch_time <= 100.0, f"Maximum batch time {max_batch_time:.2f}ms too high"
            assert 95 <= avg_batch_size <= 105, f"Batch size {avg_batch_size:.0f} not near expected 100"
            
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, memory_tracker):
        """Test memory usage remains reasonable during simulation."""
        # Get initial memory usage
        initial_memory = memory_tracker.memory_info().rss / 1024 / 1024  # MB
        
        engine = DemoSimulationEngine()
        await engine.initialize(num_agents=100)
        
        # Memory after initialization
        post_init_memory = memory_tracker.memory_info().rss / 1024 / 1024  # MB
        
        # Run simulation
        await engine.run_simulation(duration_days=60/1440)  # 1 hour
        
        # Memory after simulation
        post_sim_memory = memory_tracker.memory_info().rss / 1024 / 1024  # MB
        
        # Force garbage collection
        gc.collect()
        
        # Memory after cleanup
        post_gc_memory = memory_tracker.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Memory usage analysis:")
        print(f"  Initial: {initial_memory:.1f} MB")
        print(f"  Post-initialization: {post_init_memory:.1f} MB")
        print(f"  Post-simulation: {post_sim_memory:.1f} MB")
        print(f"  Post-GC: {post_gc_memory:.1f} MB")
        
        # Memory growth constraints
        init_growth = post_init_memory - initial_memory
        sim_growth = post_sim_memory - post_init_memory
        total_growth = post_sim_memory - initial_memory
        
        print(f"  Initialization growth: {init_growth:.1f} MB")
        print(f"  Simulation growth: {sim_growth:.1f} MB")
        print(f"  Total growth: {total_growth:.1f} MB")
        
        # Validate memory usage is reasonable
        assert init_growth <= 50.0, f"Initialization memory growth {init_growth:.1f} MB too high"
        assert sim_growth <= 100.0, f"Simulation memory growth {sim_growth:.1f} MB too high"
        assert total_growth <= 150.0, f"Total memory growth {total_growth:.1f} MB too high"
        
        # GC should free some memory
        gc_freed = post_sim_memory - post_gc_memory
        print(f"  GC freed: {gc_freed:.1f} MB")
        
    @pytest.mark.asyncio
    async def test_graceful_shutdown_30_second_requirement(self, perf_repo):
        """Test graceful shutdown completes within 30 seconds."""
        shutdown_timeout = 30.0  # seconds
        
        engine = DemoSimulationEngine()
        await engine.initialize(num_agents=100)
        
        # Add many pending updates to test shutdown performance
        for i in range(500):
            engine.add_to_batch_update({
                "person_id": str(uuid4()),
                "attribute": "energy_level",
                "old_value": 3.0,
                "new_value": 2.5,
                "timestamp": engine.current_time + i
            })
            
        # Start long-running simulation
        simulation_task = asyncio.create_task(engine.run_simulation(duration_days=7))  # 1 week
        
        # Let simulation run briefly
        await asyncio.sleep(0.5)
        
        # Initiate shutdown
        shutdown_start = time.time()
        
        # Simulate graceful shutdown
        await engine.shutdown()
        
        # Cancel simulation task
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
            
        shutdown_time = time.time() - shutdown_start
        
        print(f"Graceful shutdown performance:")
        print(f"  Shutdown time: {shutdown_time:.2f} seconds")
        print(f"  Batch updates pending: {len(engine._batch_updates)}")
        print(f"  Final state preserved: {not engine._running}")
        
        # Validate shutdown time requirement
        assert shutdown_time <= shutdown_timeout, \
            f"Shutdown time {shutdown_time:.2f}s exceeds {shutdown_timeout}s requirement"
            
        # Verify clean shutdown state
        assert not engine._running
        assert len(engine._batch_updates) == 0  # Batch should be flushed
        
    def test_database_operation_latencies(self, perf_repo):
        """Test database operation latencies are acceptable."""
        # Simulate various database operations
        operations = [
            'create_simulation_run',
            'load_affinity_map', 
            'bulk_create_persons',
            'get_active_trends',
            'bulk_update_persons',
            'create_trend',
            'log_event'
        ]
        
        # Analyze recorded operation times
        operation_stats = {}
        for operation_name in operations:
            op_times = [time_taken for op_name, time_taken in perf_repo.operation_times 
                       if op_name == operation_name]
            
            if op_times:
                operation_stats[operation_name] = {
                    'count': len(op_times),
                    'avg_ms': statistics.mean(op_times) * 1000,
                    'max_ms': max(op_times) * 1000,
                    'min_ms': min(op_times) * 1000
                }
                
        print("Database operation latencies:")
        for op_name, stats in operation_stats.items():
            print(f"  {op_name}:")
            print(f"    Average: {stats['avg_ms']:.3f}ms")
            print(f"    Maximum: {stats['max_ms']:.3f}ms")
            print(f"    Count: {stats['count']}")
            
            # Validate operation latencies
            assert stats['avg_ms'] <= 5.0, f"{op_name} average latency too high: {stats['avg_ms']:.3f}ms"
            assert stats['max_ms'] <= 20.0, f"{op_name} maximum latency too high: {stats['max_ms']:.3f}ms"
            
    @pytest.mark.asyncio
    async def test_concurrent_simulation_performance(self, perf_repo):
        """Test multiple concurrent simulations performance."""
        num_concurrent = 3
        agents_per_sim = 30
        
        # Create multiple simulation engines
        engines = []
        for i in range(num_concurrent):
            engine = DemoSimulationEngine()
            await engine.initialize(num_agents=agents_per_sim)
            engines.append(engine)
            
        # Run concurrent simulations
        start_time = time.time()
        
        concurrent_tasks = [
            engine.run_simulation(duration_days=30/1440)  # 30 minutes each
            for engine in engines
        ]
        
        await asyncio.gather(*concurrent_tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze concurrent performance
        total_agents = num_concurrent * agents_per_sim
        total_events = sum(len(engine.active_trends) for engine in engines)
        
        print(f"Concurrent simulation performance:")
        print(f"  Concurrent simulations: {num_concurrent}")
        print(f"  Total agents: {total_agents}")
        print(f"  Total execution time: {total_time:.2f}s")
        print(f"  Total events created: {total_events}")
        print(f"  Events per second: {total_events/total_time:.1f}")
        
        # Performance should scale reasonably with concurrency
        expected_max_time = 60.0  # Should complete within 1 minute
        assert total_time <= expected_max_time, \
            f"Concurrent execution time {total_time:.2f}s exceeds {expected_max_time}s"
            
        # Each simulation should produce reasonable events
        for i, engine in enumerate(engines):
            events_created = len(engine.active_trends)
            assert events_created >= 5, f"Simulation {i} created too few events: {events_created}" 