#!/usr/bin/env python3
"""
Performance Profiler for MCP ADHD Server
Measures startup time, memory usage, and import performance
"""

import time
import psutil
import sys
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Tuple
import cProfile
import pstats
import io
import tracemalloc
from datetime import datetime
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class PerformanceProfiler:
    """Profile server startup and runtime performance."""
    
    def __init__(self):
        self.startup_start = None
        self.startup_end = None
        self.memory_snapshots = []
        self.import_times = {}
        self.process = psutil.Process(os.getpid())
        
    def start_profiling(self):
        """Start performance profiling."""
        tracemalloc.start()
        self.startup_start = time.perf_counter()
        self.memory_snapshots.append({
            'timestamp': datetime.now().isoformat(),
            'memory_mb': self.get_memory_usage_mb(),
            'stage': 'startup_begin'
        })
        
    def record_stage(self, stage_name: str):
        """Record memory usage at a specific stage."""
        current_time = time.perf_counter()
        memory_mb = self.get_memory_usage_mb()
        
        self.memory_snapshots.append({
            'timestamp': datetime.now().isoformat(),
            'elapsed_time': current_time - self.startup_start if self.startup_start else 0,
            'memory_mb': memory_mb,
            'stage': stage_name
        })
        
        print(f"📊 Stage: {stage_name}")
        print(f"   Memory: {memory_mb:.1f}MB")
        print(f"   Elapsed: {(current_time - self.startup_start):.2f}s")
        
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
        
    def profile_imports(self) -> Dict[str, float]:
        """Profile import times for key modules."""
        import_times = {}
        
        modules_to_profile = [
            'fastapi',
            'uvicorn',
            'structlog',
            'asyncpg',
            'redis',
            'openai',
            'sqlalchemy',
            'pydantic',
            'mcp_server.main',
            'mcp_server.cognitive_loop',
            'mcp_server.emergent_evolution',
        ]
        
        for module in modules_to_profile:
            start_time = time.perf_counter()
            try:
                __import__(module)
                import_time = time.perf_counter() - start_time
                import_times[module] = import_time
                print(f"📦 Import {module}: {import_time:.3f}s")
            except ImportError as e:
                print(f"❌ Failed to import {module}: {e}")
                import_times[module] = -1
                
        return import_times
        
    def analyze_memory_snapshot(self) -> Dict:
        """Analyze current memory usage."""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        memory_analysis = {
            'total_memory_mb': self.get_memory_usage_mb(),
            'top_memory_consumers': []
        }
        
        # Top 10 memory consumers
        for index, stat in enumerate(top_stats[:10]):
            memory_analysis['top_memory_consumers'].append({
                'rank': index + 1,
                'file': stat.traceback.format()[0] if stat.traceback.format() else 'unknown',
                'size_mb': stat.size / 1024 / 1024,
                'count': stat.count
            })
            
        return memory_analysis
        
    def generate_report(self) -> Dict:
        """Generate comprehensive performance report."""
        if self.startup_start and self.startup_end:
            startup_time = self.startup_end - self.startup_start
        else:
            startup_time = -1
            
        report = {
            'timestamp': datetime.now().isoformat(),
            'startup_time_seconds': startup_time,
            'final_memory_mb': self.get_memory_usage_mb(),
            'memory_snapshots': self.memory_snapshots,
            'import_times': self.import_times,
            'memory_analysis': self.analyze_memory_snapshot(),
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'cpu_count': psutil.cpu_count(),
                'total_memory_gb': psutil.virtual_memory().total / 1024**3,
                'available_memory_gb': psutil.virtual_memory().available / 1024**3
            }
        }
        
        return report
        
    def save_report(self, report: Dict, filename: str = None):
        """Save performance report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
            
        filepath = os.path.join(os.path.dirname(__file__), '..', 'reports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"📊 Performance report saved: {filepath}")
        return filepath
        
    def print_summary(self, report: Dict):
        """Print performance summary."""
        print("\n" + "="*60)
        print("🚀 MCP ADHD SERVER PERFORMANCE REPORT")
        print("="*60)
        
        if report['startup_time_seconds'] > 0:
            print(f"⏱️  Startup Time: {report['startup_time_seconds']:.2f} seconds")
        print(f"💾 Final Memory: {report['final_memory_mb']:.1f} MB")
        print(f"🖥️  System: {psutil.cpu_count()} CPUs, {report['system_info']['total_memory_gb']:.1f}GB RAM")
        
        print(f"\n📦 Import Performance:")
        for module, import_time in report['import_times'].items():
            if import_time > 0:
                status = "⚠️" if import_time > 1.0 else "✅"
                print(f"   {status} {module}: {import_time:.3f}s")
                
        print(f"\n📊 Memory Stages:")
        for snapshot in report['memory_snapshots']:
            print(f"   {snapshot['stage']}: {snapshot['memory_mb']:.1f}MB")
            
        print(f"\n🎯 Performance Assessment:")
        startup_time = report['startup_time_seconds']
        memory_mb = report['final_memory_mb']
        
        # Performance targets from requirements
        startup_target = 5.0  # seconds
        memory_target = 200.0  # MB
        
        if startup_time > 0:
            if startup_time <= startup_target:
                print(f"   ✅ Startup time: PASS ({startup_time:.2f}s <= {startup_target}s)")
            else:
                print(f"   ❌ Startup time: FAIL ({startup_time:.2f}s > {startup_target}s)")
                
        if memory_mb <= memory_target:
            print(f"   ✅ Memory usage: PASS ({memory_mb:.1f}MB <= {memory_target}MB)")
        else:
            print(f"   ❌ Memory usage: FAIL ({memory_mb:.1f}MB > {memory_target}MB)")
            
        print("="*60)


async def profile_server_startup():
    """Profile the server startup process."""
    profiler = PerformanceProfiler()
    profiler.start_profiling()
    profiler.record_stage("profiler_started")
    
    try:
        # Profile imports with optimizations
        print("🔍 Profiling optimized imports...")
        profiler.import_times = profiler.profile_imports()
        profiler.record_stage("imports_complete")
        
        # Test the performance config
        print("⚙️  Testing performance configuration...")
        from mcp_server.performance_config import perf_config, lazy_importer
        profiler.record_stage("performance_config_loaded")
        
        # Import main app components with lazy loading
        print("🏗️  Loading optimized application components...")
        from mcp_server.main import create_app
        profiler.record_stage("app_factory_imported")
        
        # Create app instance (this should be much faster now)
        print("🔧 Creating optimized application instance...")
        app = create_app()
        profiler.record_stage("app_created")
        
        # Test lazy import statistics
        print("📊 Checking lazy import performance...")
        import_stats = lazy_importer.get_import_stats()
        if import_stats:
            print(f"   Lazy imports: {len(import_stats)} modules deferred")
            for module, time_taken in import_stats.items():
                print(f"   - {module}: {time_taken:.3f}s")
        
        # Simulate core system initialization without starting server
        print("⚙️  Testing core systems...")
        from mcp_server.config import settings
        from mcp_server import health_monitor, metrics_collector, alert_manager
        profiler.record_stage("core_components_loaded")
        
        profiler.startup_end = time.perf_counter()
        profiler.record_stage("startup_complete")
        
        # Generate and save report
        report = profiler.generate_report()
        profiler.print_summary(report)
        filepath = profiler.save_report(report)
        
        return report, filepath
        
    except Exception as e:
        print(f"❌ Error during profiling: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def profile_memory_usage():
    """Profile current memory usage patterns."""
    profiler = PerformanceProfiler()
    memory_analysis = profiler.analyze_memory_snapshot()
    
    print("\n🧠 Memory Usage Analysis:")
    print(f"Total Memory: {memory_analysis['total_memory_mb']:.1f}MB")
    print("\nTop Memory Consumers:")
    
    for consumer in memory_analysis['top_memory_consumers']:
        print(f"  {consumer['rank']}. {consumer['size_mb']:.2f}MB - {consumer['file']}")
        
    return memory_analysis


if __name__ == "__main__":
    print("🚀 Starting MCP ADHD Server Performance Profiling...")
    
    # Run performance profiling
    report, filepath = asyncio.run(profile_server_startup())
    
    if report:
        print(f"\n✅ Profiling complete. Report saved to: {filepath}")
    else:
        print("❌ Profiling failed.")