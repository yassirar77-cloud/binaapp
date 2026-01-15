#!/bin/bash

echo "🔍 BinaApp Delivery System Diagnostic"
echo "======================================"
echo ""

echo "1. Checking frontend profile page..."
if grep -q "Pesanan" frontend/src/app/profile/page.tsx; then
    echo "   ✅ Orders tab exists in profile page"
else
    echo "   ❌ Orders tab NOT found"
fi

echo ""
echo "2. Checking rider app..."
if [ -f "frontend/src/app/rider/page.tsx" ]; then
    echo "   ✅ Rider app page exists"
else
    echo "   ❌ Rider app NOT found"
fi

echo ""
echo "3. Checking backend API..."
HEALTH=$(curl -s https://api.binaapp.my/v1/delivery/health 2>/dev/null | grep -o '"status":"healthy"' || echo "")
if [ -n "$HEALTH" ]; then
    echo "   ✅ Delivery API is healthy"
else
    echo "   ❌ API not reachable"
fi

echo ""
echo "4. Checking delivery endpoints..."
if grep -q "admin/orders" backend/app/api/v1/endpoints/delivery.py; then
    echo "   ✅ Owner orders endpoint exists"
else
    echo "   ❌ Owner endpoint NOT found"
fi

if grep -q "riders.*orders" backend/app/api/v1/endpoints/delivery.py; then
    echo "   ✅ Rider orders endpoint exists"
else
    echo "   ❌ Rider endpoint NOT found"
fi

echo ""
echo "5. Checking chat interface..."
if [ -f "frontend/src/app/dashboard/chat/page.tsx" ]; then
    echo "   ✅ Owner chat page exists"
else
    echo "   ❌ Chat page NOT found"
fi

if [ -f "frontend/src/app/chat/[conversationId]/page.tsx" ]; then
    echo "   ✅ Customer chat page exists"
else
    echo "   ❌ Customer chat NOT found"
fi

echo ""
echo "6. Checking database tables..."
echo "   (Need Supabase credentials to check)"

echo ""
echo "======================================"
echo "📊 SUMMARY:"
echo ""
echo "Run this command to check:"
echo "  bash diagnostic.sh"
echo ""
echo "If all checks pass ✅, the features exist!"
echo "Access them at:"
echo "  - Owner: https://binaapp.my/profile → Pesanan tab"
echo "  - Rider: https://binaapp.my/rider"
echo "  - Chat:  https://binaapp.my/dashboard/chat"
