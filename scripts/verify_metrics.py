#!/usr/bin/env python3
"""
Verify Metrics Availability
Checks that all CAPSIM and macOS metrics are available in Prometheus
"""

import requests
import json
import time
from typing import Dict, List

PROMETHEUS_URL = "http://localhost:9091"

def check_metric(metric_name: str) -> bool:
    """Check if a metric is available in Prometheus"""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", 
                              params={"query": metric_name}, 
                              timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                return True
        return False
    except Exception as e:
        print(f"Error checking {metric_name}: {e}")
        return False

def get_metric_value(metric_name: str) -> str:
    """Get the latest value of a metric"""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", 
                              params={"query": metric_name}, 
                              timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                return data["data"]["result"][0]["value"][1]
        return "N/A"
    except Exception as e:
        return f"Error: {e}"

def main():
    print("🔍 Checking Metrics Availability")
    print("=" * 50)
    
    # CAPSIM metrics to check
    capsim_metrics = [
        "capsim_http_requests_total",
        "capsim_events_table_inserts_total", 
        "capsim_events_table_rows_total",
        "capsim_simulations_active",
        "capsim_events_insert_rate_per_minute"
    ]
    
    # macOS metrics to check
    macos_metrics = [
        "macos_cpu_temperature_celsius",
        "macos_memory_free_pages",
        "macos_thermal_state",
        "macos_load_average_1m",
        "macos_disk_read_ops_per_sec",
        "macos_disk_write_ops_per_sec"
    ]
    
    print("\n📊 CAPSIM Metrics:")
    print("-" * 30)
    capsim_available = 0
    for metric in capsim_metrics:
        available = check_metric(metric)
        value = get_metric_value(metric) if available else "N/A"
        status = "✅" if available else "❌"
        print(f"{status} {metric}: {value}")
        if available:
            capsim_available += 1
    
    print(f"\nCAPSIM Metrics Available: {capsim_available}/{len(capsim_metrics)}")
    
    print("\n🍎 macOS Metrics:")
    print("-" * 30)
    macos_available = 0
    for metric in macos_metrics:
        available = check_metric(metric)
        value = get_metric_value(metric) if available else "N/A"
        status = "✅" if available else "❌"
        print(f"{status} {metric}: {value}")
        if available:
            macos_available += 1
    
    print(f"\nmacOS Metrics Available: {macos_available}/{len(macos_metrics)}")
    
    print("\n📈 Summary:")
    print("-" * 30)
    total_metrics = len(capsim_metrics) + len(macos_metrics)
    total_available = capsim_available + macos_available
    print(f"Total Metrics: {total_metrics}")
    print(f"Available: {total_available}")
    print(f"Success Rate: {(total_available/total_metrics)*100:.1f}%")
    
    if total_available == total_metrics:
        print("\n🎉 All metrics are available! Dashboards should work correctly.")
    else:
        print(f"\n⚠️  {total_metrics - total_available} metrics are missing.")
    
    print("\n🌐 Dashboard URLs:")
    print("-" * 30)
    print("Grafana: http://localhost:3000")
    print("Prometheus: http://localhost:9091")
    print("macOS Exporter: http://localhost:9101/metrics")

if __name__ == "__main__":
    main() 