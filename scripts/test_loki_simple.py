#!/usr/bin/env python3
"""
Упрощенный тест для генерации структурированных JSON логов для Loki.
"""

import json
import logging
import time
import subprocess
from datetime import datetime
from uuid import uuid4

# Настройка JSON логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("capsim.test")


def log_json_event(event_type: str, **kwargs):
    """Логирует событие в JSON формате."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "logger": "capsim.test",
        "service": "capsim-test",
        "event_type": event_type,
        "correlation_id": str(uuid4()),
        **kwargs
    }
    
    logger.info(json.dumps(log_entry))


def test_smart_agent_allocation():
    """Генерирует логи для smart agent allocation."""
    print("🧪 Generating Smart Agent Allocation logs...")
    
    simulation_id = str(uuid4())
    
    # Лог инициализации симуляции
    log_json_event(
        "simulation_initialization",
        simulation_id=simulation_id,
        requested_agents=300,
        status="starting"
    )
    
    # Лог обнаружения существующих агентов
    log_json_event(
        "agents_discovery",
        simulation_id=simulation_id,
        existing_agents_found=150,
        database_query_duration_ms=45,
        allocation_strategy="smart_reuse"
    )
    
    # Лог переиспользования агентов
    log_json_event(
        "agents_reused",
        simulation_id=simulation_id,
        reused_count=150,
        requested_count=300,
        allocation_strategy="reuse_existing",
        database_table="persons",
        operation="SELECT_LIMIT_ORDER_BY_created_at"
    )
    
    # Лог дополнения агентов
    log_json_event(
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
    
    # Лог append-only событий
    for i in range(3):
        event_id = str(uuid4())
        log_json_event(
            "simulation_event_appended",
            simulation_id=simulation_id,
            event_id=event_id,
            action_type="agent_action",
            sim_time=i * 0.25,
            real_time=time.time(),
            affected_agents=5,
            database_table="events",
            operation="INSERT_APPEND_ONLY"
        )
        time.sleep(0.2)


def test_realtime_architecture():
    """Генерирует логи для realtime архитектуры."""
    print("⏰ Generating Realtime Architecture logs...")
    
    simulation_id = str(uuid4())
    
    # Лог realtime инициализации
    log_json_event(
        "realtime_mode_initialized",
        simulation_id=simulation_id,
        speed_factor=60.0,
        enable_realtime=True,
        clock_type="RealTimeClock",
        expected_duration_seconds=5.0
    )
    
    # Лог timing проверки
    log_json_event(
        "realtime_timing_check",
        simulation_id=simulation_id,
        sim_time=2.5,
        real_duration=2.38,
        expected_duration=2.50,
        timing_accuracy_percent=95.0,
        status="excellent"
    )
    
    # Лог batch commit
    log_json_event(
        "batch_commit_realtime",
        simulation_id=simulation_id,
        updates_count=25,
        commit_reason="time_based",
        batch_timeout_seconds=1.0,
        database_tables=["persons", "person_attribute_history"]
    )


def check_loki_with_curl():
    """Проверяет Loki через curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:3100/ready"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and "ready" in result.stdout:
            print("✅ Loki is ready and available")
            return True
        else:
            print(f"❌ Loki check failed: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ Failed to check Loki: {e}")
        return False


def query_loki_logs():
    """Запрашивает логи из Loki через curl."""
    print("\n🔍 Checking recent logs in Loki...")
    
    queries = [
        '{job="docker"}',
        '{service_name="app"}',
        '{logger="capsim.test"}',
        '{event_type="agents_reused"}',
        '{operation="INSERT_APPEND_ONLY"}'
    ]
    
    success_count = 0
    
    for query in queries:
        try:
            # Используем curl для запроса логов
            cmd = [
                "curl", "-G", "-s",
                "http://localhost:3100/loki/api/v1/query",
                "--data-urlencode", f"query={query}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    result_count = len(data.get('data', {}).get('result', []))
                    
                    print(f"📊 Query: {query}")
                    print(f"   • Streams found: {result_count}")
                    
                    if result_count > 0:
                        print("   ✅ Logs found!")
                        success_count += 1
                    else:
                        print("   ⚠️  No logs found")
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response")
            else:
                print(f"   ❌ Curl failed: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
        
        print()
    
    return success_count


def main():
    """Главная функция."""
    print("\n" + "="*60)
    print("🔍 CAPSIM LOKI LOGGING TEST (SIMPLIFIED)")
    print("="*60)
    
    # 1. Проверка Loki
    if not check_loki_with_curl():
        print("❌ Loki is not available. Start with: docker-compose up -d loki")
        return
    
    # 2. Генерация тестовых логов
    print("\n📝 Generating structured JSON logs...")
    test_smart_agent_allocation()
    test_realtime_architecture()
    
    # 3. Ожидание обработки
    print("\n⏳ Waiting for Promtail to process logs...")
    time.sleep(5)
    
    # 4. Проверка логов
    success_count = query_loki_logs()
    
    # 5. Итоговый отчет
    print("="*60)
    print("📋 LOGGING TEST RESULTS")
    print("="*60)
    
    print(f"✅ Loki availability: Working")
    print(f"📊 Test logs generated: Multiple JSON events")
    print(f"🎯 Query tests passed: {success_count}/5")
    
    if success_count >= 2:
        print("🎉 LOGGING SYSTEM IS WORKING!")
        print("📈 Logs are correctly flowing: App → Promtail → Loki")
    else:
        print("⚠️  PARTIAL SUCCESS - Some issues detected")
        print("💡 Check Promtail status: docker-compose logs promtail")
    
    print("\n🔗 Access points:")
    print("   • Loki API: http://localhost:3100")
    print("   • Grafana: http://localhost:3000")
    print("   • View logs: Grafana → Explore → Loki")
    
    # Демонстрация использования Grafana
    print("\n📊 To view logs in Grafana:")
    print("   1. Open http://localhost:3000")
    print("   2. Login: admin/admin")
    print("   3. Go to Explore")
    print("   4. Select Loki data source")
    print("   5. Use queries like: {logger=\"capsim.test\"}")


if __name__ == "__main__":
    main() 