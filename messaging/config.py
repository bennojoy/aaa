# Kafka config
BOOTSTRAP_SERVERS = "localhost:29092"
OUTPUT_TOPIC = "messages.outgoing"
RETRY_DELAY = 5

# System user config
SYSTEM_PHONE = "+18992455022"
SYSTEM_PASSWORD = "system123"

# Topics
TOPICS = {
    "TO_USER": "messages.ToUser",
    "TO_ASSISTANT": "messages.ToAssistant",
    "OUTGOING": "messages.outgoing"
}

# Consumer groups
CONSUMER_GROUPS = {
    "USER": "user-message-consumer",
    "ASSISTANT": "assistant-message-consumer"
} 