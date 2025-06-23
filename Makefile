.PHONY: help dev-up dev-down test lint bootstrap clean docker-build

# Default target
help:
	@echo "CAPSIM 2.0 - Agent-based Discrete Event Simulation"
	@echo ""
	@echo "Available targets:"
	@echo "  dev-up       Start development environment"
	@echo "  dev-down     Stop development environment"
	@echo "  test         Run tests with pytest"
	@echo "  lint         Run code quality checks (ruff + mypy)"
	@echo "  bootstrap    Initialize system (migrations + data)"
	@echo "  clean        Clean up containers and volumes"
	@echo "  docker-build Build docker image"
	@echo ""

# Development environment
dev-up:
	@echo "🚀 Starting CAPSIM 2.0 development environment..."
	docker-compose up -d
	@echo "✅ Services started:"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"
	@echo "   Metrics: http://localhost:9090"
	@echo "   Grafana: http://localhost:3000"

dev-down:
	@echo "🛑 Stopping development environment..."
	docker-compose down

# Testing
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v --tb=short
	@echo "✅ Tests completed"

# Code quality
lint:
	@echo "🔍 Running code quality checks..."
	@echo "Running ruff..."
	python -m ruff check . --select ALL
	@echo "Running mypy..."
	python -m mypy --strict capsim
	@echo "✅ Code quality checks passed"

# System initialization
bootstrap:
	@echo "⚡ Bootstrapping CAPSIM 2.0..."
	python scripts/bootstrap.py
	@echo "✅ Bootstrap completed"

# Docker operations  
docker-build:
	@echo "🏗️ Building CAPSIM 2.0 docker image..."
	docker build -t capsim:2.0 .
	@echo "✅ Docker image built"

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup completed"

# Database operations
db-migrate:
	@echo "🗃️ Running database migrations..."
	alembic upgrade head
	@echo "✅ Migrations completed"

db-reset:
	@echo "⚠️ Resetting database (THIS WILL DELETE ALL DATA)..."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker-compose up postgres -d; \
		sleep 5; \
		make db-migrate; \
		make bootstrap; \
	fi

# Monitoring
logs:
	@echo "📋 Showing application logs..."
	docker-compose logs -f app

logs-db:
	@echo "📋 Showing database logs..."
	docker-compose logs -f postgres

# Health checks
health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/healthz | jq '.' || echo "❌ API not responding"
	@curl -s http://localhost:9090/-/healthy && echo "✅ Prometheus healthy" || echo "❌ Prometheus not responding"

# Development utilities
shell:
	@echo "🐚 Opening application shell..."
	docker-compose exec app /bin/bash

db-shell:
	@echo "🐚 Opening database shell..."
	docker-compose exec postgres psql -U postgres -d capsim

# Performance testing
load-test:
	@echo "⚡ Running basic load test..."
	@for i in $$(seq 1 10); do \
		curl -s -o /dev/null -w "Response time: %{time_total}s\n" http://localhost:8000/healthz; \
	done

# Documentation
docs-serve:
	@echo "📚 Serving documentation..."
	@echo "Mermaid diagrams available in docs/diagrams/"
	@echo "Architecture overview: docs/architecture_overview.md"

# CI simulation (local)
ci-local:
	@echo "🔄 Running CI pipeline locally..."
	make lint
	make test
	make docker-build
	@echo "✅ Local CI pipeline completed" 