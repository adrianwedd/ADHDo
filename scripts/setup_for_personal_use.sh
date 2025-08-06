#!/bin/bash

# MCP ADHD Server - Personal Setup Script
# Complete automated setup for immediate personal use

set -e

echo "🧠⚡ Setting up YOUR MCP ADHD Server for personal use..."

# Get the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Run the main setup
echo "📦 Running system setup..."
./scripts/auto_setup.sh

# Check if OpenAI API key is needed
echo ""
echo "🔑 API KEY SETUP:"
if ! grep -q "sk-" .env; then
    echo "❗ You need an OpenAI API key to use the AI features!"
    echo "   1. Go to: https://platform.openai.com/api-keys"
    echo "   2. Create a new key"
    echo "   3. Run: echo 'OPENAI_API_KEY=your_key_here' >> .env"
    echo ""
fi

# Set up Telegram bot
echo "📱 TELEGRAM BOT SETUP:"
echo "Want nudges on your phone? Let's set up your Telegram bot!"
read -p "Set up Telegram bot now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/setup_telegram_bot.py
else
    echo "ℹ️  You can set up Telegram later with: python scripts/setup_telegram_bot.py"
fi

# Start the server
echo ""
echo "🚀 STARTING YOUR PERSONAL ADHD SERVER..."
echo "Server will start at: http://localhost:8000"

# Create a beta invite for yourself
echo "Creating your personal invite..."
PYTHONPATH=src python -c "
from mcp_server.beta_onboarding import beta_onboarding
import sys

# Create personal invite
invite = beta_onboarding.create_invite(expires_hours=8760, name='Personal Use')  # 1 year
setup_url = beta_onboarding.generate_setup_url(invite.invite_code)

print()
print('🎟️  YOUR PERSONAL SETUP LINK:')
print(f'   {setup_url}')
print()
print('💾 Save this link! You can use it to create your account.')
print()
"

echo "Starting server in background..."
./start_personal_server.sh &

# Wait for server to start
echo "Waiting for server to start..."
sleep 10

# Test server
if curl -s http://localhost:8000/health > /dev/null; then
    echo ""
    echo "🎉 SUCCESS! Your MCP ADHD Server is running!"
    echo ""
    echo "📍 Next Steps:"
    echo "1. Open: http://localhost:8000"
    echo "2. Create your account (or use the setup link above)"
    echo "3. Start chatting with your AI assistant!"
    echo "4. Get nudged and stay productive! 🎯"
    echo ""
    echo "🔧 Advanced Setup:"
    echo "• Add Google Home integration for watch nudges"
    echo "• Set up calendar sync" 
    echo "• Configure custom energy patterns"
    echo ""
    echo "💬 Need help? Your assistant is ready to chat!"
    
    # Open browser if possible
    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:8000
    elif command -v open > /dev/null; then
        open http://localhost:8000
    fi
else
    echo "❌ Server didn't start properly. Check the logs above."
    exit 1
fi