#!/usr/bin/env python3
"""Debug Chromecast socket client structure."""
import pychromecast

print("🔍 Discovering Chromecast devices for socket client debugging...")
chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

for cc in chromecasts:
    if 'nest hub max' in cc.model_name.lower():
        print(f"\n📱 {cc.name} ({cc.model_name})")
        print(f"URI: {cc.uri}")
        
        if hasattr(cc, 'socket_client'):
            sc = cc.socket_client
            print(f"Socket client: {sc}")
            print(f"Socket client dir: {[attr for attr in dir(sc) if not attr.startswith('_')]}")
            
            # Check common attributes
            for attr in ['host', 'port', 'address']:
                if hasattr(sc, attr):
                    print(f"Socket client {attr}: {getattr(sc, attr)}")
        
        # Parse URI manually
        uri_parts = cc.uri.split(':')
        if len(uri_parts) == 2:
            host = uri_parts[0]
            port = int(uri_parts[1])
            print(f"Parsed from URI - Host: {host}, Port: {port}")
        
        break

browser.stop_discovery()