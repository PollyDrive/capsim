#!/usr/bin/env python3
"""
Performance Tuning Automation Script
Implements the DevOps AI Playbook for iterative performance tuning
"""

import os
import yaml
import json
import time
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tuning.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceTuner:
    def __init__(self, prometheus_url: str = "http://localhost:9091"):
        self.prometheus_url = prometheus_url
        self.baseline_file = "baseline.yaml"
        self.levers_file = "config/levers.yaml"
        self.changelog_file = "CHANGELOG_TUNING.md"
        self.current_baseline = None
        self.current_levers = None
        
    def load_configuration(self):
        """Load baseline and levers configuration"""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r') as f:
                    self.current_baseline = yaml.safe_load(f)
            
            if os.path.exists(self.levers_file):
                with open(self.levers_file, 'r') as f:
                    self.current_levers = yaml.safe_load(f)
                    
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def query_prometheus(self, query: str) -> Optional[float]:
        """Query Prometheus for metric values"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': query}
            )
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'success' and data['data']['result']:
                return float(data['data']['result'][0]['value'][1])
            return None
            
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None
    
    def establish_baseline(self) -> Dict:
        """Step 1: Establish baseline metrics"""
        logger.info("🔍 Establishing baseline metrics...")
        
        # Add Grafana annotation
        self.add_grafana_annotation(f"Baseline {datetime.now().isoformat()}")
        
        # Query metrics
        baseline_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        metrics_queries = {
            'wal_write_rate': 'rate(pg_wal_lsn_bytes_total[5m])',
            'disk_io_latency': 'avg(node_disk_io_time_seconds_total)',
            'io_wait_percentage': 'avg(rate(node_cpu_seconds_total{mode="iowait"}[2m])) * 100',
            'cpu_temperature': 'max(macos_cpu_temperature_celsius)',
            'throttle_count': 'macos_throttle_count_total',
            'p95_write_latency': 'histogram_quantile(0.95, rate(capsim_event_latency_ms_bucket[5m]))'
        }
        
        for metric, query in metrics_queries.items():
            value = self.query_prometheus(query)
            baseline_data['metrics'][metric] = {
                'value': value,
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"  {metric}: {value}")
        
        # Save baseline
        self.save_baseline(baseline_data)
        return baseline_data
    
    def save_baseline(self, baseline_data: Dict):
        """Save baseline data to YAML file"""
        # Update the baseline template with real values
        template = {
            'baseline': {
                'timestamp': baseline_data['timestamp'],
                'system_info': {
                    'cpu': 'M1 Air',
                    'postgres_version': '15',
                    'environment': 'Docker'
                },
                'metrics': {
                    'wal_write_rate': {
                        'query': 'rate(pg_wal_lsn_bytes_total[5m])',
                        'value_bytes_per_sec': baseline_data['metrics']['wal_write_rate']['value'] or 0,
                        'peak_bytes_per_sec': baseline_data['metrics']['wal_write_rate']['value'] or 0,
                        'unit': 'bytes/sec'
                    },
                    'disk_io_latency': {
                        'query': 'avg(node_disk_io_time_seconds_total)',
                        'value_seconds': baseline_data['metrics']['disk_io_latency']['value'] or 0,
                        'unit': 'seconds'
                    },
                    'io_wait_percentage': {
                        'query': 'avg(rate(node_cpu_seconds_total{mode="iowait"}[2m]))',
                        'value_percent': baseline_data['metrics']['io_wait_percentage']['value'] or 0,
                        'unit': 'percent'
                    },
                    'cpu_temperature': {
                        'query': 'max(macos_cpu_temperature_celsius)',
                        'value_celsius': baseline_data['metrics']['cpu_temperature']['value'] or 0,
                        'max_safe_celsius': 85,
                        'unit': 'celsius'
                    },
                    'throttle_count': {
                        'query': 'macos_throttle_count_total',
                        'value': baseline_data['metrics']['throttle_count']['value'] or 0,
                        'unit': 'count'
                    },
                    'p95_write_latency': {
                        'query': 'histogram_quantile(0.95, rate(capsim_event_latency_ms_bucket[5m]))',
                        'value_ms': baseline_data['metrics']['p95_write_latency']['value'] or 0,
                        'unit': 'ms'
                    }
                },
                'sla_targets': {
                    'cpu_temp_max': 85,
                    'io_wait_max': 25,
                    'p95_write_latency_max': 200,
                    'wal_rate_multiplier': 1.5
                }
            }
        }
        
        with open(self.baseline_file, 'w') as f:
            yaml.dump(template, f, default_flow_style=False)
        
        logger.info(f"✅ Baseline saved to {self.baseline_file}")
    
    def identify_worst_metric(self, baseline_data: Dict) -> str:
        """Identify which metric is violating SLA the most"""
        sla_violations = {}
        
        # Check each metric against SLA
        metrics = baseline_data['metrics']
        
        # CPU temperature
        cpu_temp = metrics.get('cpu_temperature', {}).get('value', 0)
        if cpu_temp > 85:
            sla_violations['high_cpu_temp'] = cpu_temp - 85
            
        # IO wait
        io_wait = metrics.get('io_wait_percentage', {}).get('value', 0)
        if io_wait > 25:
            sla_violations['high_io_wait'] = io_wait - 25
            
        # P95 write latency
        p95_latency = metrics.get('p95_write_latency', {}).get('value', 0)
        if p95_latency > 200:
            sla_violations['high_write_latency'] = p95_latency - 200
            
        # WAL rate (simplified check)
        wal_rate = metrics.get('wal_write_rate', {}).get('value', 0)
        if wal_rate > 1000000:  # 1MB/s baseline assumption
            sla_violations['high_wal_rate'] = wal_rate - 1000000
        
        if not sla_violations:
            return None
            
        # Return the worst violation
        return max(sla_violations, key=sla_violations.get)
    
    def choose_lever(self, target_symptom: str) -> Optional[Dict]:
        """Step 2: Choose the cheapest lever for the symptom"""
        if not self.current_levers:
            logger.error("No levers configuration loaded")
            return None
            
        # Get symptom mappings
        symptom_mappings = self.current_levers.get('symptom_mappings', {})
        lever_names = symptom_mappings.get(target_symptom, [])
        
        if not lever_names:
            logger.warning(f"No levers found for symptom: {target_symptom}")
            return None
        
        # Find the cheapest lever
        all_levers = []
        for cost_category in ['low_cost', 'medium_cost', 'high_cost']:
            levers = self.current_levers.get('levers', {}).get(cost_category, [])
            for lever in levers:
                if lever['name'] in lever_names:
                    lever['cost_category'] = cost_category
                    all_levers.append(lever)
        
        if not all_levers:
            logger.warning(f"No matching levers found for symptom: {target_symptom}")
            return None
            
        # Sort by cost (low -> high)
        cost_order = {'low_cost': 0, 'medium_cost': 1, 'high_cost': 2}
        all_levers.sort(key=lambda x: cost_order[x['cost_category']])
        
        return all_levers[0]  # Return the cheapest
    
    def apply_lever(self, lever: Dict) -> bool:
        """Apply a performance tuning lever"""
        logger.info(f"🔧 Applying lever: {lever['name']}")
        
        try:
            config_file = lever['config_file']
            parameter = lever['parameter']
            recommended_values = lever['recommended_values']
            
            # For simplicity, use the first recommended value
            new_value = recommended_values[0]
            
            if config_file == "monitoring/postgresql.conf":
                return self.update_postgres_config(parameter, new_value)
            elif config_file == ".env":
                return self.update_env_file(parameter, new_value)
            elif config_file == "docker-compose.yml":
                logger.info(f"⚠️  Manual intervention required for {config_file}")
                return False
            else:
                logger.warning(f"Unknown config file: {config_file}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying lever: {e}")
            return False
    
    def update_postgres_config(self, parameter: str, value: str) -> bool:
        """Update PostgreSQL configuration"""
        config_file = "monitoring/postgresql.conf"
        
        try:
            # Read current config
            with open(config_file, 'r') as f:
                lines = f.readlines()
            
            # Update or add parameter
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{parameter} ="):
                    lines[i] = f"{parameter} = {value}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"{parameter} = {value}\n")
            
            # Write back
            with open(config_file, 'w') as f:
                f.writelines(lines)
            
            logger.info(f"✅ Updated {parameter} = {value} in {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating PostgreSQL config: {e}")
            return False
    
    def update_env_file(self, parameter: str, value: str) -> bool:
        """Update .env file"""
        try:
            # Read current .env
            env_lines = []
            if os.path.exists(".env"):
                with open(".env", 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add parameter
            updated = False
            for i, line in enumerate(env_lines):
                if line.strip().startswith(f"{parameter}="):
                    env_lines[i] = f"{parameter}={value}\n"
                    updated = True
                    break
            
            if not updated:
                env_lines.append(f"{parameter}={value}\n")
            
            # Write back
            with open(".env", 'w') as f:
                f.writelines(env_lines)
            
            logger.info(f"✅ Updated {parameter} = {value} in .env")
            return True
            
        except Exception as e:
            logger.error(f"Error updating .env file: {e}")
            return False
    
    def wait_one_load_cycle(self, duration_minutes: int = 15):
        """Step 3: Wait one load cycle and log metrics"""
        logger.info(f"⏳ Waiting {duration_minutes} minutes for load cycle...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            # Log current metrics
            self.log_current_metrics()
            time.sleep(60)  # Log every minute
        
        logger.info("✅ Load cycle wait completed")
    
    def log_current_metrics(self):
        """Log current metrics to tuning.log"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'wal_rate': self.query_prometheus('rate(pg_wal_lsn_bytes_total[5m])'),
            'disk_latency': self.query_prometheus('avg(node_disk_io_time_seconds_total)'),
            'io_wait': self.query_prometheus('avg(rate(node_cpu_seconds_total{mode="iowait"}[2m])) * 100'),
            'cpu_temp': self.query_prometheus('max(macos_cpu_temperature_celsius)')
        }
        
        logger.info(f"📊 Metrics: {json.dumps(metrics, indent=2)}")
    
    def check_alerts(self) -> List[str]:
        """Step 4: Check for alert triggers"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/alerts")
            response.raise_for_status()
            data = response.json()
            
            tuning_alerts = []
            for alert in data.get('data', {}).get('alerts', []):
                labels = alert.get('labels', {})
                if labels.get('tuning_trigger') == 'true':
                    tuning_alerts.append(alert['labels']['alertname'])
            
            return tuning_alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    def add_grafana_annotation(self, text: str):
        """Add annotation to Grafana"""
        # This would require Grafana API configuration
        # For now, just log the annotation
        logger.info(f"📝 Grafana annotation: {text}")
    
    def update_changelog(self, lever_name: str, goal_metric: str, old_value: float, new_value: float, result: str):
        """Step 5: Update changelog"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        changelog_entry = f"""
## {timestamp}

* Lever: {lever_name}
* Goal metric: {goal_metric} from {old_value} → {new_value}
* Result: {result}

---
"""
        
        try:
            with open(self.changelog_file, 'a') as f:
                f.write(changelog_entry)
            
            logger.info(f"✅ Changelog updated: {result}")
            
        except Exception as e:
            logger.error(f"Error updating changelog: {e}")
    
    def run_tuning_cycle(self):
        """Run one complete tuning cycle"""
        logger.info("🚀 Starting performance tuning cycle...")
        
        # Load configuration
        self.load_configuration()
        
        # Step 1: Establish baseline
        baseline_data = self.establish_baseline()
        
        # Step 2: Identify worst metric and choose lever
        worst_metric = self.identify_worst_metric(baseline_data)
        if not worst_metric:
            logger.info("✅ All metrics within SLA - no tuning needed")
            return
        
        logger.info(f"🎯 Worst metric: {worst_metric}")
        
        lever = self.choose_lever(worst_metric)
        if not lever:
            logger.error("❌ No suitable lever found")
            return
        
        # Apply lever
        if not self.apply_lever(lever):
            logger.error("❌ Failed to apply lever")
            return
        
        # Git commit
        subprocess.run([
            'git', 'add', '-A'
        ], capture_output=True)
        
        subprocess.run([
            'git', 'commit', '-m', f"lever: {lever['name']} applied for {worst_metric}"
        ], capture_output=True)
        
        # Step 3: Wait one load cycle
        self.wait_one_load_cycle()
        
        # Step 4: Check alerts
        alerts = self.check_alerts()
        if alerts:
            logger.warning(f"⚠️  Alerts triggered: {alerts}")
            # TODO: Implement rollback logic
        
        # Step 5: Document results
        # Get new metric value
        new_baseline = self.establish_baseline()
        old_value = baseline_data['metrics'].get(worst_metric, {}).get('value', 0)
        new_value = new_baseline['metrics'].get(worst_metric, {}).get('value', 0)
        
        # Determine result
        if new_value < old_value:
            result = "✅ improved"
        elif new_value == old_value:
            result = "➖ no change"
        else:
            result = "⚠️ worse"
        
        self.update_changelog(lever['name'], worst_metric, old_value, new_value, result)
        
        logger.info("🏁 Tuning cycle completed")

def main():
    """Main entry point"""
    tuner = PerformanceTuner()
    tuner.run_tuning_cycle()

if __name__ == "__main__":
    main() 