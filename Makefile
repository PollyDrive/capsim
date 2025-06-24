.PHONY: help dev-up dev-down test lint bootstrap clean docker-build

# Default target
help:
	@echo "CAPSIM 2.0 - Agent-based Discrete Event Simulation"
	@echo ""
	@echo "🚀 Development:"
	@echo "  dev-up         Start development environment"
	@echo "  dev-down       Stop development environment"
	@echo "  test           Run tests with pytest"
	@echo "  lint           Run code quality checks (ruff + mypy)"
	@echo "  bootstrap      Initialize system (migrations + data)"
	@echo ""
	@echo "🔐 Security:"
	@echo "  setup-env      Create .env from .env.example template"
	@echo "  validate-secrets   Check for placeholder secrets in .env"
	@echo "  generate-passwords Generate secure random passwords"
	@echo "  generate-jwt-secret Generate JWT secret (256-bit)"
	@echo "  security-audit     Run complete security audit"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  check-health   Check service health status"
	@echo "  monitor-db     Database monitoring dashboard"
	@echo "  metrics        Show current metrics"
	@echo "  compose-logs   Show docker-compose logs"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean          Clean up containers and volumes"
	@echo "  clean-logs     Clean Docker logs and system"
	@echo "  docker-build   Build docker image"
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

# DevOps additions for monitoring and DB tracking
compose-logs:
	@echo "📋 Showing docker-compose logs..."
	docker-compose logs -f --tail=50

check-health:
	@echo "🏥 Checking service health..."
	@echo "API Health:"
	@curl -s http://localhost:8000/healthz | jq . || echo "❌ API not responding"
	@echo "\nPrometheus Targets:"
	@curl -s http://localhost:9091/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}' || echo "❌ Prometheus not responding"

monitor-db:
	@echo "📊 Database monitoring..."
	@echo "Active simulations:"
	@psql postgresql://postgres:capsim321@localhost:5432/capsim_db -c "SELECT run_id, status, start_time, num_agents FROM capsim.simulation_runs ORDER BY start_time DESC LIMIT 5;" || echo "❌ Cannot connect to database"
	@echo "\nTotal agents:"
	@psql postgresql://postgres:capsim321@localhost:5432/capsim_db -c "SELECT COUNT(*) as total_agents FROM capsim.persons;" || echo "❌ Cannot query agents"

clean-logs:
	@echo "🧹 Cleaning Docker logs and system..."
	docker system prune -f
	@echo "✅ Cleanup completed"

metrics:
	@echo "📈 Current CAPSIM metrics:"
	@curl -s http://localhost:8000/metrics | grep -E "capsim_" | head -10

grafana-reload:
	@echo "📊 Reloading Grafana..."
	docker-compose restart grafana
	@sleep 10
	@echo "✅ Grafana reloaded"

# Security commands
setup-env:
	@echo "🔐 Setting up environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from template"; \
		echo "⚠️  Please edit .env with your actual secrets"; \
		echo "   Run: nano .env"; \
	else \
		echo "✅ .env already exists"; \
	fi

validate-secrets:
	@echo "🔍 Validating secret configuration..."
	@if [ -f .env ]; then \
		grep -q "change_me" .env && echo "❌ Found placeholder secrets in .env - please update them" || echo "✅ No placeholder secrets found"; \
	else \
		echo "❌ .env file not found - run 'make setup-env' first"; \
	fi

generate-jwt-secret:
	@echo "🔐 Generating JWT secret (256-bit):"
	@openssl rand -hex 32

generate-passwords:
	@echo "🔐 Generating secure passwords:"
	@echo "POSTGRES_PASSWORD=$(shell openssl rand -base64 32)"
	@echo "CAPSIM_RW_PASSWORD=$(shell openssl rand -base64 32)" 
	@echo "CAPSIM_RO_PASSWORD=$(shell openssl rand -base64 32)"
	@echo "GRAFANA_PASSWORD=$(shell openssl rand -base64 16)"

security-audit:
	@echo "🛡️ Running security audit..."
	@echo "1. Checking .gitignore coverage..."
	@grep -q ".env" .gitignore && echo "✅ .env files are gitignored" || echo "❌ .env not in .gitignore"
	@echo "2. Checking for secrets in git history..."
	@git log --all --full-history --grep="password\|secret\|token" --oneline | head -5
	@echo "3. Checking environment setup..."
	@make validate-secrets
	@echo "✅ Security audit completed" 