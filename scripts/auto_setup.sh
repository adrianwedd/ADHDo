#!/bin/bash

# MCP ADHD Server - Automated Setup Script
# This script handles complete environment setup for beta testers

set -e  # Exit on any error

echo "🧠⚡ MCP ADHD Server - Automated Setup Starting..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_status "Project directory: $PROJECT_DIR"

# Check if we're in the right directory
if [[ ! -f "$PROJECT_DIR/pyproject.toml" ]] || [[ ! -d "$PROJECT_DIR/src/mcp_server" ]]; then
    print_error "Script must be run from the MCP ADHD Server project directory"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
print_status "Checking system requirements..."

# Check Python
if ! command_exists python3; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_error "Python 3.9+ is required, found Python $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION found"

# Install system dependencies
print_status "Installing system dependencies..."

if command_exists apt-get; then
    # Ubuntu/Debian
    sudo apt-get update -qq
    sudo apt-get install -y redis-server curl jq
    sudo systemctl start redis-server 2>/dev/null || true
    sudo systemctl enable redis-server 2>/dev/null || true
elif command_exists yum; then
    # CentOS/RHEL
    sudo yum install -y redis curl jq
    sudo systemctl start redis
    sudo systemctl enable redis
elif command_exists brew; then
    # macOS
    brew install redis curl jq
    brew services start redis
else
    print_warning "Unknown package manager. Please install Redis, curl, and jq manually"
fi

# Test Redis connection
if redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is running"
else
    print_error "Redis is not running. Please start Redis manually"
    exit 1
fi

# Create virtual environment
print_status "Setting up Python virtual environment..."

cd "$PROJECT_DIR"

if [[ -d "venv_beta" ]]; then
    print_status "Virtual environment exists, updating..."
else
    print_status "Creating new virtual environment..."
    python3 -m venv venv_beta
fi

# Activate virtual environment
source venv_beta/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
print_status "Setting up environment configuration..."

if [[ ! -f ".env" ]]; then
    cp scripts/templates/.env.template .env
    print_success "Created .env file from template"
else
    print_status ".env file already exists"
fi

# Generate secure secrets
print_status "Generating secure secrets..."
JWT_SECRET=$(openssl rand -base64 32)
sed -i "s/your-secret-key-change-in-production/$JWT_SECRET/g" .env

# Initialize database
print_status "Initializing database..."
PYTHONPATH=src python -c "
import asyncio
from mcp_server.database import init_database
asyncio.run(init_database())
print('Database initialized successfully')
"

# Test server startup
print_status "Testing server startup..."
timeout 10s bash -c '
    PYTHONPATH=src python -m uvicorn mcp_server.main:app --host 127.0.0.1 --port 8001 > /dev/null 2>&1 &
    SERVER_PID=$!
    sleep 5
    
    # Test health endpoint
    if curl -s http://127.0.0.1:8001/health > /dev/null; then
        echo "Server startup test successful"
        kill $SERVER_PID 2>/dev/null || true
        exit 0
    else
        echo "Server startup test failed"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
' || {
    print_error "Server startup test failed"
    exit 1
}

print_success "Server startup test passed"

# Create systemd service for production
print_status "Creating systemd service..."

sudo tee /etc/systemd/system/mcp-adhd-server.service > /dev/null <<EOF
[Unit]
Description=MCP ADHD Server
After=network.target redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv_beta/bin
Environment=PYTHONPATH=$PROJECT_DIR/src
ExecStart=$PROJECT_DIR/venv_beta/bin/python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
print_success "Systemd service created"

# Create startup script
print_status "Creating convenient startup script..."

cat > start_personal_server.sh << 'EOF'
#!/bin/bash

# MCP ADHD Server - Personal Startup Script
cd "$(dirname "$0")"

echo "🧠⚡ Starting your personal MCP ADHD Server..."

# Activate virtual environment
source venv_beta/bin/activate

# Start server
PYTHONPATH=src python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000 --reload

EOF

chmod +x start_personal_server.sh
print_success "Created start_personal_server.sh"

print_success "🎉 Setup complete! Your MCP ADHD Server is ready!"
print_status ""
print_status "Next steps:"
print_status "1. Edit .env file to add your OpenAI API key and Telegram bot token"
print_status "2. Run: ./start_personal_server.sh"
print_status "3. Open http://localhost:8000 in your browser"
print_status "4. Create your account and start getting nudged!"
print_status ""
print_status "For production deployment:"
print_status "• sudo systemctl start mcp-adhd-server"
print_status "• sudo systemctl enable mcp-adhd-server"
print_status ""
print_success "Happy productivity! 🚀"