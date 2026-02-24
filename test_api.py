import requests
import json

# Test the API endpoint directly
url = "http://192.168.0.188:8000/api/analytics/admin/dashboard/summary"

# First, we need to login to get a token
login_url = "http://192.168.0.188:8000/api/auth/login"
login_data = {
    "email": "admin@cocoguard.com",
    "password": "admin123"
}

try:
    # Login
    login_resp = requests.post(login_url, json=login_data, timeout=10)
    print(f"Login status: {login_resp.status_code}")
    
    if login_resp.status_code == 200:
        token = login_resp.json().get("access_token")
        print(f"Got token: {token[:50]}...")
        
        # Call dashboard summary
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"\nDashboard API status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\nFull response:")
            print(json.dumps(data, indent=2, default=str)[:2000])
            print(f"\ntoday_scans: {data.get('today_scans')}")
            print(f"yesterday_scans: {data.get('yesterday_scans')}")
        else:
            print(f"Error: {resp.text}")
    else:
        print(f"Login failed: {login_resp.text}")
        
except Exception as e:
    print(f"Error: {e}")
