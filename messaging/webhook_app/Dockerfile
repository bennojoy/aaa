FROM python:3.11-slim

WORKDIR /app
COPY . .

# Install dependencies including aiokafka instead of kafka-python
RUN pip install --no-cache-dir fastapi uvicorn aiokafka python-dotenv

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

