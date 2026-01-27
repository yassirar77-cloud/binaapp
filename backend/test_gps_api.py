#!/usr/bin/env python3
"""
Test script for Phase 2 GPS Location Update API

This script simulates a rider sending GPS updates to the backend.
Useful for testing the real-time tracking feature.
"""

import requests
import time
import random
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/v1/delivery"  # Change to your API URL
RIDER_ID = "your-rider-id-here"  # Replace with actual rider ID
ORDER_ID = "your-order-id-here"   # Optional: associate with order

# Simulated route (e.g., Kuala Lumpur city center)
# Start point: KLCC
# End point: Bukit Bintang
START_LAT = 3.1578
START_LNG = 101.7123
END_LAT = 3.1478
END_LNG = 101.7056

def simulate_rider_movement(steps=20, delay=5):
    """
    Simulate a rider moving from start to end point.

    Args:
        steps: Number of GPS updates to send
        delay: Seconds between updates
    """
    print(f"🛵 Starting GPS tracking simulation")
    print(f"📍 Route: ({START_LAT}, {START_LNG}) → ({END_LAT}, {END_LNG})")
    print(f"⏱️  {steps} updates, {delay}s interval\n")

    for i in range(steps + 1):
        # Calculate current position (linear interpolation)
        progress = i / steps
        current_lat = START_LAT + (END_LAT - START_LAT) * progress
        current_lng = START_LNG + (END_LNG - START_LNG) * progress

        # Add small random variation (simulates GPS drift)
        current_lat += random.uniform(-0.0005, 0.0005)
        current_lng += random.uniform(-0.0005, 0.0005)

        # Send update to API
        try:
            response = requests.put(
                f"{API_BASE_URL}/riders/{RIDER_ID}/location",
                json={
                    "latitude": current_lat,
                    "longitude": current_lng
                },
                params={"order_id": ORDER_ID} if ORDER_ID != "your-order-id-here" else {}
            )

            if response.status_code == 200:
                data = response.json()
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"✅ [{timestamp}] Update {i+1}/{steps+1}: "
                      f"({current_lat:.6f}, {current_lng:.6f})")
                print(f"   Response: {data.get('message')}")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

        # Wait before next update (except last one)
        if i < steps:
            time.sleep(delay)

    print(f"\n🎉 Simulation complete! Sent {steps + 1} GPS updates.")


def get_current_location():
    """Get rider's current location from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/riders/{RIDER_ID}/location")
        if response.status_code == 200:
            data = response.json()
            print(f"\n📍 Current Location:")
            print(f"   Rider: {data.get('rider_name')}")
            print(f"   Lat: {data.get('latitude')}")
            print(f"   Lng: {data.get('longitude')}")
            print(f"   Last Update: {data.get('last_update')}")
            print(f"   Online: {data.get('is_online')}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")


def get_location_history(limit=10):
    """Get rider's location history"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/riders/{RIDER_ID}/location/history",
            params={"limit": limit}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"\n📜 Location History ({data.get('count')} records):")
            for h in data.get('history', [])[:5]:  # Show first 5
                print(f"   • ({h['latitude']:.6f}, {h['longitude']:.6f}) "
                      f"at {h['recorded_at']}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")


def single_update(lat=None, lng=None):
    """Send a single GPS update"""
    # Use KLCC as default
    lat = lat or 3.1578
    lng = lng or 101.7123

    try:
        response = requests.put(
            f"{API_BASE_URL}/riders/{RIDER_ID}/location",
            json={
                "latitude": lat,
                "longitude": lng
            },
            params={"order_id": ORDER_ID} if ORDER_ID != "your-order-id-here" else {}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Location updated: ({lat}, {lng})")
            print(f"   {data}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  BinaApp Phase 2 - GPS Location Update Test")
    print("=" * 60)

    # Check configuration
    if RIDER_ID == "your-rider-id-here":
        print("\n⚠️  WARNING: Please update RIDER_ID in this script!")
        print("   1. Get a rider ID from your database")
        print("   2. Update RIDER_ID variable at the top of this file")
        print("   3. Run the script again\n")
        exit(1)

    # Menu
    print("\nChoose test mode:")
    print("1. Single GPS update (KLCC)")
    print("2. Simulate rider movement (20 updates over 5 minutes)")
    print("3. Get current location")
    print("4. Get location history")
    print("5. Custom single update")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        single_update()
    elif choice == "2":
        confirm = input("This will send 20 updates over ~1.5 minutes. Continue? (y/n): ")
        if confirm.lower() == 'y':
            simulate_rider_movement(steps=20, delay=5)
    elif choice == "3":
        get_current_location()
    elif choice == "4":
        get_location_history()
    elif choice == "5":
        lat = float(input("Enter latitude: "))
        lng = float(input("Enter longitude: "))
        single_update(lat, lng)
    else:
        print("Invalid choice")

    print("\n" + "=" * 60)
