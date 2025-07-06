#!/usr/bin/env python3
"""
Скрипт для проверки работоспособности дашбордов Grafana
"""

import requests
import json
import time

def check_grafana_status():
    """Проверяет статус Grafana"""
    try:
        response = requests.get("http://localhost:3000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Grafana доступен")
            return True
        else:
            print(f"❌ Grafana недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к Grafana: {e}")
        return False

def check_prometheus_metrics():
    """Проверяет наличие метрик в Prometheus"""
    try:
        response = requests.get("http://localhost:9091/api/v1/label/__name__/values", timeout=5)
        if response.status_code == 200:
            data = response.json()
            capsim_metrics = [m for m in data['data'] if m.startswith('capsim_')]
            print(f"✅ Найдено {len(capsim_metrics)} capsim метрик в Prometheus")
            for metric in capsim_metrics:
                print(f"   - {metric}")
            return len(capsim_metrics) > 0
        else:
            print(f"❌ Prometheus недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к Prometheus: {e}")
        return False

def check_specific_metrics():
    """Проверяет конкретные метрики"""
    metrics_to_check = [
        "capsim_events_table_inserts_total",
        "capsim_http_requests_total", 
        "capsim_simulations_active",
        "capsim_events_insert_rate_per_minute"
    ]
    
    print("\n📊 Проверка конкретных метрик:")
    for metric in metrics_to_check:
        try:
            response = requests.get(f"http://localhost:9091/api/v1/query?query={metric}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['data']['result']:
                    value = data['data']['result'][0]['value'][1]
                    print(f"   ✅ {metric}: {value}")
                else:
                    print(f"   ⚠️  {metric}: нет данных")
            else:
                print(f"   ❌ {metric}: ошибка запроса")
        except Exception as e:
            print(f"   ❌ {metric}: {e}")

def main():
    print("🔍 ПРОВЕРКА РАБОТОСПОСОБНОСТИ DASHBOARDS")
    print("=" * 50)
    
    # Проверка Grafana
    if not check_grafana_status():
        return
    
    # Проверка Prometheus
    if not check_prometheus_metrics():
        return
    
    # Проверка конкретных метрик
    check_specific_metrics()
    
    print("\n🎯 РЕЗУЛЬТАТ:")
    print("✅ Дашборды должны работать корректно!")
    print("🌐 Откройте http://localhost:3000")
    print("📊 Доступные дашборды:")
    print("   - CAPSIM Performance Tuning")
    print("   - CAPSIM Events Real Time")
    print("   - PostgreSQL Stats")
    print("   - Logs Dashboard")

if __name__ == "__main__":
    main() 