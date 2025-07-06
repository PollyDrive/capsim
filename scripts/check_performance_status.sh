#!/bin/bash

# Performance Status Check Script
# Check current performance metrics from Prometheus

PROMETHEUS_URL="http://localhost:9091"

echo "📊 Checking current performance metrics..."

# CPU Temperature
CPU_TEMP=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=macos_cpu_temperature_celsius" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo "CPU Temperature: ${CPU_TEMP}°C"

# IO Wait Percentage (check if data exists)
IO_WAIT_RAW=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=node_cpu_seconds_total{mode=\"iowait\"}" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null)
if [ "$IO_WAIT_RAW" != "null" ] && [ "$IO_WAIT_RAW" != "" ]; then
    IO_WAIT=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=avg(rate(node_cpu_seconds_total{mode=\"iowait\"}[2m]))*100" | \
        jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
else
    IO_WAIT="N/A"
fi
echo "IO Wait: ${IO_WAIT}%"

# HTTP Request Rate (as proxy for latency)
HTTP_RATE=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=rate(capsim_http_requests_total[5m])" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo "HTTP Request Rate: ${HTTP_RATE} req/sec"

# WAL Size (current)
WAL_SIZE=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=pg_wal_size_bytes" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo "WAL Size: ${WAL_SIZE} bytes"

# System Load
LOAD_AVG=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=macos_load_average_1m" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo "Load Average (1m): ${LOAD_AVG}"

# Memory Free Pages
FREE_PAGES=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=macos_memory_free_pages" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo "Free Memory Pages: ${FREE_PAGES}"

# Thermal State
THERMAL_STATE=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=macos_thermal_state" | \
    jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
if [ "$THERMAL_STATE" = "0" ]; then
    echo "Thermal State: ✅ Normal"
elif [ "$THERMAL_STATE" = "1" ]; then
    echo "Thermal State: ⚠️  Warning"
else
    echo "Thermal State: N/A"
fi

echo ""
echo "📋 SLA Targets:"
echo "• CPU Temperature: ≤ 85°C"
echo "• IO Wait: < 25%"
echo "• P95 Latency: ≤ 200ms"
echo "• WAL Rate: ≤ 1.5× baseline"

# SLA Compliance Check
echo ""
echo "🎯 SLA Compliance:"

if [ "$CPU_TEMP" != "N/A" ] && [ "$CPU_TEMP" != "null" ] && [ "$CPU_TEMP" != "" ]; then
    if (( $(echo "$CPU_TEMP <= 85" | bc -l) )); then
        echo "✅ CPU Temperature: ${CPU_TEMP}°C (within limit)"
    else
        echo "❌ CPU Temperature: ${CPU_TEMP}°C (exceeds 85°C limit)"
    fi
else
    echo "⚠️  CPU Temperature: No data available"
fi

if [ "$IO_WAIT" != "N/A" ] && [ "$IO_WAIT" != "null" ]; then
    if (( $(echo "$IO_WAIT < 25" | bc -l) )); then
        echo "✅ IO Wait: $IO_WAIT% (within limit)"
    else
        echo "❌ IO Wait: $IO_WAIT% (exceeds 25% limit)"
    fi
else
    echo "⚠️  IO Wait: No data available"
fi

if [ "$HTTP_RATE" != "N/A" ] && [ "$HTTP_RATE" != "null" ]; then
    echo "✅ HTTP Request Rate: ${HTTP_RATE} req/sec (monitoring active)"
else
    echo "⚠️  HTTP Request Rate: No data available"
fi

if [ "$WAL_SIZE" != "N/A" ] && [ "$WAL_SIZE" != "null" ]; then
    echo "✅ WAL Size: ${WAL_SIZE} bytes (monitoring active)"
else
    echo "⚠️  WAL Size: No data available"
fi 