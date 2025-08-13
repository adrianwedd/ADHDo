#\!/usr/bin/env python3
import requests

# Try schedule-based approach
url = "http://localhost:23443/schedule/add"
data = {
    "schedule_type": "bedtime",
    "target_time": "22:41",
    "title": "URGENT BEDTIME TEST",
    "pre_nudge_minutes": 0,
    "escalation_intervals": [1, 2, 3]
}

response = requests.post(url, json=data)
print(f"Response: {response.status_code}")
print(f"Body: {response.text}")
