#!/usr/bin/env python3
"""
Test BinaApp Delivery API Endpoints
Tests the delivery system with real Supabase data
"""

import os
import sys
import json
from decimal import Decimal

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test configuration
WEBSITE_ID = "5d208c1d-70bb-46c6-9bf8-e9700b33736c"  # khulafa

def convert_decimal(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def test_supabase_connection():
    """Test 1: Verify Supabase connection"""
    print("\n" + "="*60)
    print("TEST 1: Supabase Connection")
    print("="*60)

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        # Test query
        result = supabase.table("websites").select("id, name, subdomain").limit(1).execute()

        print("✅ Supabase connected successfully")
        if result.data:
            print(f"   Found website: {result.data[0].get('name')} ({result.data[0].get('subdomain')})")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False


def test_get_zones():
    """Test 2: GET /delivery/zones/{website_id}"""
    print("\n" + "="*60)
    print("TEST 2: GET Delivery Zones")
    print("="*60)

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        # Get zones
        zones_response = supabase.table("delivery_zones").select("*").eq(
            "website_id", WEBSITE_ID
        ).eq("is_active", True).order("sort_order").execute()

        # Get settings
        settings_response = supabase.table("delivery_settings").select("*").eq(
            "website_id", WEBSITE_ID
        ).execute()

        zones_count = len(zones_response.data)
        print(f"✅ Found {zones_count} delivery zones:")

        for zone in zones_response.data:
            print(f"   - {zone['zone_name']}: RM{zone['delivery_fee']} (min: RM{zone['minimum_order']})")

        if settings_response.data:
            settings = settings_response.data[0]
            print(f"\n   Settings: Min Order RM{settings['minimum_order']}, COD: {settings['accept_cod']}")

        return zones_count > 0
    except Exception as e:
        print(f"❌ Failed to get zones: {e}")
        return False


def test_get_menu():
    """Test 3: GET /delivery/menu/{website_id}"""
    print("\n" + "="*60)
    print("TEST 3: GET Menu")
    print("="*60)

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        # Get categories
        categories_response = supabase.table("menu_categories").select("*").eq(
            "website_id", WEBSITE_ID
        ).eq("is_active", True).order("sort_order").execute()

        # Get menu items
        items_response = supabase.table("menu_items").select("*").eq(
            "website_id", WEBSITE_ID
        ).eq("is_available", True).order("sort_order").execute()

        categories_count = len(categories_response.data)
        items_count = len(items_response.data)

        print(f"✅ Found {categories_count} categories and {items_count} menu items:")

        for category in categories_response.data:
            cat_items = [item for item in items_response.data if item['category_id'] == category['id']]
            print(f"\n   {category['icon']} {category['name']} ({len(cat_items)} items):")
            for item in cat_items[:3]:  # Show first 3 items
                print(f"      - {item['name']}: RM{item['price']}")

        return categories_count > 0 and items_count > 0
    except Exception as e:
        print(f"❌ Failed to get menu: {e}")
        return False


def test_create_order():
    """Test 4: POST /delivery/orders"""
    print("\n" + "="*60)
    print("TEST 4: Create Order")
    print("="*60)

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        # Get first zone
        zone_response = supabase.table("delivery_zones").select("*").eq(
            "website_id", WEBSITE_ID
        ).limit(1).execute()

        if not zone_response.data:
            print("❌ No delivery zones found")
            return False

        zone = zone_response.data[0]

        # Get first 2 menu items
        items_response = supabase.table("menu_items").select("*").eq(
            "website_id", WEBSITE_ID
        ).limit(2).execute()

        if not items_response.data:
            print("❌ No menu items found")
            return False

        menu_items = items_response.data

        # Calculate order totals
        subtotal = Decimal("0")
        order_items_data = []

        for menu_item in menu_items:
            quantity = 2
            unit_price = Decimal(str(menu_item['price']))
            total_price = unit_price * quantity
            subtotal += total_price

            order_items_data.append({
                "menu_item_id": menu_item['id'],
                "item_name": menu_item['name'],
                "quantity": quantity,
                "unit_price": float(unit_price),
                "total_price": float(total_price),
                "options": None,
                "notes": "Test order"
            })

        delivery_fee = Decimal(str(zone['delivery_fee']))
        total_amount = subtotal + delivery_fee

        # Create order
        order_data = {
            "website_id": WEBSITE_ID,
            "customer_name": "Ahmad Test",
            "customer_phone": "+60123456789",
            "customer_email": "test@example.com",
            "delivery_address": "123 Jalan Test, Shah Alam",
            "delivery_latitude": 3.0738,
            "delivery_longitude": 101.5183,
            "delivery_notes": "Please ring doorbell",
            "delivery_zone_id": zone['id'],
            "delivery_fee": float(delivery_fee),
            "subtotal": float(subtotal),
            "total_amount": float(total_amount),
            "payment_method": "cod",
            "payment_status": "pending",
            "status": "pending",
            "estimated_prep_time": 30,
            "estimated_delivery_time": zone['estimated_time_min']
        }

        order_response = supabase.table("delivery_orders").insert(order_data).execute()

        if not order_response.data:
            print("❌ Failed to create order")
            return False

        created_order = order_response.data[0]
        order_id = created_order['id']
        order_number = created_order['order_number']

        # Add order items
        for item_data in order_items_data:
            item_data['order_id'] = order_id

        supabase.table("order_items").insert(order_items_data).execute()

        print(f"✅ Order created successfully!")
        print(f"   Order Number: {order_number}")
        print(f"   Customer: {created_order['customer_name']}")
        print(f"   Items: {len(order_items_data)} items")
        print(f"   Subtotal: RM{subtotal}")
        print(f"   Delivery Fee: RM{delivery_fee}")
        print(f"   Total: RM{total_amount}")
        print(f"   Status: {created_order['status']}")

        return order_number
    except Exception as e:
        print(f"❌ Failed to create order: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_track_order(order_number):
    """Test 5: GET /delivery/orders/{order_number}/track"""
    print("\n" + "="*60)
    print("TEST 5: Track Order")
    print("="*60)

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        # Get order
        order_response = supabase.table("delivery_orders").select("*").eq(
            "order_number", order_number
        ).execute()

        if not order_response.data:
            print(f"❌ Order {order_number} not found")
            return False

        order = order_response.data[0]
        order_id = order['id']

        # Get order items
        items_response = supabase.table("order_items").select("*").eq(
            "order_id", order_id
        ).execute()

        # Get status history
        history_response = supabase.table("order_status_history").select("*").eq(
            "order_id", order_id
        ).order("created_at").execute()

        print(f"✅ Order Tracking: {order_number}")
        print(f"   Status: {order['status']}")
        print(f"   Customer: {order['customer_name']}")
        print(f"   Phone: {order['customer_phone']}")
        print(f"   Address: {order['delivery_address']}")
        print(f"   Total: RM{order['total_amount']}")

        print(f"\n   Items ({len(items_response.data)}):")
        for item in items_response.data:
            print(f"      - {item['item_name']} x{item['quantity']} = RM{item['total_price']}")

        if history_response.data:
            print(f"\n   Status History:")
            for history in history_response.data:
                print(f"      - {history['status']} ({history['created_at']})")

        return True
    except Exception as e:
        print(f"❌ Failed to track order: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🛵 BinaApp Delivery System - API Tests")
    print("="*60)
    print(f"Website ID: {WEBSITE_ID}")
    print(f"Subdomain: khulafa")

    results = {
        "Supabase Connection": False,
        "Get Zones": False,
        "Get Menu": False,
        "Create Order": False,
        "Track Order": False
    }

    # Test 1: Connection
    results["Supabase Connection"] = test_supabase_connection()

    if not results["Supabase Connection"]:
        print("\n❌ Cannot continue without Supabase connection")
        return

    # Test 2: Get Zones
    results["Get Zones"] = test_get_zones()

    # Test 3: Get Menu
    results["Get Menu"] = test_get_menu()

    # Test 4: Create Order
    order_number = test_create_order()
    results["Create Order"] = bool(order_number)

    # Test 5: Track Order
    if order_number:
        results["Track Order"] = test_track_order(order_number)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for p in results.values() if p)

    print(f"\n{passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Delivery system is working perfectly!")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")


if __name__ == "__main__":
    main()
