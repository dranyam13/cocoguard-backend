import requests
import json

BASE_URL = "http://192.168.0.188:8000"

# Try to get the analytics data without authentication first
try:
    r = requests.get(f"{BASE_URL}/analytics/admin/dashboard/summary", timeout=10)
    print(f"GET /analytics/admin/dashboard/summary: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

print()

# Try the non-admin endpoint
try:
    r = requests.get(f"{BASE_URL}/analytics/dashboard/summary", timeout=10)
    print(f"GET /analytics/dashboard/summary: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
