#!/usr/bin/env python3
"""Debug Chromecast object structure."""
import pychromecast

print("🔍 Discovering Chromecast devices for debugging...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

for cc in chromecasts:
    if 'nest hub max' in cc.model_name.lower():
        print(f"\n📱 {cc.name} ({cc.model_name})")
        print(f"Dir: {[attr for attr in dir(cc) if not attr.startswith('_')]}")
        print(f"Host: {getattr(cc, 'host', 'NO HOST ATTR')}")
        print(f"Port: {getattr(cc, 'port', 'NO PORT ATTR')}")
        
        # Check if it has a .device attribute
        if hasattr(cc, 'device'):
            print(f"Device attr: {cc.device}")
            print(f"Device dir: {[attr for attr in dir(cc.device) if not attr.startswith('_')]}")
        
        # Check if it has other connection attributes
        for attr in ['uri', 'socket_client', '_socket_client']:
            if hasattr(cc, attr):
                print(f"{attr}: {getattr(cc, attr)}")
        
        break

browser.stop_discovery()