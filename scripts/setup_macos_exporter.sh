#!/bin/bash

# Setup macOS exporter for performance tuning
# This script sets up monitoring for macOS-specific metrics

set -e

echo "🚀 Setting up macOS monitoring for performance tuning..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first."
    echo "Visit: https://brew.sh/"
    exit 1
fi

# Install node_exporter via Homebrew
echo "📦 Installing node_exporter..."
brew install node_exporter

# Create systemd-like service for macOS using launchd
echo "⚙️  Creating launchd service..."

# Create plist file for node_exporter
cat > ~/Library/LaunchAgents/homebrew.node_exporter.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>homebrew.node_exporter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/node_exporter</string>
        <string>--web.listen-address=0.0.0.0:9100</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/node_exporter.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/node_exporter.error.log</string>
</dict>
</plist>
EOF

# Load and start the service
echo "🔄 Starting node_exporter service..."
launchctl load ~/Library/LaunchAgents/homebrew.node_exporter.plist
launchctl start homebrew.node_exporter

# Wait a moment for the service to start
sleep 3

# Check if node_exporter is running
if curl -s http://localhost:9100/metrics > /dev/null; then
    echo "✅ node_exporter is running successfully on port 9100"
else
    echo "❌ node_exporter failed to start"
    exit 1
fi

# Create a simple script to collect macOS-specific metrics
echo "📊 Creating macOS metrics collector..."

cat > /tmp/macos_metrics.sh << 'EOF'
#!/bin/bash

# Collect macOS-specific performance metrics
# This supplements node_exporter with macOS-specific data

# CPU temperature (requires additional tools)
if command -v osx-cpu-temp &> /dev/null; then
    CPU_TEMP=$(osx-cpu-temp)
    echo "# HELP macos_cpu_temperature_celsius CPU temperature in Celsius"
    echo "# TYPE macos_cpu_temperature_celsius gauge"
    echo "macos_cpu_temperature_celsius $CPU_TEMP"
fi

# Thermal throttling information
if command -v pmset &> /dev/null; then
    THROTTLE_COUNT=$(pmset -g thermlog | grep -c "CPU_Speed_Limit" || echo "0")
    echo "# HELP macos_throttle_count_total Number of thermal throttle events"
    echo "# TYPE macos_throttle_count_total counter"
    echo "macos_throttle_count_total $THROTTLE_COUNT"
fi

# Memory pressure
if command -v memory_pressure &> /dev/null; then
    MEMORY_PRESSURE=$(memory_pressure | grep "System-wide memory free percentage" | awk '{print $NF}' | tr -d '%')
    echo "# HELP macos_memory_pressure_percentage Memory pressure percentage"
    echo "# TYPE macos_memory_pressure_percentage gauge"
    echo "macos_memory_pressure_percentage $MEMORY_PRESSURE"
fi

# Disk IO statistics
if command -v iostat &> /dev/null; then
    DISK_IO=$(iostat -d -c 1 | tail -n +3 | head -n 1 | awk '{print $3}')
    echo "# HELP macos_disk_io_per_second Disk I/O operations per second"
    echo "# TYPE macos_disk_io_per_second gauge"
    echo "macos_disk_io_per_second $DISK_IO"
fi
EOF

chmod +x /tmp/macos_metrics.sh

# Install additional tools for better macOS monitoring
echo "🔧 Installing additional monitoring tools..."

# Install osx-cpu-temp for CPU temperature monitoring
if ! command -v osx-cpu-temp &> /dev/null; then
    echo "📦 Installing osx-cpu-temp..."
    brew install osx-cpu-temp
fi

# Test the metrics collection
echo "🧪 Testing metrics collection..."
/tmp/macos_metrics.sh

echo "✅ macOS monitoring setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Ensure Docker is running"
echo "2. Run 'make dev-up' to start the monitoring stack"
echo "3. Check Prometheus targets at http://localhost:9091/targets"
echo "4. Access Grafana at http://localhost:3000"
echo "5. Run performance tuning: python scripts/performance_tuning.py"
echo ""
echo "🔍 Monitoring endpoints:"
echo "- Node exporter: http://localhost:9100/metrics"
echo "- Prometheus: http://localhost:9091"
echo "- Grafana: http://localhost:3000"
echo "- cAdvisor: http://localhost:8080" 