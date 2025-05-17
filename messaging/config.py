# Kafka config
BOOTSTRAP_SERVERS = "localhost:29092"
OUTPUT_TOPIC = "messages.outgoing"
RETRY_DELAY = 5

# System user config
SYSTEM_PHONE = "+18992455022"
SYSTEM_PASSWORD = "system123"
SYSTEM_JWT_SECRET = "your-secret-key-here"
SYSTEM_USER_UUID = "2d90c5f0-f3ca-4fb4-a726-ac90316635d6"

# Topics
TOPICS = {
    "TO_USER": "messages.ToUser",
    "TO_ASSISTANT": "messages.ToAssistant",
    "TO_TRANSLATION": "messages.ToTranslation",
    "OUTGOING": "messages.outgoing"
}

# Consumer groups
CONSUMER_GROUPS = {
    "USER": "user_group",
    "ASSISTANT": "assistant_group",
    "TRANSLATION": "translation_group"
} 