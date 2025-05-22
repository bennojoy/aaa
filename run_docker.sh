#!/bin/bash

# Change to the messaging services directory
cd messaging/services

# Start Docker services
echo "Starting messaging services..."
docker compose up -d

# Check if services started successfully
if [ $? -eq 0 ]; then
    echo "✅ Messaging services started successfully!"
    echo "Services running:"
    echo "- Zookeeper (port 2181)"
    echo "- Kafka (ports 9092, 29092)"
    echo "- EMQX MQTT Broker (ports 1883, 8083, 18083)"
    echo "- Webhook Server (port 4000)"
    echo "- Kafka-to-MQTT Bridge"
    echo ""
    echo "You can access:"
    echo "- EMQX Dashboard: http://localhost:18083 (default: admin/public)"
else
    echo "❌ Failed to start messaging services"
    exit 1
fi 