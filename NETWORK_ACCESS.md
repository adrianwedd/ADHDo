# Network Access Guide - MCP ADHD Server

## 🌐 Access Your ADHD Support System from Any Device

Your MCP ADHD Server is now configured for local network access, allowing you to use it from:
- Your phone, tablet, laptop
- Other devices on your home/office network  
- Multiple browsers simultaneously

## 🚀 Quick Start

### Option 1: Use the Network Startup Script
```bash
cd /home/pi/repos/ADHDo
./start_network.sh
```

### Option 2: Manual Startup
```bash
cd /home/pi/repos/ADHDo
PORT=8080 PYTHONPATH=src /home/pi/repos/ADHDo/venv_beta/bin/python src/mcp_server/minimal_main.py
```

## 📡 Network URLs

Replace `192.168.1.100` with your Pi's actual IP address:

- **Main API**: http://192.168.1.100:23443
- **Health Check**: http://192.168.1.100:23443/health  
- **API Documentation**: http://192.168.1.100:23443/docs
- **Chat Interface**: POST to http://192.168.1.100:23443/chat

## 💬 Using from Other Devices

### From a Phone/Tablet Browser
Navigate to: `http://192.168.1.100:23443/docs`

Use the interactive API interface to:
1. Test the `/chat` endpoint
2. Check system `/health`  
3. Connect Claude Pro via `/claude/authenticate`

### From curl/Postman
```bash
# Test ADHD support
curl -X POST http://192.168.1.100:23443/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help focusing on my work",
    "user_id": "your_device_id"
  }'

# Check system health
curl http://192.168.1.100:23443/health
```

### From JavaScript/App
```javascript
const response = await fetch('http://192.168.1.100:23443/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "I'm feeling overwhelmed with my tasks",
    user_id: "mobile_app"
  })
});
const result = await response.json();
console.log(result.response); // ADHD-optimized advice
```

## 🔒 Security Notes

- **Local Network Only**: Server only accessible within your local network
- **No Authentication Required**: Direct access for convenience  
- **Claude Integration**: Requires manual authentication via browser
- **Crisis Detection**: Always active regardless of access method

## 🎯 ADHD Features Available

All sophisticated features work over the network:

✅ **Pattern Matching**: <1ms responses for common ADHD needs
✅ **Crisis Detection**: Immediate safety resources if needed  
✅ **Circuit Breaker**: Psychological protection system
✅ **Claude Integration**: Connect your Claude Pro/Max subscription
✅ **Local Privacy**: Ollama reasoning stays on your Pi

## 📱 Mobile-Friendly Usage

The system is optimized for ADHD users across all devices:
- **Quick Responses**: Sub-3 second reply times
- **Short Messages**: Concise, actionable advice
- **Multiple Access**: Use from phone, laptop, tablet simultaneously
- **Offline Resilience**: Local Ollama works without internet

## 🔧 Troubleshooting

**Can't connect from other devices?**
1. Check Pi's IP: `hostname -I`
2. Verify server is running: `curl http://localhost:23443/health`
3. Test network access: `ping 192.168.1.100` from other device

**Port conflicts?**
- Change PORT environment variable: `PORT=23444 ./start_network.sh`
- Check what's using ports: `sudo lsof -i :23443`

**Performance issues?**
- Use pattern-matched responses for speed (work well for most ADHD needs)
- Connect Claude Pro for complex reasoning tasks
- Local Ollama is slow but private (8-15 second responses)

Your ADHD support system is now accessible from any device on your network! 🎉