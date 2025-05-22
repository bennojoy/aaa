#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Make sure you have created it with:"
    echo "python3.12 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

echo "🔧 Initializing test data..."
echo "----------------------------------------"

# Run system user creation script
echo "1. Creating system user..."
python scripts/add_system_user.py

# Run test users and room creation script
echo "2. Creating test users and room..."
python messaging/tests/create_users_and_room.py

echo "----------------------------------------"
echo "✅ Test data initialization complete!"
echo ""
echo "Test users created:"
echo "- User 1: +15509990001 (pwuser1new2024)"
echo "- User 2: +15509990002 (pwuser2new2024)"
echo ""
echo "A test room 'messaging_room_test' has been created with both users as participants." 