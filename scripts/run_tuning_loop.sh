#!/bin/bash

# Performance Tuning Loop Script
# Implements the complete DevOps AI Playbook workflow

set -e

# Configuration
PROMETHEUS_URL="http://localhost:9091"
GRAFANA_URL="http://localhost:3000"
MAX_CYCLES=10
CYCLE_COUNT=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛠️  DevOps AI Playbook — Iterative Performance Tuning${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Function to check if services are running
check_services() {
    echo -e "${BLUE}🔍 Checking required services...${NC}"
    
    # Check Prometheus
    if ! curl -s "$PROMETHEUS_URL/api/v1/query?query=up" > /dev/null; then
        echo -e "${RED}❌ Prometheus not accessible at $PROMETHEUS_URL${NC}"
        echo -e "${YELLOW}Please run 'make dev-up' to start the monitoring stack${NC}"
        exit 1
    fi
    
    # Check Grafana
    if ! curl -s "$GRAFANA_URL/api/health" > /dev/null; then
        echo -e "${RED}❌ Grafana not accessible at $GRAFANA_URL${NC}"
        echo -e "${YELLOW}Please run 'make dev-up' to start the monitoring stack${NC}"
        exit 1
    fi
    
    # Check if metrics are being collected
    if ! curl -s "$PROMETHEUS_URL/api/v1/query?query=pg_up" | grep -q "success"; then
        echo -e "${YELLOW}⚠️  PostgreSQL metrics not available${NC}"
        echo -e "${YELLOW}Make sure postgres-exporter is running${NC}"
    fi
    
    echo -e "${GREEN}✅ All services are accessible${NC}"
}

# Function to check SLA compliance
check_sla_compliance() {
    echo -e "${BLUE}📊 Checking SLA compliance...${NC}"
    
    # Query current metrics
    CPU_TEMP=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=max(macos_cpu_temperature_celsius)" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    IO_WAIT=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=avg(rate(node_cpu_seconds_total{mode=\"iowait\"}[2m]))*100" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    P95_LATENCY=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=histogram_quantile(0.95,rate(capsim_event_latency_ms_bucket[5m]))" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    echo -e "  CPU Temp: ${CPU_TEMP}°C (target: ≤85°C)"
    echo -e "  IO Wait: ${IO_WAIT}% (target: <25%)"
    echo -e "  P95 Latency: ${P95_LATENCY}ms (target: ≤200ms)"
    
    # Check if all metrics are within SLA
    SLA_VIOLATIONS=0
    
    if (( $(echo "$CPU_TEMP > 85" | bc -l) )); then
        echo -e "${RED}❌ CPU temperature violation: ${CPU_TEMP}°C${NC}"
        SLA_VIOLATIONS=$((SLA_VIOLATIONS + 1))
    fi
    
    if (( $(echo "$IO_WAIT > 25" | bc -l) )); then
        echo -e "${RED}❌ IO wait violation: ${IO_WAIT}%${NC}"
        SLA_VIOLATIONS=$((SLA_VIOLATIONS + 1))
    fi
    
    if (( $(echo "$P95_LATENCY > 200" | bc -l) )); then
        echo -e "${RED}❌ P95 latency violation: ${P95_LATENCY}ms${NC}"
        SLA_VIOLATIONS=$((SLA_VIOLATIONS + 1))
    fi
    
    if [ $SLA_VIOLATIONS -eq 0 ]; then
        echo -e "${GREEN}✅ All metrics within SLA targets${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  ${SLA_VIOLATIONS} SLA violations detected${NC}"
        return 1
    fi
}

# Function to run one tuning cycle
run_tuning_cycle() {
    local cycle_num=$1
    
    echo -e "${BLUE}🔄 Starting tuning cycle ${cycle_num}/${MAX_CYCLES}${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    
    # Run the Python tuning script
    if python3 scripts/performance_tuning.py; then
        echo -e "${GREEN}✅ Tuning cycle ${cycle_num} completed successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Tuning cycle ${cycle_num} failed${NC}"
        return 1
    fi
}

# Function to add Grafana annotation
add_grafana_annotation() {
    local message=$1
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # This would require Grafana API key setup
    # For now, just log the annotation
    echo -e "${BLUE}📝 Grafana annotation: $message${NC}"
    echo "$(date): $message" >> tuning_annotations.log
}

# Function to backup current configuration
backup_configuration() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    echo -e "${BLUE}💾 Backing up current configuration...${NC}"
    
    # Backup key configuration files
    cp monitoring/postgresql.conf "$backup_dir/" 2>/dev/null || true
    cp .env "$backup_dir/" 2>/dev/null || true
    cp docker-compose.yml "$backup_dir/" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Configuration backed up to $backup_dir${NC}"
}

# Function to wait for user confirmation
wait_for_confirmation() {
    local message=$1
    echo -e "${YELLOW}$message${NC}"
    echo -e "${YELLOW}Press Enter to continue or Ctrl+C to cancel...${NC}"
    read -r
}

# Main execution starts here
main() {
    echo -e "${BLUE}Starting performance tuning loop...${NC}"
    echo -e "${BLUE}$(date)${NC}"
    echo ""
    
    # Check prerequisites
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ jq is required but not installed${NC}"
        echo -e "${YELLOW}Install with: brew install jq${NC}"
        exit 1
    fi
    
    if ! command -v bc &> /dev/null; then
        echo -e "${RED}❌ bc is required but not installed${NC}"
        echo -e "${YELLOW}Install with: brew install bc${NC}"
        exit 1
    fi
    
    # Check services
    check_services
    
    # Backup current configuration
    backup_configuration
    
    # Add initial annotation
    add_grafana_annotation "Performance tuning loop started"
    
    # Main tuning loop
    while [ $CYCLE_COUNT -lt $MAX_CYCLES ]; do
        CYCLE_COUNT=$((CYCLE_COUNT + 1))
        
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}CYCLE ${CYCLE_COUNT} of ${MAX_CYCLES}${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        
        # Check if we're already compliant
        if check_sla_compliance; then
            echo -e "${GREEN}🎉 All SLA targets met! Tuning complete.${NC}"
            break
        fi
        
        # Wait for user confirmation before making changes
        if [ $CYCLE_COUNT -eq 1 ]; then
            wait_for_confirmation "⚠️  About to start automated tuning. This will modify system configuration."
        fi
        
        # Run tuning cycle
        if run_tuning_cycle $CYCLE_COUNT; then
            echo -e "${GREEN}✅ Cycle ${CYCLE_COUNT} completed${NC}"
            
            # Wait for stabilization
            echo -e "${BLUE}⏳ Waiting for system stabilization (60 seconds)...${NC}"
            sleep 60
            
            # Check if we've improved
            if check_sla_compliance; then
                echo -e "${GREEN}🎉 SLA compliance achieved after ${CYCLE_COUNT} cycles!${NC}"
                break
            fi
        else
            echo -e "${RED}❌ Cycle ${CYCLE_COUNT} failed${NC}"
            echo -e "${YELLOW}⚠️  Consider manual intervention${NC}"
            break
        fi
    done
    
    # Final status
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}FINAL RESULTS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    
    check_sla_compliance
    
    # Add final annotation
    add_grafana_annotation "Performance tuning loop completed after $CYCLE_COUNT cycles"
    
    echo ""
    echo -e "${BLUE}📊 View results:${NC}"
    echo -e "  Prometheus: $PROMETHEUS_URL"
    echo -e "  Grafana: $GRAFANA_URL"
    echo -e "  Changelog: cat CHANGELOG_TUNING.md"
    echo -e "  Tuning log: cat tuning.log"
    echo ""
    echo -e "${GREEN}🏁 Performance tuning loop completed!${NC}"
}

# Handle script interruption
trap 'echo -e "\n${YELLOW}⚠️  Tuning loop interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@" 