#!/bin/bash

# ============================================
# BINAAPP CHAT API TESTING SCRIPT
# ============================================
# Quick test script to verify chat endpoints are working

API_URL="${API_URL:-https://binaapp-backend.onrender.com}"
WEBSITE_ID="${WEBSITE_ID:-}"

echo "🧪 BinaApp Chat API Test"
echo "========================"
echo "API URL: $API_URL"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "Test 1: Health Check"
echo "--------------------"
response=$(curl -s -w "\n%{http_code}" "$API_URL/health")
status_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Backend is healthy"
    echo "Response: $body"
else
    echo -e "${RED}❌ FAIL${NC} - Backend is not responding"
    echo "Status: $status_code"
fi
echo ""

# Test 2: Chat Widget Script
echo "Test 2: Chat Widget Script"
echo "--------------------------"
response=$(curl -s -w "\n%{http_code}" "$API_URL/static/widgets/chat-widget.js")
status_code=$(echo "$response" | tail -n 1)

if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Chat widget script is accessible"
    echo "File size: $(echo "$response" | head -n -1 | wc -c) bytes"
else
    echo -e "${RED}❌ FAIL${NC} - Chat widget script not found"
    echo "Status: $status_code"
fi
echo ""

# Test 3: Create Test Conversation (requires WEBSITE_ID)
if [ -n "$WEBSITE_ID" ]; then
    echo "Test 3: Create Conversation"
    echo "---------------------------"
    echo "Using website_id: $WEBSITE_ID"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/chat/conversations/create" \
        -H "Content-Type: application/json" \
        -d "{
            \"website_id\": \"$WEBSITE_ID\",
            \"customer_name\": \"Test Customer\",
            \"customer_phone\": \"0123456789\"
        }")

    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✅ PASS${NC} - Conversation created successfully"
        echo "Response: $body"

        # Extract conversation_id for next test
        CONVERSATION_ID=$(echo "$body" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)
        echo "Conversation ID: $CONVERSATION_ID"
    else
        echo -e "${RED}❌ FAIL${NC} - Failed to create conversation"
        echo "Status: $status_code"
        echo "Response: $body"
    fi
    echo ""

    # Test 4: Send Message (if conversation was created)
    if [ -n "$CONVERSATION_ID" ]; then
        echo "Test 4: Send Message"
        echo "--------------------"

        response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/chat/messages/send" \
            -H "Content-Type: application/json" \
            -d "{
                \"conversation_id\": \"$CONVERSATION_ID\",
                \"sender_type\": \"customer\",
                \"sender_id\": \"customer_0123456789\",
                \"sender_name\": \"Test Customer\",
                \"message_type\": \"text\",
                \"message_text\": \"This is a test message from the API test script\"
            }")

        status_code=$(echo "$response" | tail -n 1)
        body=$(echo "$response" | head -n -1)

        if [ "$status_code" = "200" ]; then
            echo -e "${GREEN}✅ PASS${NC} - Message sent successfully"
            echo "Response: $body"
        else
            echo -e "${RED}❌ FAIL${NC} - Failed to send message"
            echo "Status: $status_code"
            echo "Response: $body"
        fi
        echo ""

        # Test 5: Get Messages
        echo "Test 5: Get Messages"
        echo "--------------------"

        response=$(curl -s -w "\n%{http_code}" "$API_URL/api/v1/chat/conversations/$CONVERSATION_ID")
        status_code=$(echo "$response" | tail -n 1)
        body=$(echo "$response" | head -n -1)

        if [ "$status_code" = "200" ]; then
            echo -e "${GREEN}✅ PASS${NC} - Messages retrieved successfully"
            echo "Response preview:"
            echo "$body" | head -c 500
            echo "..."
        else
            echo -e "${RED}❌ FAIL${NC} - Failed to get messages"
            echo "Status: $status_code"
        fi
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  SKIP${NC} - Tests 3-5 require WEBSITE_ID environment variable"
    echo "Usage: WEBSITE_ID='your-website-uuid' ./test-chat-api.sh"
    echo ""
fi

echo "========================"
echo "✅ Test suite completed"
echo ""
echo "To run full tests with a real website:"
echo "  WEBSITE_ID='your-uuid-here' ./scripts/test-chat-api.sh"
echo ""
