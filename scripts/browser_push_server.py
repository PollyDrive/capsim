#!/usr/bin/env python3
"""
Сервер для обработки браузерных push уведомлений от Grafana
Запускается на порту 8001 и принимает webhook-и от Grafana Alerting
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Хранилище для уведомлений (в реальном приложении используйте Redis/DB)
notifications_store = []

# HTML шаблон для отображения уведомлений
NOTIFICATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CAPSIM Performance Alerts</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; }
        .alert { 
            background: white; 
            border-left: 4px solid #ff6b6b; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .alert.warning { border-left-color: #ffa500; }
        .alert.info { border-left-color: #3498db; }
        .alert.critical { border-left-color: #e74c3c; }
        .alert-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
        .alert-time { color: #666; font-size: 12px; }
        .alert-body { margin: 10px 0; }
        .alert-actions { margin-top: 10px; }
        .btn { 
            padding: 8px 16px; 
            margin-right: 10px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-secondary { background: #95a5a6; color: white; }
        .stats { background: white; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .refresh-btn { 
            position: fixed; 
            top: 20px; 
            right: 20px; 
            background: #27ae60; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }
        .clear-btn { 
            position: fixed; 
            top: 20px; 
            right: 150px; 
            background: #e74c3c; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }
        .no-alerts { 
            text-align: center; 
            color: #666; 
            font-style: italic; 
            padding: 40px; 
            background: white; 
            border-radius: 4px;
        }
        .enable-push { 
            background: #f39c12; 
            color: white; 
            padding: 15px; 
            border-radius: 4px; 
            margin-bottom: 20px;
            text-align: center;
        }
        .enable-push button { 
            background: #e67e22; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
    <button class="clear-btn" onclick="clearNotifications()">🗑️ Clear All</button>
    
    <div class="container">
        <h1>🚨 CAPSIM Performance Alerts</h1>
        
        <div class="enable-push">
            <strong>📱 Enable Browser Notifications</strong>
            <button onclick="enablePushNotifications()">Enable Push Notifications</button>
        </div>
        
        <div class="stats">
            <strong>📊 Statistics:</strong>
            Total alerts: {{ total_alerts }} | 
            Critical: {{ critical_count }} | 
            Warning: {{ warning_count }} | 
            Info: {{ info_count }}
        </div>
        
        {% if notifications %}
            {% for notification in notifications %}
            <div class="alert {{ notification.severity }}">
                <div class="alert-title">{{ notification.title }}</div>
                <div class="alert-time">{{ notification.timestamp }}</div>
                <div class="alert-body">{{ notification.body }}</div>
                <div class="alert-actions">
                    {% if notification.dashboard_url %}
                    <a href="{{ notification.dashboard_url }}" class="btn btn-primary" target="_blank">📊 View Dashboard</a>
                    {% endif %}
                    <button class="btn btn-secondary" onclick="dismissAlert('{{ notification.id }}')">✖️ Dismiss</button>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="no-alerts">
                ✅ No active alerts. System is running normally.
            </div>
        {% endif %}
    </div>

    <script>
        // Функция для включения push уведомлений
        async function enablePushNotifications() {
            if ('Notification' in window) {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    alert('✅ Push notifications enabled!');
                    // Регистрируем service worker для push уведомлений
                    if ('serviceWorker' in navigator) {
                        navigator.serviceWorker.register('/sw.js');
                    }
                } else {
                    alert('❌ Push notifications blocked by browser');
                }
            } else {
                alert('❌ Browser does not support notifications');
            }
        }

        // Функция для отображения push уведомления
        function showPushNotification(title, body, icon) {
            if (Notification.permission === 'granted') {
                new Notification(title, {
                    body: body,
                    icon: icon || '/static/alert-icon.png',
                    badge: '/static/badge.png',
                    tag: 'performance-alert',
                    requireInteraction: true
                });
            }
        }

        // Функция для очистки всех уведомлений
        async function clearNotifications() {
            if (confirm('Clear all notifications?')) {
                const response = await fetch('/api/notifications/clear', {
                    method: 'POST'
                });
                if (response.ok) {
                    location.reload();
                }
            }
        }

        // Функция для скрытия конкретного алерта
        async function dismissAlert(alertId) {
            const response = await fetch(`/api/notifications/${alertId}/dismiss`, {
                method: 'POST'
            });
            if (response.ok) {
                location.reload();
            }
        }

        // Автообновление каждые 30 секунд
        setInterval(() => {
            location.reload();
        }, 30000);

        // Проверяем новые уведомления через WebSocket или polling
        async function checkForNewAlerts() {
            try {
                const response = await fetch('/api/notifications/latest');
                const data = await response.json();
                
                if (data.new_alerts && data.new_alerts.length > 0) {
                    data.new_alerts.forEach(alert => {
                        showPushNotification(alert.title, alert.body, alert.icon);
                    });
                }
            } catch (error) {
                console.error('Error checking for new alerts:', error);
            }
        }

        // Проверяем новые алерты каждые 10 секунд
        setInterval(checkForNewAlerts, 10000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Главная страница с отображением уведомлений"""
    # Подсчитываем статистику
    total_alerts = len(notifications_store)
    critical_count = sum(1 for n in notifications_store if n.get('severity') == 'critical')
    warning_count = sum(1 for n in notifications_store if n.get('severity') == 'warning')
    info_count = sum(1 for n in notifications_store if n.get('severity') == 'info')
    
    # Сортируем по времени (новые первыми)
    sorted_notifications = sorted(notifications_store, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return render_template_string(
        NOTIFICATION_TEMPLATE,
        notifications=sorted_notifications,
        total_alerts=total_alerts,
        critical_count=critical_count,
        warning_count=warning_count,
        info_count=info_count
    )

@app.route('/api/notifications/browser-push', methods=['POST'])
def handle_browser_push():
    """Обработка webhook-а от Grafana для браузерных push уведомлений"""
    try:
        data = request.get_json()
        logger.info(f"Received alert webhook: {json.dumps(data, indent=2)}")
        
        # Парсим данные от Grafana
        if isinstance(data, dict) and 'alerts' in data:
            # Новый формат Grafana Alerting
            alerts = data['alerts']
            for alert in alerts:
                notification = {
                    'id': f"alert-{int(time.time())}-{alert.get('fingerprint', 'unknown')}",
                    'title': f"🚨 {alert.get('labels', {}).get('alertname', 'Unknown Alert')}",
                    'body': alert.get('annotations', {}).get('summary', 'No summary available'),
                    'severity': alert.get('labels', {}).get('severity', 'info'),
                    'component': alert.get('labels', {}).get('component', 'system'),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'dashboard_url': f"http://localhost:3000/d/performance-tuning",
                    'raw_data': alert
                }
                notifications_store.append(notification)
                logger.info(f"Added notification: {notification['title']}")
        
        elif isinstance(data, dict) and 'title' in data:
            # Прямой формат от webhook
            notification = {
                'id': f"direct-{int(time.time())}",
                'title': data.get('title', 'Performance Alert'),
                'body': data.get('body', 'No details available'),
                'severity': data.get('data', {}).get('severity', 'info'),
                'component': 'system',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'dashboard_url': data.get('data', {}).get('dashboard_url'),
                'raw_data': data
            }
            notifications_store.append(notification)
            logger.info(f"Added direct notification: {notification['title']}")
        
        # Ограничиваем количество уведомлений (последние 100)
        if len(notifications_store) > 100:
            notifications_store[:] = notifications_store[-100:]
        
        return jsonify({
            'status': 'success',
            'message': 'Notification received',
            'count': len(notifications_store)
        })
        
    except Exception as e:
        logger.error(f"Error processing browser push: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/notifications/latest')
def get_latest_notifications():
    """Получение последних уведомлений (для polling)"""
    # Возвращаем последние 10 уведомлений
    latest = notifications_store[-10:] if notifications_store else []
    return jsonify({
        'notifications': latest,
        'total': len(notifications_store),
        'new_alerts': []  # Здесь могла бы быть логика для новых алертов
    })

@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    """Очистка всех уведомлений"""
    notifications_store.clear()
    logger.info("Cleared all notifications")
    return jsonify({'status': 'success', 'message': 'All notifications cleared'})

@app.route('/api/notifications/<notification_id>/dismiss', methods=['POST'])
def dismiss_notification(notification_id):
    """Скрытие конкретного уведомления"""
    global notifications_store
    notifications_store = [n for n in notifications_store if n.get('id') != notification_id]
    logger.info(f"Dismissed notification: {notification_id}")
    return jsonify({'status': 'success', 'message': 'Notification dismissed'})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'notifications_count': len(notifications_store)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting browser push notification server on port {port}")
    logger.info(f"Access dashboard at: http://localhost:{port}")
    logger.info(f"Webhook endpoint: http://localhost:{port}/api/notifications/browser-push")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 