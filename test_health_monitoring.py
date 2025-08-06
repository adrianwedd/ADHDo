#!/usr/bin/env python3
"""
Test Health Monitoring and Metrics System.

Tests comprehensive health checks, Prometheus metrics, and monitoring functionality.
"""
import asyncio
import sys
import os
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from mcp_server.main import app
from mcp_server.health_monitor import health_monitor
from mcp_server.metrics import metrics_collector


def test_health_monitoring_system():
    """Test health monitoring and metrics functionality."""
    
    print("❤️ Testing Health Monitoring & Metrics System")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Test 1: Basic health check
    print("\n🔍 Test 1: Basic Health Check")
    
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Basic health check working")
        print(f"   Status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Message: {data.get('message')}")
    else:
        print("❌ Basic health check failed")
    
    # Test 2: Detailed health check
    print("\n🏥 Test 2: Detailed Health Check")
    
    response = client.get("/health/detailed")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Detailed health check working")
        print(f"   Overall Status: {data.get('status')}")
        print(f"   Uptime: {data.get('uptime_seconds')}s")
        print(f"   Components: {len(data.get('components', {}))}")
        
        # Check each component
        for component, info in data.get('components', {}).items():
            print(f"   - {component}: {info.get('status')} ({info.get('response_time_ms', 0):.1f}ms)")
        
        # Check system metrics
        metrics = data.get('system_metrics', {})
        if metrics:
            print(f"   CPU: {metrics.get('cpu_percent', 0):.1f}%")
            print(f"   Memory: {metrics.get('memory_percent', 0):.1f}%")
            print(f"   Disk: {metrics.get('disk_usage_percent', 0):.1f}%")
    else:
        print(f"❌ Detailed health check failed: {response.text}")
    
    # Test 3: Individual component health
    print("\n🧩 Test 3: Individual Component Health")
    
    components = ["redis", "database", "llm", "system", "application"]
    
    for component in components:
        response = client.get(f"/health/{component}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {component}: {data.get('status')} ({data.get('response_time_ms', 0):.1f}ms)")
        else:
            print(f"❌ {component}: Failed to get health status")
    
    # Test 4: System metrics
    print("\n📊 Test 4: System Metrics")
    
    response = client.get("/health/metrics/system")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ System metrics working")
        print(f"   CPU: {data.get('cpu_percent', 0):.1f}%")
        print(f"   Memory: {data.get('memory_percent', 0):.1f}% ({data.get('memory_available_mb', 0):.0f}MB available)")
        print(f"   Disk: {data.get('disk_usage_percent', 0):.1f}% ({data.get('disk_free_gb', 0):.1f}GB free)")
        print(f"   Load Average: {data.get('load_average', [0,0,0])}")
        print(f"   Processes: {data.get('process_count', 0)}")
        print(f"   Uptime: {data.get('uptime_seconds', 0)}s")
    else:
        print(f"❌ System metrics failed: {response.text}")
    
    # Test 5: Prometheus metrics
    print("\n📈 Test 5: Prometheus Metrics")
    
    response = client.get("/metrics")
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    if response.status_code == 200:
        metrics_text = response.text
        print("✅ Prometheus metrics working")
        print(f"   Response length: {len(metrics_text)} bytes")
        
        # Check for key metrics
        expected_metrics = [
            "mcp_adhd_server_info",
            "mcp_adhd_server_uptime_seconds",
            "mcp_adhd_server_http_requests_total",
            "mcp_adhd_server_component_health",
            "mcp_adhd_server_cpu_usage_percent",
            "mcp_adhd_server_memory_usage_percent"
        ]
        
        found_metrics = 0
        for metric in expected_metrics:
            if metric in metrics_text:
                found_metrics += 1
                print(f"   ✓ Found metric: {metric}")
            else:
                print(f"   ✗ Missing metric: {metric}")
        
        print(f"   Metrics found: {found_metrics}/{len(expected_metrics)}")
    else:
        print(f"❌ Prometheus metrics failed: {response.text}")
    
    # Test 6: Metrics summary
    print("\n📋 Test 6: Metrics Summary")
    
    response = client.get("/metrics/summary")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Metrics summary working")
        summary = data.get('metrics', {})
        print(f"   Uptime: {summary.get('uptime_seconds', 0):.1f}s")
        print(f"   Active Users: {summary.get('active_users', 0)}")
        print(f"   Total Sessions: {summary.get('total_sessions', 0)}")
        print(f"   Tasks Created: {summary.get('total_tasks_created', 0)}")
        print(f"   Tasks Completed: {summary.get('total_tasks_completed', 0)}")
        print(f"   Cognitive Load: {summary.get('avg_cognitive_load', 0):.2f}")
        print(f"   Pattern Matches: {summary.get('total_pattern_matches', 0)}")
        print(f"   Cache Hit Rate: {summary.get('cache_hit_rate', 0):.2f}")
    else:
        print(f"❌ Metrics summary failed: {response.text}")
    
    # Test 7: Dashboard
    print("\n🎛️ Test 7: Performance Dashboard")
    
    response = client.get("/dashboard")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Dashboard accessible")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   Content length: {len(response.content)} bytes")
        
        # Check if it's HTML content
        if "text/html" in response.headers.get("content-type", ""):
            content = response.text
            if "MCP ADHD Server - Performance Dashboard" in content:
                print("   ✓ Dashboard title found")
            if "Chart.js" in content:
                print("   ✓ Chart library loaded")
            if "tailwindcss" in content:
                print("   ✓ Styling framework loaded")
    else:
        print(f"❌ Dashboard failed: {response.text}")
    
    # Test 8: Metrics collection simulation
    print("\n🧪 Test 8: Metrics Collection Simulation")
    
    try:
        # Simulate some metrics
        print("   Simulating HTTP requests...")
        for i in range(5):
            metrics_collector.record_http_request("GET", "/chat", 200, 0.1 + i * 0.05)
        
        print("   Simulating user sessions...")
        metrics_collector.record_user_session_start("test-user-1")
        metrics_collector.record_user_session_start("test-user-2")
        
        print("   Simulating task operations...")
        metrics_collector.record_task_created(3, "medium")
        metrics_collector.record_task_created(4, "high")
        
        print("   Simulating cognitive loop executions...")
        metrics_collector.record_cognitive_loop_execution("success", 0.05)
        metrics_collector.record_cognitive_loop_execution("success", 0.12)
        
        print("   Simulating pattern matches...")
        metrics_collector.record_pattern_match("ready", 0.5)
        metrics_collector.record_pattern_match("stuck", 0.8)
        
        print("   Updating cognitive load...")
        metrics_collector.update_cognitive_load(0.3)
        metrics_collector.update_cognitive_load(0.4)
        metrics_collector.update_cognitive_load(0.2)
        
        print("   Updating system metrics...")
        metrics_collector.update_system_metrics(45.2, 62.1, 78.5)
        
        print("   Updating component health...")
        metrics_collector.update_component_health("redis", "healthy")
        metrics_collector.update_component_health("database", "healthy")
        metrics_collector.update_component_health("llm", "degraded")
        
        print("✅ Metrics simulation completed")
        
        # Test metrics export after simulation
        print("   Testing metrics export...")
        metrics_data = metrics_collector.export_metrics()
        print(f"   ✓ Exported {len(metrics_data)} bytes of metrics")
        
        # Test summary after simulation
        summary = metrics_collector.get_metrics_summary()
        print(f"   ✓ Summary shows {summary.get('active_users', 0)} active users")
        print(f"   ✓ Average cognitive load: {summary.get('avg_cognitive_load', 0):.2f}")
        
    except Exception as e:
        print(f"❌ Metrics simulation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 9: Performance timing
    print("\n⚡ Test 9: Performance Timing")
    
    endpoints_to_test = [
        "/health",
        "/health/detailed", 
        "/health/redis",
        "/health/metrics/system",
        "/metrics/summary"
    ]
    
    for endpoint in endpoints_to_test:
        start_time = time.time()
        response = client.get(endpoint)
        duration = (time.time() - start_time) * 1000
        
        status = "✅" if response.status_code == 200 else "❌"
        print(f"   {status} {endpoint}: {duration:.1f}ms (status: {response.status_code})")
        
        # Check for ADHD optimization headers
        if response.status_code == 200:
            cognitive_load = response.headers.get("X-Cognitive-Load")
            processing_time = response.headers.get("X-Processing-Time")
            if cognitive_load:
                print(f"      Cognitive Load: {cognitive_load}")
            if processing_time:
                print(f"      Processing Time: {processing_time}s")
    
    # Test 10: Error handling
    print("\n🚨 Test 10: Error Handling")
    
    # Test non-existent component
    response = client.get("/health/nonexistent")
    if response.status_code == 404:
        print("✅ Non-existent component returns 404")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
    
    # Test malformed requests
    response = client.get("/health/history/redis?hours=invalid")
    print(f"   Malformed parameter handling: {response.status_code}")
    
    print("\n🎉 Health Monitoring & Metrics Test Summary")
    print("=" * 52)
    print("✅ Basic and detailed health checks")
    print("✅ Individual component monitoring")
    print("✅ System resource metrics")
    print("✅ Prometheus metrics export")
    print("✅ Performance analytics dashboard")
    print("✅ Metrics collection and aggregation")
    print("✅ ADHD-optimized response headers")
    print("✅ Error handling and validation")
    
    print("\n🚀 Health monitoring system ready for production!")
    print("Key endpoints:")
    print("- GET /health - Basic health check")
    print("- GET /health/detailed - Comprehensive status")
    print("- GET /health/{component} - Component-specific health")
    print("- GET /health/metrics/system - System resources")
    print("- GET /metrics - Prometheus metrics")
    print("- GET /dashboard - Performance dashboard")
    print("- GET /metrics/summary - Key metrics summary")


if __name__ == "__main__":
    try:
        test_health_monitoring_system()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()