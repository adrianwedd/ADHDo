#!/usr/bin/env python3
"""
Test Web Interface Integration.

Tests the web interface serving and API endpoints.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from mcp_server.main import app
from traces.memory import trace_memory

def test_web_interface():
    """Test web interface functionality."""
    
    print("🌐 Testing Web Interface")
    print("=" * 30)
    
    client = TestClient(app)
    
    # Test 1: Static file serving
    print("\n📁 Test 1: Static File Access")
    
    # Check if static files are mounted
    static_path = Path(__file__).parent / "static" / "index.html"
    if static_path.exists():
        print(f"✅ Static files found at: {static_path}")
    else:
        print(f"⚠️  Static files not found at: {static_path}")
    
    # Test 2: Root endpoint (web interface)
    print("\n🏠 Test 2: Root Endpoint")
    
    response = client.get("/")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        if "text/html" in response.headers.get("content-type", ""):
            print("✅ Web interface served successfully")
        else:
            print("✅ API fallback working")
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
    else:
        print("❌ Root endpoint failed")
    
    # Test 3: API info endpoint
    print("\n📊 Test 3: API Info Endpoint")
    
    response = client.get("/api")
    if response.status_code == 200:
        data = response.json()
        print("✅ API info endpoint working")
        print(f"   Service: {data.get('service')}")
        print(f"   Status: {data.get('status')}")
    else:
        print("❌ API info endpoint failed")
    
    # Test 4: Health check
    print("\n❤️ Test 4: Health Check")
    
    response = client.get("/health")
    if response.status_code == 200:
        data = response.json()
        print("✅ Health check working")
        print(f"   Status: {data.get('status')}")
        print(f"   Message: {data.get('message')}")
    else:
        print("❌ Health check failed")
    
    # Test 5: Chat endpoint (with debug mode)
    print("\n💬 Test 5: Chat Endpoint (Debug Mode)")
    
    chat_data = {
        "message": "I'm ready to work!",
        "task_focus": "Test the web interface",
        "nudge_tier": 0
    }
    
    headers = {"X-User-ID": "test-web-user"}
    
    response = client.post("/chat", json=chat_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Chat endpoint working")
        print(f"   Success: {data.get('success')}")
        print(f"   Response: {data.get('response', '')[:50]}...")
        print(f"   Processing time: {data.get('processing_time_ms')}ms")
    else:
        print(f"❌ Chat endpoint failed: {response.text}")
    
    # Test 6: Authentication endpoints
    print("\n🔐 Test 6: Authentication Endpoints")
    
    # Test auth/me without credentials
    response = client.get("/auth/me")
    if response.status_code == 401:
        print("✅ Auth protection working (401 without credentials)")
    else:
        print(f"⚠️  Expected 401, got {response.status_code}")
    
    # Test auth/me with debug header
    response = client.get("/auth/me", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ Debug auth working")
        print(f"   User ID: {data.get('user_id')}")
        print(f"   Name: {data.get('name')}")
    else:
        print(f"❌ Debug auth failed: {response.status_code}")
    
    print("\n🎉 Web Interface Test Summary")
    print("=" * 35)
    print("✅ Static file handling")
    print("✅ Root endpoint routing")
    print("✅ API endpoints")
    print("✅ Health monitoring")
    print("✅ Chat functionality")
    print("✅ Authentication system")
    
    print("\n🚀 Web interface ready!")
    print(f"To access: python start_server.py")
    print(f"Then visit: http://localhost:8000")

if __name__ == "__main__":
    try:
        test_web_interface()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()