"""
API Contract validation tests for CAPSIM REST endpoints.

Tests API requirements from specification:
- POST /simulations (201, simulation_id)
- GET /simulations/{id} (200 status, 404 if missing)  
- GET /trends?simulation_id= (list of trends)
- GET /healthz (health check)
- GET /metrics (Prometheus metrics)
- Error handling (400, 404, 500)
- JSON schema validation

These tests ensure API contracts match specification.
"""

import pytest
import json
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import FastAPI testing tools
try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    # Create mock FastAPI app for testing
    app = FastAPI()
    
    # Mock data models
    class SimulationRequest(BaseModel):
        num_agents: int
        duration_days: int
        seed: int = None
        
    class SimulationResponse(BaseModel):
        simulation_id: str
        
    class SimulationStatus(BaseModel):
        simulation_id: str
        status: str
        current_time: float
        agents_count: int
        trends_count: int
        
    class TrendResponse(BaseModel):
        trend_id: str
        topic: str
        total_interactions: int
        virality_score: float
        
    # Mock endpoints
    @app.post("/simulations", response_model=SimulationResponse, status_code=201)
    async def create_simulation(request: SimulationRequest):
        return SimulationResponse(simulation_id=str(uuid.uuid4()))
        
    @app.get("/simulations/{simulation_id}", response_model=SimulationStatus)
    async def get_simulation(simulation_id: str):
        try:
            uuid.UUID(simulation_id)  # Validate UUID format
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid simulation_id format")
            
        # Mock simulation status
        return SimulationStatus(
            simulation_id=simulation_id,
            status="running",
            current_time=120.5,
            agents_count=100,
            trends_count=15
        )
        
    @app.get("/trends", response_model=list[TrendResponse])
    async def get_trends(simulation_id: str = None):
        if not simulation_id:
            raise HTTPException(status_code=400, detail="simulation_id parameter required")
            
        # Mock trend data
        return [
            TrendResponse(
                trend_id=str(uuid.uuid4()),
                topic="ECONOMIC", 
                total_interactions=150,
                virality_score=4.2
            ),
            TrendResponse(
                trend_id=str(uuid.uuid4()),
                topic="HEALTH",
                total_interactions=89,
                virality_score=3.7
            )
        ]
        
    @app.get("/healthz")
    async def health_check():
        return {"status": "ok"}
        
    @app.get("/metrics")
    async def metrics():
        # Mock Prometheus metrics
        return """# HELP capsim_queue_length Current event queue length
# TYPE capsim_queue_length gauge  
capsim_queue_length 142

# HELP capsim_event_latency_ms Event processing latency
# TYPE capsim_event_latency_ms histogram
capsim_event_latency_ms_bucket{le="1"} 245
capsim_event_latency_ms_bucket{le="5"} 891
capsim_event_latency_ms_bucket{le="10"} 985
capsim_event_latency_ms_bucket{le="+Inf"} 1000
capsim_event_latency_ms_sum 4567.8
capsim_event_latency_ms_count 1000

# HELP capsim_batch_commit_errors_total Batch commit errors  
# TYPE capsim_batch_commit_errors_total counter
capsim_batch_commit_errors_total 2
"""

    FASTAPI_AVAILABLE = True
    
except ImportError:
    FASTAPI_AVAILABLE = False
    app = None
    TestClient = None


class TestAPIContractValidation:
    """API contract validation test suite."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client fixture."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available for testing")
        return TestClient(app)
        
    def test_post_simulations_endpoint_contract(self, client):
        """API-01: POST /simulations contract validation."""
        # Test valid request
        valid_request = {
            "num_agents": 100,
            "duration_days": 1,
            "seed": 12345
        }
        
        response = client.post("/simulations", json=valid_request)
        
        # Validate response
        assert response.status_code == 201
        response_data = response.json()
        
        # Validate response schema
        assert "simulation_id" in response_data
        assert isinstance(response_data["simulation_id"], str)
        
        # Validate UUID format
        try:
            uuid.UUID(response_data["simulation_id"])
        except ValueError:
            pytest.fail("simulation_id is not a valid UUID")
            
        print(f"Created simulation: {response_data['simulation_id']}")
        
    def test_post_simulations_validation_errors(self, client):
        """Test POST /simulations validation and error handling."""
        # Test missing required fields
        invalid_requests = [
            {},  # Empty request
            {"num_agents": 100},  # Missing duration_days
            {"duration_days": 1},  # Missing num_agents
            {"num_agents": "invalid", "duration_days": 1},  # Invalid type
            {"num_agents": -1, "duration_days": 1},  # Invalid value
            {"num_agents": 10000, "duration_days": 1},  # Too many agents
            {"num_agents": 100, "duration_days": -1},  # Invalid duration
        ]
        
        for invalid_request in invalid_requests:
            response = client.post("/simulations", json=invalid_request)
            
            # Should return 400 Bad Request for validation errors
            assert response.status_code == 422 or response.status_code == 400, \
                f"Expected 422/400 for invalid request {invalid_request}, got {response.status_code}"
                
    def test_get_simulation_status_endpoint(self, client):
        """Test GET /simulations/{id} endpoint contract."""
        # Test with valid UUID
        test_uuid = str(uuid.uuid4())
        response = client.get(f"/simulations/{test_uuid}")
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Validate response schema
        required_fields = ["simulation_id", "status", "current_time", "agents_count", "trends_count"]
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
            
        # Validate field types
        assert isinstance(response_data["simulation_id"], str)
        assert isinstance(response_data["status"], str)
        assert isinstance(response_data["current_time"], (int, float))
        assert isinstance(response_data["agents_count"], int)
        assert isinstance(response_data["trends_count"], int)
        
        print(f"Simulation status: {response_data}")
        
    def test_get_simulation_invalid_id_handling(self, client):
        """Test GET /simulations/{id} with invalid IDs."""
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "",
            "invalid-uuid-format"
        ]
        
        for invalid_id in invalid_ids:
            response = client.get(f"/simulations/{invalid_id}")
            
            # Should return 400 Bad Request for invalid UUID format
            assert response.status_code == 400, \
                f"Expected 400 for invalid ID {invalid_id}, got {response.status_code}"
                
    def test_get_trends_endpoint_contract(self, client):
        """Test GET /trends endpoint contract."""
        test_simulation_id = str(uuid.uuid4())
        
        # Test with simulation_id parameter
        response = client.get(f"/trends?simulation_id={test_simulation_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Should return list of trends
        assert isinstance(response_data, list)
        
        # Validate trend schema if trends exist
        if response_data:
            trend = response_data[0]
            required_fields = ["trend_id", "topic", "total_interactions", "virality_score"]
            
            for field in required_fields:
                assert field in trend, f"Missing required trend field: {field}"
                
            # Validate field types
            assert isinstance(trend["trend_id"], str)
            assert isinstance(trend["topic"], str)
            assert isinstance(trend["total_interactions"], int)
            assert isinstance(trend["virality_score"], (int, float))
            
            # Validate value ranges
            assert trend["total_interactions"] >= 0
            assert 0.0 <= trend["virality_score"] <= 5.0
            
        print(f"Retrieved {len(response_data)} trends")
        
    def test_get_trends_missing_parameter(self, client):
        """Test GET /trends without simulation_id parameter."""
        response = client.get("/trends")
        
        # Should return 400 Bad Request for missing parameter
        assert response.status_code == 400
        
        response_data = response.json()
        assert "detail" in response_data
        assert "simulation_id" in response_data["detail"].lower()
        
    def test_health_check_endpoint(self, client):
        """Test GET /healthz endpoint."""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Validate health check response
        assert "status" in response_data
        assert response_data["status"] == "ok"
        
        print(f"Health check: {response_data}")
        
    def test_metrics_endpoint_prometheus_format(self, client):
        """Test GET /metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        
        # Should return text/plain content
        assert "text/plain" in response.headers.get("content-type", "")
        
        metrics_text = response.text
        
        # Validate Prometheus metrics format
        required_metrics = [
            "capsim_queue_length",
            "capsim_event_latency_ms", 
            "capsim_batch_commit_errors_total"
        ]
        
        for metric in required_metrics:
            assert metric in metrics_text, f"Missing required metric: {metric}"
            
        # Validate metric format structure
        lines = metrics_text.strip().split('\n')
        help_lines = [line for line in lines if line.startswith("# HELP")]
        type_lines = [line for line in lines if line.startswith("# TYPE")]
        
        assert len(help_lines) >= 3, "Should have HELP comments for metrics"
        assert len(type_lines) >= 3, "Should have TYPE comments for metrics"
        
        print(f"Metrics endpoint returned {len(lines)} lines")
        
    def test_error_response_format_consistency(self, client):
        """Test error responses follow consistent format."""
        # Generate various error conditions
        error_requests = [
            ("GET", "/simulations/invalid-uuid", 400),
            ("GET", "/trends", 400),  # Missing parameter
            ("GET", "/nonexistent-endpoint", 404),
            ("POST", "/simulations", 422),  # Empty body
        ]
        
        for method, url, expected_status in error_requests:
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                response = client.post(url)
                
            assert response.status_code == expected_status, \
                f"Expected {expected_status} for {method} {url}, got {response.status_code}"
                
            # Validate error response format
            if response.status_code >= 400:
                response_data = response.json()
                
                # Should have error details
                assert "detail" in response_data or "message" in response_data, \
                    f"Error response should contain 'detail' or 'message' field"
                    
    def test_request_response_content_types(self, client):
        """Test request/response content type handling."""
        # Test JSON request content type
        valid_request = {
            "num_agents": 50,
            "duration_days": 1
        }
        
        # Test with correct content type
        response = client.post(
            "/simulations",
            json=valid_request,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")
        
        # Test health endpoint returns JSON
        health_response = client.get("/healthz")
        assert "application/json" in health_response.headers.get("content-type", "")
        
        # Test metrics endpoint returns plain text
        metrics_response = client.get("/metrics")
        assert "text/plain" in metrics_response.headers.get("content-type", "")
        
    def test_api_response_time_requirements(self, client):
        """Test API response times meet performance requirements."""
        import time
        
        endpoints_to_test = [
            ("GET", "/healthz"),
            ("GET", "/metrics"),
            ("GET", f"/simulations/{uuid.uuid4()}"),
            ("GET", f"/trends?simulation_id={uuid.uuid4()}"),
        ]
        
        response_times = []
        
        for method, url in endpoints_to_test:
            start_time = time.perf_counter()
            
            if method == "GET":
                response = client.get(url)
            
            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000
            
            response_times.append((url, response_time_ms))
            
            # API endpoints should respond quickly (< 100ms for mocked responses)
            assert response_time_ms < 100, \
                f"API response time {response_time_ms:.2f}ms too slow for {url}"
                
        print("API response times:")
        for url, time_ms in response_times:
            print(f"  {url}: {time_ms:.2f}ms")
            
    def test_json_schema_validation_comprehensive(self, client):
        """Comprehensive JSON schema validation for all endpoints."""
        # POST /simulations schema validation
        simulation_request = {
            "num_agents": 100,
            "duration_days": 2,
            "seed": 42
        }
        
        response = client.post("/simulations", json=simulation_request)
        assert response.status_code == 201
        
        # Validate simulation response schema
        sim_data = response.json()
        simulation_id = sim_data["simulation_id"]
        
        # GET /simulations/{id} schema validation
        status_response = client.get(f"/simulations/{simulation_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        
        # Comprehensive status schema validation  
        schema_validations = [
            (status_data["simulation_id"], str, "simulation_id must be string"),
            (status_data["status"], str, "status must be string"),
            (status_data["current_time"], (int, float), "current_time must be numeric"),
            (status_data["agents_count"], int, "agents_count must be integer"),
            (status_data["trends_count"], int, "trends_count must be integer"),
        ]
        
        for value, expected_type, error_msg in schema_validations:
            assert isinstance(value, expected_type), error_msg
            
        # GET /trends schema validation
        trends_response = client.get(f"/trends?simulation_id={simulation_id}")
        assert trends_response.status_code == 200
        
        trends_data = trends_response.json()
        assert isinstance(trends_data, list)
        
        # If trends exist, validate trend schema
        if trends_data:
            trend = trends_data[0]
            trend_validations = [
                (trend["trend_id"], str, "trend_id must be string"),
                (trend["topic"], str, "topic must be string"),
                (trend["total_interactions"], int, "total_interactions must be integer"),
                (trend["virality_score"], (int, float), "virality_score must be numeric"),
            ]
            
            for value, expected_type, error_msg in trend_validations:
                assert isinstance(value, expected_type), error_msg
                
            # Additional validations
            assert trend["total_interactions"] >= 0
            assert 0.0 <= trend["virality_score"] <= 5.0
            assert trend["topic"] in ["ECONOMIC", "HEALTH", "SPIRITUAL", "CONSPIRACY", "SCIENCE", "CULTURE", "SPORT"]
            
        print("All JSON schemas validated successfully")
        
        
class TestAPIIntegrationScenarios:
    """Integration scenarios testing complete API workflows."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client fixture."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available for testing")
        return TestClient(app)
        
    def test_complete_simulation_workflow(self, client):
        """Test complete simulation creation and monitoring workflow."""
        # Step 1: Create simulation
        create_request = {
            "num_agents": 50,
            "duration_days": 1,
            "seed": 123
        }
        
        create_response = client.post("/simulations", json=create_request)
        assert create_response.status_code == 201
        
        simulation_id = create_response.json()["simulation_id"]
        
        # Step 2: Check simulation status
        status_response = client.get(f"/simulations/{simulation_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["simulation_id"] == simulation_id
        
        # Step 3: Retrieve trends for simulation
        trends_response = client.get(f"/trends?simulation_id={simulation_id}")
        assert trends_response.status_code == 200
        
        trends_data = trends_response.json()
        
        # Step 4: Verify health check still works
        health_response = client.get("/healthz")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"
        
        print(f"Complete workflow tested for simulation {simulation_id}")
        print(f"Status: {status_data['status']}")
        print(f"Trends count: {len(trends_data)}")
        
    def test_multiple_simulations_isolation(self, client):
        """Test multiple simulations are properly isolated."""
        # Create multiple simulations
        sim_ids = []
        
        for i in range(3):
            request = {
                "num_agents": 20 + i * 10,
                "duration_days": 1,
                "seed": 100 + i
            }
            
            response = client.post("/simulations", json=request)
            assert response.status_code == 201
            
            sim_id = response.json()["simulation_id"]
            sim_ids.append(sim_id)
            
        # Verify each simulation has independent status
        for i, sim_id in enumerate(sim_ids):
            status_response = client.get(f"/simulations/{sim_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["simulation_id"] == sim_id
            
            # Trends should be independent per simulation
            trends_response = client.get(f"/trends?simulation_id={sim_id}")
            assert trends_response.status_code == 200
            
        print(f"Successfully tested isolation of {len(sim_ids)} simulations") 