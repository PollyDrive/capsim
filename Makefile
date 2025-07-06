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
	@echo "🔧 Performance Tuning:"
	@echo "  setup-macos-monitoring  Set up macOS-specific monitoring"
	@echo "  performance-baseline    Establish performance baseline"
	@echo "  performance-tuning      Run automated tuning loop"
	@echo "  performance-status      Check current performance metrics"
	@echo "  performance-help        Show performance tuning help"
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

# Performance Tuning Targets
setup-macos-monitoring:
	@echo "🚀 Setting up macOS monitoring for performance tuning..."
	./scripts/setup_macos_exporter.sh

performance-baseline:
	@echo "📊 Establishing performance baseline..."
	python3 scripts/performance_tuning.py

performance-tuning:
	@echo "🔧 Starting automated performance tuning..."
	./scripts/run_tuning_loop.sh

performance-status:
	@./scripts/check_performance_status.sh

performance-help:
	@echo "🛠️  Performance Tuning Commands:"
	@echo "  make setup-macos-monitoring  - Set up macOS-specific monitoring"
	@echo "  make performance-baseline    - Establish performance baseline"
	@echo "  make performance-tuning      - Run automated tuning loop"
	@echo "  make performance-status      - Check current performance metrics"
	@echo "  make performance-help        - Show this help"
	@echo ""
	@echo "📊 View results:"
	@echo "  Prometheus: http://localhost:9091"
	@echo "  Grafana: http://localhost:3000"
	@echo "  cAdvisor: http://localhost:8080"
	@echo ""
	@echo "📋 Files to check:"
	@echo "  baseline.yaml         - Performance baseline"
	@echo "  config/levers.yaml    - Tuning parameters"
	@echo "  CHANGELOG_TUNING.md   - Tuning history"
	@echo "  tuning.log           - Detailed tuning logs"

# Grafana Alerting & Browser Push Notifications
start-browser-push:  ## Start browser push notification server
	@echo "🚀 Starting browser push notification server..."
	@python3 scripts/browser_push_server.py --port 8001 &
	@echo "✅ Browser push server started on http://localhost:8001"

stop-browser-push:  ## Stop browser push notification server
	@echo "🛑 Stopping browser push notification server..."
	@pkill -f "browser_push_server.py" || true
	@echo "✅ Browser push server stopped"

restart-browser-push:  ## Restart browser push notification server
	@$(MAKE) stop-browser-push
	@sleep 2
	@$(MAKE) start-browser-push

test-browser-push:  ## Test browser push notification endpoint
	@echo "📱 Testing browser push notification..."
	@curl -X POST http://localhost:8001/api/notifications/browser-push \
		-H "Content-Type: application/json" \
		-d '{"title": "🧪 Test Alert", "body": "This is a test notification", "data": {"severity": "info", "dashboard_url": "http://localhost:3000/d/performance-tuning"}}' \
		|| echo "❌ Browser push server not running"

open-alerts-dashboard:  ## Open browser alerts dashboard
	@echo "🖥️  Opening alerts dashboard..."
	@open http://localhost:8001 || echo "❌ Cannot open browser (run 'make start-browser-push' first)"

setup-grafana-alerting:  ## Configure Grafana alerting (requires email setup)
	@echo "📧 Setting up Grafana alerting..."
	@echo "📝 Please update your .env file with:"
	@echo "   - your-email@gmail.com (replace with your actual email)"
	@echo "   - your-app-password (generate in Gmail security settings)"
	@echo "🔄 Restart Grafana after updating .env: make restart-grafana"

restart-grafana:  ## Restart Grafana service
	@echo "🔄 Restarting Grafana..."
	@docker-compose restart grafana
	@echo "✅ Grafana restarted"

check-grafana-alerts:  ## Check Grafana alert rules status
	@echo "🔍 Checking Grafana alert rules..."
	@curl -s -u admin:$$GRAFANA_PASSWORD http://localhost:3000/api/v1/provisioning/alert-rules | jq -r '.[] | "\(.title): \(.condition)"' || echo "❌ Cannot connect to Grafana"

grafana-alerting-help:  ## Show Grafana alerting help
	@echo "📧 Grafana Alerting & Browser Push Help:"
	@echo "  make setup-grafana-alerting  - Configure email alerting"
	@echo "  make restart-grafana         - Restart Grafana service"
	@echo "  make check-grafana-alerts    - Check alert rules status"
	@echo "  make start-browser-push      - Start browser notification server"
	@echo "  make test-browser-push       - Test browser notifications"
	@echo "  make open-alerts-dashboard   - Open alerts dashboard"
	@echo ""
	@echo "📊 Dashboard URLs:"
	@echo "  Performance Tuning: http://localhost:3000/d/performance-tuning"
	@echo "  Browser Alerts: http://localhost:8001"
	@echo ""
	@echo "📧 Email Setup:"
	@echo "  1. Enable 2FA in Gmail"
	@echo "  2. Generate App Password in Gmail Security settings"
	@echo "  3. Update .env with your email and app password"
	@echo "  4. Run 'make restart-grafana'"

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