# Chat Platform

A real-time chat platform with messaging, reminders, and AI assistant capabilities.

## Prerequisites

- Python 3.12
- Docker and Docker Compose
- Git

## Setup

1. Clone the repository:
```bash
git clone https://github.com/bennojoy/aaa.git
cd aaa
```

2. Create and activate virtual environment:
```bash
python3.12 -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Starting Services

### 1. Start Messaging Services (Kafka, MQTT, Webhook)

You can start the messaging services in two ways:

#### Option 1: Using the provided script (Recommended)
```bash
./run_docker.sh
```

#### Option 2: Manual start
```bash
cd messaging/services
docker compose up -d
```

This will start:
- Zookeeper (port 2181)
- Kafka (ports 9092, 29092)
- EMQX MQTT Broker (ports 1883, 8083, 18083)
- Webhook Server (port 4000)
- Kafka-to-MQTT Bridge

### 2. Start FastAPI Server

You can start the FastAPI server in two ways:

#### Option 1: Using the provided script (Recommended)
```bash
./run_app.sh
```

#### Option 2: Manual start
```bash
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### 3. Start Kafka Consumers

In a new terminal, start the Kafka consumers:

```bash
cd <repository-root>
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows

python run_consumers.py
```

This starts:
- Translation Consumer
- User Consumer
- Assistant Consumer

### 4. Start Reminder Service

In a new terminal, start the reminder service:

```bash
cd <repository-root>
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows

python run_reminder_service.py
```

## Service Overview

1. **FastAPI Server** (port 8000)
   - Main application server
   - Handles HTTP requests
   - Manages database operations
   - Provides API endpoints

2. **Messaging Services**
   - Kafka (ports 9092, 29092): Message broker
   - MQTT (port 1883): Real-time messaging
   - Webhook Server (port 4000): External integrations
   - Kafka-to-MQTT Bridge: Connects Kafka and MQTT

3. **Kafka Consumers**
   - Translation Consumer: Handles message translations
   - User Consumer: Processes user messages
   - Assistant Consumer: Manages AI assistant interactions

4. **Reminder Service**
   - Scans for due reminders
   - Sends reminder notifications
   - Manages recurring reminders

## Monitoring

- EMQX Dashboard: http://localhost:18083 (default: admin/public)
- API Documentation: http://localhost:8000/docs
- Application Logs: `logs/app.log`

## Stopping Services

1. Stop the reminder service and consumers with Ctrl+C
2. Stop the FastAPI server with Ctrl+C
3. Stop Docker containers:
```bash
cd messaging/services
docker compose down
``` 