# kafka_to_mqtt/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir PyJWT asyncio-mqtt paho-mqtt==1.6.1 aiokafka python-dotenv

CMD ["python", "kafka_to_mqtt_bridge.py"]

