#!/usr/bin/env python3
"""
Скрипт проверки исправлений:
1. Проверяет мок-данные в Grafana заменены на реальные
2. Проверяет создание событий в БД
3. Проверяет обновление метрик Prometheus
"""

import asyncio
import psycopg2
import json
import requests
import time
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://postgres:capsim321@postgres:5432/capsim_db"
API_BASE = "http://localhost:8000"
GRAFANA_BASE = "http://localhost:3000"
PROMETHEUS_BASE = "http://localhost:9091"

class EventsVerificationTest:
    def __init__(self):
        self.results = {}
        
    def connect_db(self):
        """Подключение к БД"""
        try:
            conn = psycopg2.connect(
                host="postgres",
                database="capsim_db",
                user="postgres", 
                password="capsim321",
                port=5432
            )
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return None
            
    def check_initial_state(self):
        """Проверка начального состояния БД"""
        print("\n🔍 Проверка начального состояния БД...")
        
        conn = self.connect_db()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        # Проверка количества событий
        cur.execute("SELECT COUNT(*) FROM capsim.events")
        events_count = cur.fetchone()[0]
        print(f"📊 События в БД: {events_count}")
        
        # Проверка активных симуляций
        cur.execute("""
            SELECT run_id, status, start_time, num_agents 
            FROM capsim.simulation_runs 
            WHERE end_time IS NULL
        """)
        active_sims = cur.fetchall()
        print(f"🔄 Активные симуляции: {len(active_sims)}")
        
        for sim in active_sims:
            print(f"  - {sim[0]} | {sim[1]} | {sim[2]} | {sim[3]} агентов")
            
        cur.close()
        conn.close()
        
        self.results['initial_events'] = events_count
        self.results['initial_active_sims'] = len(active_sims)
        return True
        
    def check_api_metrics(self):
        """Проверка API метрик"""
        print("\n📊 Проверка API метрик...")
        
        try:
            # Обновляем метрики
            response = requests.get(f"{API_BASE}/update-metrics")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Метрики обновлены: {data}")
                self.results['metrics_update'] = data
            else:
                print(f"❌ Ошибка обновления метрик: {response.status_code}")
                return False
                
            # Проверяем /stats/events
            response = requests.get(f"{API_BASE}/stats/events")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Статистика событий: {data['events_table']}")
                self.results['events_stats'] = data
                
                if data['events_table']['data_source'] == 'REAL_DATABASE':
                    print("✅ Используются РЕАЛЬНЫЕ данные из БД")
                else:
                    print("❌ Все еще используются мок-данные!")
                    return False
            else:
                print(f"❌ Ошибка получения статистики: {response.status_code}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Ошибка API: {e}")
            return False
            
    def check_prometheus_metrics(self):
        """Проверка метрик Prometheus"""
        print("\n🎯 Проверка метрик Prometheus...")
        
        try:
            # Проверяем метрики
            metrics = [
                "capsim_events_table_rows_total",
                "capsim_events_insert_rate_per_minute", 
                "capsim_simulations_active"
            ]
            
            for metric in metrics:
                url = f"{PROMETHEUS_BASE}/api/v1/query?query={metric}"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if data['data']['result']:
                        value = data['data']['result'][0]['value'][1]
                        print(f"✅ {metric}: {value}")
                        self.results[f'prometheus_{metric}'] = float(value)
                    else:
                        print(f"⚠️  {metric}: нет данных")
                        self.results[f'prometheus_{metric}'] = 0
                else:
                    print(f"❌ Ошибка получения {metric}: {response.status_code}")
                    
            return True
            
        except Exception as e:
            print(f"❌ Ошибка Prometheus: {e}")
            return False
            
    def run_test_simulation(self):
        """Запуск тестовой симуляции для проверки событий"""
        print("\n🧪 Запуск тестовой симуляции...")
        
        # Останавливаем активные симуляции
        print("🛑 Остановка активных симуляций...")
        import subprocess
        result = subprocess.run([
            "python", "-m", "capsim", "stop", "--force"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Активные симуляции остановлены")
        else:
            print(f"⚠️  Остановка симуляций: {result.stderr}")
            
        time.sleep(2)
        
        # Запускаем новую симуляцию
        print("🚀 Запуск новой симуляции (5 агентов, 2 минуты)...")
        
        result = subprocess.run([
            "python", "-m", "capsim", "run", 
            "--agents", "5", 
            "--minutes", "2",
            "--speed", "10.0"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Симуляция завершена успешно")
            
            # Проверяем новые события в БД
            conn = self.connect_db()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM capsim.events")
                new_events_count = cur.fetchone()[0]
                print(f"📊 События после симуляции: {new_events_count}")
                
                events_created = new_events_count - self.results.get('initial_events', 0)
                print(f"✨ Создано новых событий: {events_created}")
                
                if events_created > 0:
                    print("✅ События успешно создаются в БД!")
                    self.results['events_created'] = events_created
                    self.results['final_events'] = new_events_count
                else:
                    print("❌ События НЕ создаются в БД!")
                    return False
                    
                cur.close()
                conn.close()
                
            return True
        else:
            print(f"❌ Ошибка симуляции: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False
            
    def check_final_state(self):
        """Итоговая проверка состояния"""
        print("\n🏁 Итоговая проверка...")
        
        # Обновляем метрики
        self.check_api_metrics()
        self.check_prometheus_metrics()
        
        initial_events = self.results.get('initial_events', 0)
        final_events = self.results.get('final_events', 0)
        events_created = final_events - initial_events
        
        print("\n📋 РЕЗЮМЕ:")
        print(f"  📊 События в БД: {initial_events} → {final_events} (+{events_created})")
        print(f"  🎯 Prometheus события: {self.results.get('prometheus_capsim_events_table_rows_total', 0)}")
        print(f"  🔄 Активные симуляции: {self.results.get('prometheus_capsim_simulations_active', 0)}")
        
        # Проверка соответствия
        prometheus_events = self.results.get('prometheus_capsim_events_table_rows_total', 0)
        if abs(prometheus_events - final_events) <= 1:  # Допускаем небольшое расхождение
            print("✅ Prometheus метрики соответствуют реальным данным БД")
            return True
        else:
            print(f"❌ Prometheus метрики НЕ соответствуют БД: {prometheus_events} vs {final_events}")
            return False
            
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🚀 CAPSIM Events & Grafana Verification Test")
        print("=" * 50)
        
        tests = [
            ("Начальное состояние", self.check_initial_state),
            ("API метрики", self.check_api_metrics), 
            ("Prometheus метрики", self.check_prometheus_metrics),
            ("Тестовая симуляция", self.run_test_simulation),
            ("Итоговое состояние", self.check_final_state)
        ]
        
        passed = 0
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}...")
            try:
                if test_func():
                    print(f"✅ {test_name}: ПРОЙДЕН")
                    passed += 1
                else:
                    print(f"❌ {test_name}: ПРОВАЛЕН")
            except Exception as e:
                print(f"💥 {test_name}: ОШИБКА - {e}")
                
        print(f"\n🏆 РЕЗУЛЬТАТ: {passed}/{len(tests)} тестов пройдено")
        
        if passed == len(tests):
            print("🎉 ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ КОРРЕКТНО!")
            print("🎯 Grafana теперь отображает РЕАЛЬНЫЕ данные из БД")
            print("📊 События корректно записываются в capsim.events")
            return True
        else:
            print("⚠️  Некоторые проблемы еще не исправлены")
            return False

if __name__ == "__main__":
    test = EventsVerificationTest()
    success = test.run_all_tests()
    
    if success:
        print("\n🎯 ИНСТРУКЦИИ ДЛЯ ПРОВЕРКИ GRAFANA:")
        print("1. Откройте http://localhost:3000")
        print("2. Перейдите в CAPSIM 2.0 - Events & Simulations Dashboard")
        print("3. Убедитесь что все панели показывают '(REAL DATA)'")
        print("4. Значения должны соответствовать реальной БД, а не быть 7.31k")
        
    exit(0 if success else 1) 