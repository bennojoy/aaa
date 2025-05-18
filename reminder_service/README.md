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
