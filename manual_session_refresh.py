#!/usr/bin/env python3
"""
Manual Claude Session Refresh Helper
Quick way to update session key without browser automation
"""

import os
import sys

print("🔄 Claude Session Refresh Helper")
print("=" * 50)
print()
print("📝 INSTRUCTIONS:")
print("1. Open Claude.ai in your browser")
print("2. Make sure you're logged in")
print("3. Open Developer Tools (F12)")
print("4. Go to Application/Storage → Cookies")
print("5. Find the 'sessionKey' cookie")
print("6. Copy its value")
print()

session_key = input("Paste the sessionKey value here: ").strip()

if not session_key:
    print("❌ No session key provided")
    sys.exit(1)

# Remove quotes if present
session_key = session_key.strip('"').strip("'")

print(f"\n✅ Got session key: {session_key[:20]}...")

# Update .env file
env_file = '.env'
lines = []
found = False

if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if line.startswith('CLAUDE_SESSION_KEY='):
            lines[i] = f'CLAUDE_SESSION_KEY="{session_key}"\n'
            found = True
            break

if not found:
    lines.append(f'CLAUDE_SESSION_KEY="{session_key}"\n')

with open(env_file, 'w') as f:
    f.writelines(lines)

print("✅ Updated .env file")
print()
print("🔄 Restarting server...")
os.system("sudo systemctl restart adhdo")

print("⏳ Waiting for server to start...")
import time
time.sleep(5)

# Test the connection
print("\n🧪 Testing Claude connection...")
import subprocess
result = subprocess.run([
    'curl', '-X', 'POST', 
    'http://localhost:23443/claude/v2/chat',
    '-H', 'Content-Type: application/json',
    '-d', '{"message": "Test. Say: Session refreshed successfully", "user_id": "test"}',
    '-s'
], capture_output=True, text=True)

if result.returncode == 0:
    import json
    try:
        response = json.loads(result.stdout)
        if 'response' in response:
            print(f"✅ Claude responded: {response['response'][:100]}...")
            print("\n🎉 Session refresh complete!")
        else:
            print("⚠️ Got response but format unexpected")
            print(result.stdout[:200])
    except:
        print("⚠️ Response parsing failed")
        print(result.stdout[:200])
else:
    print("❌ Connection test failed")
    print(result.stderr)

print("\n✨ Done!")