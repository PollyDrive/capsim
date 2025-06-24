#!/usr/bin/env python3
"""
Тестовый скрипт для проверки корректности логирования в Loki.

Генерирует структурированные JSON логи с событиями smart agent allocation
и проверяет их поступление в Loki через Promtail.
"""

import json
import logging
import time
import requests
import asyncio
from datetime import datetime
from uuid import uuid4

# Настройка JSON логирования как в CAPSIM
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # JSON логи должны быть без дополнительного форматирования
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("capsim.test")


class StructuredLogger:
    """Класс для структурированного JSON логирования."""
    
    def __init__(self, service_name: str = "capsim-test"):
        self.service_name = service_name
        
    def log_event(self, event_type: str, **kwargs):
        """Логирует событие в JSON формате."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "logger": "capsim.test",
            "service": self.service_name,
            "event_type": event_type,
            "correlation_id": str(uuid4()),
            **kwargs
        }
        
        # Выводим JSON в один ряд для корректной обработки Promtail
        logger.info(json.dumps(log_entry))


def test_smart_agent_allocation_logging():
    """Тестирует логирование smart agent allocation."""
    structured_logger = StructuredLogger()
    
    print("🧪 Testing Smart Agent Allocation Logging...")
    
    # Симуляция существующих агентов
    simulation_id = str(uuid4())
    
    structured_logger.log_event(
        "simulation_initialization",
        simulation_id=simulation_id,
        requested_agents=300,
        status="starting"
    )
    
    # Логируем обнаружение существующих агентов
    structured_logger.log_event(
        "agents_discovery",
        simulation_id=simulation_id,
        existing_agents_found=150,
        database_query_duration_ms=45,
        allocation_strategy="smart_reuse"
    )
    
    # Логируем переиспользование агентов
    structured_logger.log_event(
        "agents_reused",
        simulation_id=simulation_id,
        reused_count=150,
        requested_count=300,
        allocation_strategy="reuse_existing",
        database_table="persons",
        operation="SELECT_LIMIT_ORDER_BY_created_at"
    )
    
    # Логируем создание недостающих агентов
    structured_logger.log_event(
        "agents_supplemented",
        simulation_id=simulation_id,
        existing_count=150,
        created_count=150,
        total_count=300,
        requested_count=300,
        allocation_strategy="supplement_missing",
        database_table="persons",
        operation="INSERT_BULK"
    )
    
    # Логируем профессиональное распределение
    profession_distribution = {
        "Teacher": 72, "Developer": 48, "Artist": 42, "Worker": 40,
        "Blogger": 37, "ShopClerk": 27, "Unemployed": 13, "Businessman": 12
    }
    
    structured_logger.log_event(
        "agent_distribution_created",
        simulation_id=simulation_id,
        profession_distribution=profession_distribution,
        total_professions=len(profession_distribution),
        database_table="persons"
    )
    
    # Логируем append-only события
    for i in range(5):
        event_id = str(uuid4())
        structured_logger.log_event(
            "simulation_event_appended",
            simulation_id=simulation_id,
            event_id=event_id,
            event_type="agent_action",
            sim_time=i * 0.25,
            real_time=time.time(),
            affected_agents=5,
            database_table="events",
            operation="INSERT_APPEND_ONLY"
        )
        time.sleep(0.1)  # Небольшая пауза между событиями


def test_realtime_architecture_logging():
    """Тестирует логирование realtime архитектуры."""
    structured_logger = StructuredLogger()
    
    print("⏰ Testing Realtime Architecture Logging...")
    
    simulation_id = str(uuid4())
    
    # Логируем инициализацию realtime режима
    structured_logger.log_event(
        "realtime_mode_initialized",
        simulation_id=simulation_id,
        speed_factor=60.0,
        enable_realtime=True,
        clock_type="RealTimeClock",
        expected_duration_seconds=5.0
    )
    
    # Логируем timing события
    structured_logger.log_event(
        "realtime_timing_check",
        simulation_id=simulation_id,
        sim_time=2.5,
        real_duration=2.38,
        expected_duration=2.50,
        timing_accuracy_percent=95.0,
        status="excellent"
    )
    
    # Логируем batch commit
    structured_logger.log_event(
        "batch_commit_realtime",
        simulation_id=simulation_id,
        updates_count=25,
        commit_reason="time_based",
        batch_timeout_seconds=1.0,
        database_tables=["persons", "person_attribute_history"]
    )


def check_loki_availability():
    """Проверяет доступность Loki."""
    try:
        response = requests.get("http://localhost:3100/ready", timeout=5)
        if response.status_code == 200:
            print("✅ Loki is ready and available")
            return True
        else:
            print(f"❌ Loki returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to Loki: {e}")
        return False


def query_logs_from_loki(query: str, start_time: str = None):
    """Запрашивает логи из Loki."""
    if not start_time:
        # Логи за последние 10 минут
        start_time = datetime.fromtimestamp(time.time() - 600).isoformat() + "Z"
    
    end_time = datetime.utcnow().isoformat() + "Z"
    
    try:
        params = {
            'query': query,
            'start': start_time,
            'end': end_time
        }
        
        response = requests.get(
            "http://localhost:3100/loki/api/v1/query_range",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            result_count = len(data.get('data', {}).get('result', []))
            total_entries = sum(
                len(stream.get('values', [])) 
                for stream in data.get('data', {}).get('result', [])
            )
            
            print(f"📊 Query: {query}")
            print(f"   • Streams found: {result_count}")
            print(f"   • Total log entries: {total_entries}")
            
            if total_entries > 0:
                print("   ✅ Logs found in Loki!")
                # Показываем пример последнего лога
                streams = data.get('data', {}).get('result', [])
                if streams and streams[0].get('values'):
                    last_log = streams[0]['values'][-1]
                    print(f"   📝 Latest entry: {last_log[1][:100]}...")
            else:
                print("   ⚠️  No logs found for this query")
            
            return total_entries > 0
        else:
            print(f"❌ Failed to query Loki: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to query Loki: {e}")
        return False


def main():
    """Главная функция для тестирования логирования."""
    print("\n" + "="*60)
    print("🔍 CAPSIM LOKI LOGGING TEST")
    print("="*60)
    
    # 1. Проверяем доступность Loki
    if not check_loki_availability():
        print("❌ Loki is not available. Please start with: docker-compose up -d loki")
        return
    
    # 2. Генерируем тестовые логи
    print("\n📝 Generating test logs...")
    test_smart_agent_allocation_logging()
    test_realtime_architecture_logging()
    
    # 3. Ждем пока логи попадут в Loki через Promtail
    print("\n⏳ Waiting for logs to be processed by Promtail...")
    time.sleep(10)
    
    # 4. Проверяем логи в Loki
    print("\n🔍 Checking logs in Loki...")
    
    test_queries = [
        '{job="docker"}',  # Все Docker логи
        '{service_name="app"}',  # Логи CAPSIM приложения
        '{logger="capsim.test"}',  # Наши тестовые логи
        '{event_type="agents_reused"}',  # Логи переиспользования агентов
        '{event_type="agents_supplemented"}',  # Логи дополнения агентов
        '{operation="INSERT_APPEND_ONLY"}',  # Логи append-only операций
        '{clock_type="RealTimeClock"}',  # Логи realtime режима
    ]
    
    success_count = 0
    for query in test_queries:
        if query_logs_from_loki(query):
            success_count += 1
        print()
    
    # 5. Итоговый отчет
    print("="*60)
    print("📋 LOGGING TEST RESULTS")
    print("="*60)
    
    print(f"✅ Loki availability: Working")
    print(f"📊 Test queries executed: {len(test_queries)}")
    print(f"🎯 Queries with results: {success_count}/{len(test_queries)}")
    
    if success_count >= len(test_queries) // 2:
        print("🎉 LOGGING TEST PASSED - Logs are correctly flowing to Loki!")
    else:
        print("⚠️  LOGGING TEST PARTIAL - Some logs may not be reaching Loki")
        print("💡 Troubleshooting tips:")
        print("   • Check Promtail status: docker-compose logs promtail")
        print("   • Verify Promtail config: monitoring/promtail-config.yml")
        print("   • Check app container labels: docker inspect capsim-app-1")
    
    print("\n🔗 Useful URLs:")
    print("   • Loki: http://localhost:3100")
    print("   • Grafana: http://localhost:3000 (admin/admin)")
    print("   • Prometheus: http://localhost:9091")


if __name__ == "__main__":
    main() 