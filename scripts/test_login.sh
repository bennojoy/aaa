#!/bin/bash

# Test user credentials
PHONE="+9876543210"
PASSWORD="SecurePass123!"

# Create test user
echo "Creating test user..."
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"phone_number\": \"$PHONE\", \"password\": \"$PASSWORD\"}"

echo -e "\n\nTesting login..."
# Test login
curl -X POST "http://localhost:8000/api/v1/auth/signin" \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"$PHONE\", \"password\": \"$PASSWORD\"}"

echo -e "\n\nTesting protected route..."
# Get the token from the previous response and use it
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/signin" \
  -H "Content-Type: application/json" \
  -d "{\"identifier\": \"$PHONE\", \"password\": \"$PASSWORD\"}" | jq -r '.access_token')

curl -X GET "http://localhost:8000/api/v1/auth/protected" \
  -H "Authorization: Bearer $TOKEN" 