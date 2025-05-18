#!/bin/bash

# Create main directory
mkdir -p reminder_service

# Create Python package files
touch reminder_service/__init__.py
touch reminder_service/scanner.py
touch reminder_service/config.py
touch reminder_service/producer.py
touch reminder_service/models.py
touch reminder_service/requirements.txt
touch reminder_service/README.md

# Create a basic README
cat > reminder_service/README.md << 'EOL'
# Reminder Service

A standalone service that scans the database for due reminders and publishes them to Kafka.

## Features
- Scans database every minute for due reminders
- Publishes reminders to Kafka topic
- Handles recurring reminders
- Uses database-level locking for safe concurrent processing

## Configuration
- Database connection
- Kafka settings
- Scan interval
- Batch size

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Configure environment variables
3. Run: `python -m reminder_service.scanner`

## Monitoring
- JSON-formatted logs
- Trace IDs for request tracking
- Error reporting
EOL

# Create requirements.txt with basic dependencies
cat > reminder_service/requirements.txt << 'EOL'
sqlalchemy>=2.0.0
asyncpg>=0.27.0
aiokafka>=0.8.0
python-dotenv>=1.0.0
pydantic>=2.0.0
EOL
