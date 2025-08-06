# Quick Start - MCP ADHD Server 🚀

> **TL;DR**: 5 minutes to get your ADHD support system running. Copy commands, paste, edit one file, done! No overwhelming technical stuff.

**Perfect for**: People who just want it to work, ADHD developers who need clear steps, anyone who gets decision paralysis with too many options.

## ⚡ Super Quick Start (2 minutes)

**Prerequisites**: Docker installed on your computer. That's it.

```bash
# 1. Get the code
git clone https://github.com/adrianwedd/ADHDo.git
cd ADHDo

# 2. Set up environment
cp .env.example .env

# 3. Edit ONLY these required lines in .env:
# OPENAI_API_KEY=sk-your-key-here
# SECRET_KEY=make-up-a-32-character-password

# 4. Start everything
docker-compose up -d

# 5. Test it works
curl http://localhost:8000/health
```

**Done!** Visit `http://localhost:8000` and start chatting with your ADHD support AI.

## 🎯 What You Just Built

**TL;DR**: A complete ADHD support system running on your computer. No cloud, no subscriptions, your data stays private.

- ✅ **Web interface**: Chat with AI optimized for ADHD minds
- ✅ **Authentication**: Secure account system 
- ✅ **Telegram bot**: Mobile support (optional)
- ✅ **Database**: Stores your conversations and preferences
- ✅ **Monitoring**: Built-in health checks and performance tracking

## 🔧 Required Setup Details

### Get Your OpenAI API Key

**TL;DR**: Visit OpenAI, create account, get API key, paste it in .env file.

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create account or sign in
3. Click "API keys" in left sidebar
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)
6. Paste it in `.env` file: `OPENAI_API_KEY=sk-your-key-here`

**Cost**: ~$5-20/month depending on usage. ADHD-optimized for efficiency.

### Create a Secret Key

**TL;DR**: Make up a random 32-character password for security.

```bash
# Generate one automatically (Linux/Mac):
openssl rand -base64 32

# Or make one up (any 32 characters):
SECRET_KEY=your-super-secret-32-char-key-here
```

Paste it in `.env` file: `SECRET_KEY=your-generated-key`

## 📱 Optional: Telegram Bot Setup

**TL;DR**: Skip if you don't want mobile support. If you do, takes 2 minutes.

### Create Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Choose a name: "My ADHD Assistant"  
4. Choose username: "your_name_adhd_bot"
5. Copy the token (looks like `123456789:ABC-DEF...`)
6. Add to `.env`: `TELEGRAM_BOT_TOKEN=your-token-here`

### Connect Your Account

1. Find your bot on Telegram
2. Send `/start`
3. Follow instructions to link your web account

**Done!** Now you get ADHD support on your phone too.

## 🎮 Using Your ADHD Server

### Web Interface

**TL;DR**: Visit `http://localhost:8000`, sign up, start chatting.

1. **Sign Up**: Click "Sign In" → "Don't have account? Sign up"
2. **Create Account**: Name, email, password (ADHD-friendly validation)
3. **Optional Onboarding**: Customize your ADHD support (or skip)
4. **Start Chatting**: Type anything - "I can't focus today" or "Help me get started"

### What to Try First

**TL;DR**: Real conversation starters that work well with the ADHD AI.

```
"I have 10 things to do and can't pick where to start"
"I'm feeling overwhelmed by my to-do list"  
"Help me break down this big project"
"I keep getting distracted, what should I do?"
"I finished something! Let's celebrate"
```

### ADHD-Specific Features

- **Performance Tracking**: See response times (should be <3 seconds)
- **Task Focus Settings**: Adjust how the AI helps you focus
- **Nudge Tier Control**: Set how gentle or firm you want reminders
- **Crisis Support**: AI detects overwhelm and offers de-escalation
- **Win Celebration**: Dopamine-friendly achievement recognition

## 🚨 Troubleshooting (When Things Don't Work)

### "Server won't start"

**TL;DR**: Most common issue - Docker not running or ports in use.

```bash
# Check if Docker is running
docker --version

# Check what's using port 8000
lsof -i :8000

# If something's using port 8000, change it:
# Edit docker-compose.yml, change "8000:8000" to "8080:8000"
# Then visit http://localhost:8080 instead
```

### "Can't connect to OpenAI"

**TL;DR**: Check your API key is correct and has credits.

```bash
# Test your API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-your-key-here"

# Should return list of models. If not, check:
# 1. Key is correct (no extra spaces)
# 2. Account has credits
# 3. Key has proper permissions
```

### "Database errors"

**TL;DR**: Database container didn't start properly.

```bash
# Check container status
docker-compose ps

# Restart database
docker-compose restart db

# If still broken, reset everything:
docker-compose down
docker-compose up -d
# (This will lose data, but fine for testing)
```

### "Too slow / timing out"

**TL;DR**: Server needs more resources or network is slow.

```bash
# Check system resources
docker stats

# If high CPU/memory usage:
# 1. Close other applications
# 2. Increase Docker resource limits
# 3. Try smaller OpenAI model (in .env: MODEL_NAME=gpt-3.5-turbo)
```

## 🎯 Next Steps

### For Regular Use

**TL;DR**: Daily workflow tips for getting the most from your ADHD server.

- **Morning Setup**: Quick check-in with your goals
- **During Work**: Chat when you feel stuck or overwhelmed  
- **Task Switching**: Ask for help prioritizing
- **End of Day**: Celebrate what you accomplished
- **Mobile**: Use Telegram bot for quick nudges and check-ins

### For Developers

**TL;DR**: How to customize and extend your ADHD server.

```bash
# Development setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run in development mode
cd src
PYTHONPATH=. python -m uvicorn mcp_server.main:app --reload

# Make changes to:
# - src/mcp_server/ (backend code)
# - static/ (web interface)
# - tests/ (add your own tests)
```

### Production Deployment

**TL;DR**: Ready to deploy for others or make it public? Check the full deployment guide.

- Read `DEPLOYMENT_GUIDE.md` for production setup
- Configure HTTPS and domain name
- Set up proper monitoring and backups
- Review security checklist

## 📚 Getting Help

### Quick References

**TL;DR**: Where to find answers without getting overwhelmed.

- **Health Check**: Visit `http://localhost:8000/health`
- **API Docs**: Visit `http://localhost:8000/docs`
- **System Status**: `docker-compose logs adhd-server`
- **Database**: `docker-compose logs db`

### Support Channels

- **🐛 Bug Reports**: GitHub Issues (include error messages)
- **💡 Feature Requests**: GitHub Issues (describe ADHD use case)
- **❓ Questions**: GitHub Discussions
- **💬 Community**: ADHD Developer Discord (link)

### For ADHD Developers

**We get it.** This project is built by ADHD minds for ADHD minds. Don't feel bad about:

- Needing simple instructions
- Asking "obvious" questions  
- Taking breaks during setup
- Not reading all the documentation
- Wanting things to "just work"

**You're not broken.** The tools should work for your brain, not against it.

---

## 🎉 Success! What You Built

**TL;DR**: You now have a complete ADHD support system. It's yours, it's private, and it actually understands how ADHD minds work.

### What's Running

- **Web Server**: FastAPI handling requests and AI chat
- **Database**: PostgreSQL storing your data securely
- **Cache**: Redis making everything faster  
- **Monitoring**: Grafana tracking system health
- **Optional**: Telegram bot for mobile access

### What's Special About This

- **<3 Second Responses**: Optimized for ADHD attention spans
- **No Shame Language**: Supportive AI that doesn't judge
- **Privacy First**: Your data stays on your server
- **Crisis Support**: Detects overwhelm and helps de-escalate
- **Built by ADHDers**: We understand executive function struggles

### You Did It!

Setting up a complete AI system is no small task. Your ADHD brain just accomplished something pretty awesome. 

**Ready to get some executive function support?** Start chatting! 🧠⚡

---

*"Because ADHD minds deserve tools that actually work for them, not against them."*