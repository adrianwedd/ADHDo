#!/usr/bin/env python3
"""
ADHDo - Just Works™ Edition
Automatically detects your setup and starts with what you have.
No configuration needed - it figures it out.
"""

import os
import sys
import subprocess
import socket
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

# ANSI colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

class ADHDServerBootstrap:
    """Auto-configures and starts the ADHD server with zero hassle."""
    
    def __init__(self):
        self.config = {
            'has_redis': False,
            'redis_url': 'redis://localhost:6379/0',
            'has_ollama': False,
            'ollama_model': None,
            'has_postgres': False,
            'database_url': None,
            'openai_key': None,
            'port': 8000
        }
        self.env_file = Path('.env')
        self.venv_path = Path('venv_beta')
        
    def print_header(self):
        """Show startup banner."""
        print(f"\n{BOLD}🧠 ADHDo - ADHD Support Server{RESET}")
        print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print("Auto-detecting your environment...\n")
    
    def check_redis(self) -> bool:
        """Check if Redis is available."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            
            if result == 0:
                print(f"{GREEN}✓{RESET} Redis found on port 6379")
                self.config['has_redis'] = True
                return True
        except:
            pass
        
        print(f"{YELLOW}⚠{RESET}  Redis not found - using in-memory storage")
        return False
    
    def check_ollama(self) -> bool:
        """Check if Ollama is available with models."""
        try:
            result = subprocess.run(
                ['ollama', 'list'], 
                capture_output=True, 
                text=True, 
                timeout=3
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Has models
                    # Parse first model
                    model_line = lines[1].split()
                    if model_line:
                        model_name = model_line[0]
                        self.config['has_ollama'] = True
                        self.config['ollama_model'] = model_name
                        print(f"{GREEN}✓{RESET} Ollama found with model: {model_name}")
                        return True
        except:
            pass
        
        print(f"{YELLOW}⚠{RESET}  Ollama not found - using simple responses")
        return False
    
    def check_postgres(self) -> bool:
        """Check if PostgreSQL is available."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 5432))
            sock.close()
            
            if result == 0:
                print(f"{GREEN}✓{RESET} PostgreSQL found on port 5432")
                self.config['has_postgres'] = True
                self.config['database_url'] = 'postgresql://localhost/adhdo'
                return True
        except:
            pass
        
        # Fallback to SQLite
        print(f"{YELLOW}⚠{RESET}  PostgreSQL not found - using SQLite")
        self.config['database_url'] = 'sqlite:///./adhdo.db'
        return False
    
    def check_openai(self) -> bool:
        """Check for OpenAI API key in environment."""
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key and len(api_key) > 20:
            print(f"{GREEN}✓{RESET} OpenAI API key found")
            self.config['openai_key'] = api_key
            return True
        
        print(f"{YELLOW}⚠{RESET}  No OpenAI key - using local models only")
        return False
    
    def find_free_port(self, start_port: int = 8000) -> int:
        """Find an available port."""
        for port in range(start_port, start_port + 10):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('', port))
                sock.close()
                return port
            except:
                continue
        return start_port
    
    def create_minimal_env(self):
        """Create minimal .env file with auto-detected settings."""
        env_content = f"""# Auto-generated ADHDo configuration
# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}

# Core Settings
ENVIRONMENT=development
DEBUG=false
SECRET_KEY=adhd-local-dev-{os.urandom(8).hex()}

# Database
DATABASE_URL={self.config['database_url'] or 'sqlite:///./adhdo.db'}

# Redis Cache
REDIS_URL={self.config['redis_url'] if self.config['has_redis'] else ''}
ENABLE_REDIS={str(self.config['has_redis']).lower()}

# LLM Configuration
{'OLLAMA_MODEL=' + self.config['ollama_model'] if self.config['has_ollama'] else '# No Ollama found'}
{'OPENAI_API_KEY=' + self.config['openai_key'] if self.config['openai_key'] else '# No OpenAI key'}
USE_LOCAL_LLM={str(self.config['has_ollama']).lower()}

# Server
HOST=0.0.0.0
PORT={self.config['port']}

# ADHD Features - All enabled by default
ENABLE_COGNITIVE_LOAD_TRACKING=true
ENABLE_OVERWHELM_DETECTION=true
ENABLE_HYPERFOCUS_DETECTION=true
ENABLE_DOPAMINE_REWARDS=true
ENABLE_NUDGES=true

# Simplified Settings
MAX_RESPONSE_TIME_MS=3000
NUDGE_FREQUENCY_MINUTES=30
"""
        
        # Backup existing .env if it exists
        if self.env_file.exists():
            backup_path = Path(f'.env.backup.{int(time.time())}')
            self.env_file.rename(backup_path)
            print(f"{YELLOW}ℹ{RESET}  Backed up existing .env to {backup_path}")
        
        self.env_file.write_text(env_content)
        print(f"{GREEN}✓{RESET} Created .env configuration")
    
    def install_minimal_deps(self):
        """Install only essential dependencies."""
        print(f"\n{BLUE}Installing essential dependencies...{RESET}")
        
        essential_packages = [
            'fastapi',
            'uvicorn[standard]',
            'sqlalchemy',
            'aiosqlite',  # For async SQLite
            'python-dotenv',
            'pydantic',
            'pydantic-settings',
            'httpx',  # For API calls
            'structlog',
        ]
        
        if self.config['has_redis']:
            essential_packages.append('redis')
        
        if self.config['has_ollama']:
            essential_packages.append('ollama')  # Python client for Ollama
        
        # Use venv if it exists
        if self.venv_path.exists():
            pip_cmd = str(self.venv_path / 'bin' / 'pip')
            python_cmd = str(self.venv_path / 'bin' / 'python')
        else:
            pip_cmd = 'pip3'
            python_cmd = 'python3'
        
        # Install packages
        cmd = [pip_cmd, 'install', '-q'] + essential_packages
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"{GREEN}✓{RESET} Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"{YELLOW}⚠{RESET}  Some packages failed to install - continuing anyway")
    
    def create_simple_server(self):
        """Create the actual working server."""
        server_code = '''#!/usr/bin/env python3
"""
ADHDo Server - Minimal Working Version
Uses your actual environment with graceful fallbacks.
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import structlog

# Load environment
load_dotenv()

# Configure logging
logger = structlog.get_logger()

# Configuration from environment
class Config:
    redis_url = os.getenv('REDIS_URL', '')
    use_redis = os.getenv('ENABLE_REDIS', 'false').lower() == 'true'
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./adhdo.db')
    ollama_model = os.getenv('OLLAMA_MODEL', '')
    use_local_llm = os.getenv('USE_LOCAL_LLM', 'false').lower() == 'true'
    openai_key = os.getenv('OPENAI_API_KEY', '')
    port = int(os.getenv('PORT', 8000))
    
config = Config()

# Initialize storage
if config.use_redis:
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(config.redis_url)
        logger.info("Using Redis for storage")
    except:
        redis_client = None
        logger.info("Redis failed, using memory storage")
else:
    redis_client = None
    logger.info("Using in-memory storage")

# In-memory fallback
memory_store: Dict[str, Any] = {
    'sessions': {},
    'tasks': {},
    'patterns': {}
}

# Initialize LLM
llm_client = None
if config.use_local_llm and config.ollama_model:
    try:
        import ollama
        llm_client = ollama.Client()
        logger.info(f"Using Ollama with model: {config.ollama_model}")
    except:
        logger.warning("Ollama client failed to initialize")
elif config.openai_key:
    try:
        import openai
        openai.api_key = config.openai_key
        llm_client = openai
        logger.info("Using OpenAI API")
    except:
        logger.warning("OpenAI client failed to initialize")

# Create FastAPI app
app = FastAPI(
    title="ADHDo - ADHD Support Assistant",
    description="Personal ADHD support with privacy-first local processing",
    version="1.0.0"
)

# CORS for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    energy_level: Optional[str] = None
    task_breakdown: Optional[List[str]] = None

class Task(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due: Optional[datetime] = None
    priority: str = "medium"
    completed: bool = False
    steps: List[str] = []

# ADHD Support Logic
class ADHDSupport:
    """Core ADHD support functionality."""
    
    def __init__(self):
        self.crisis_keywords = [
            "suicide", "kill myself", "end it all", 
            "self harm", "hurt myself", "not worth living"
        ]
        
        self.adhd_patterns = {
            "can't start": self.handle_task_initiation,
            "overwhelmed": self.handle_overwhelm,
            "distracted": self.handle_distraction,
            "can't focus": self.handle_focus,
            "forgot": self.handle_memory,
            "time": self.handle_time_blindness,
            "procrastinat": self.handle_procrastination,
        }
    
    async def process_message(self, message: str, context: Dict) -> ChatResponse:
        """Process user message with ADHD support logic."""
        
        message_lower = message.lower()
        
        # Crisis detection
        if any(keyword in message_lower for keyword in self.crisis_keywords):
            return ChatResponse(
                response=(
                    "I'm very concerned about what you're sharing. Please reach out for help:\\n"
                    "• Crisis Line: 988 (US)\\n"
                    "• Text HOME to 741741\\n"
                    "• Emergency: 911\\n"
                    "You matter and there is support available."
                ),
                suggestions=["Talk to someone now", "Call a friend", "Contact therapist"]
            )
        
        # Check ADHD patterns
        for pattern, handler in self.adhd_patterns.items():
            if pattern in message_lower:
                return await handler(message, context)
        
        # Try LLM if available
        if llm_client:
            return await self.llm_response(message, context)
        
        # Fallback response
        return ChatResponse(
            response="I hear you. What specific challenge can I help you tackle right now?",
            suggestions=[
                "Break down a task",
                "Set a timer",
                "Make a simple plan"
            ]
        )
    
    async def handle_task_initiation(self, message: str, context: Dict) -> ChatResponse:
        return ChatResponse(
            response=(
                "Starting is often the hardest part. Let's make it tiny:\\n\\n"
                "1. What's the absolute smallest piece you could do?\\n"
                "2. Can you just open the document/app?\\n"
                "3. Set a 2-minute timer and do anything related to it\\n\\n"
                "Remember: Starting badly is better than not starting at all!"
            ),
            suggestions=["Set 2-min timer", "List first step", "Just open the file"],
            task_breakdown=["Open the document", "Write one sentence", "Save the file"]
        )
    
    async def handle_overwhelm(self, message: str, context: Dict) -> ChatResponse:
        return ChatResponse(
            response=(
                "Let's slow down and simplify:\\n\\n"
                "🫁 Take 3 deep breaths first\\n\\n"
                "Now, let's find ONE thing:\\n"
                "• What's the most urgent?\\n"
                "• What's the easiest?\\n"
                "• What would feel best to complete?\\n\\n"
                "Pick one. Ignore everything else for now."
            ),
            suggestions=["List everything out", "Pick the easiest", "Take a break first"],
            energy_level="low"
        )
    
    async def handle_distraction(self, message: str, context: Dict) -> ChatResponse:
        return ChatResponse(
            response=(
                "ADHD brains seek stimulation - it's not a character flaw!\\n\\n"
                "Try these:\\n"
                "• 🎵 Background music (lo-fi, brown noise)\\n"
                "• ⏰ Pomodoro: 15 min work, 5 min break\\n"
                "• 🎯 Make it a game: How much can you do in 10 min?\\n"
                "• 📝 Keep a 'distraction list' for later\\n\\n"
                "What usually helps you focus best?"
            ),
            suggestions=["Start timer", "Put on focus music", "Change location"]
        )
    
    async def handle_focus(self, message: str, context: Dict) -> ChatResponse:
        return self.handle_distraction(message, context)  # Similar approach
    
    async def handle_memory(self, message: str, context: Dict) -> ChatResponse:
        return ChatResponse(
            response=(
                "Working memory challenges are real! Let's externalize it:\\n\\n"
                "Right now:\\n"
                "• Write it down immediately\\n"
                "• Set a phone reminder\\n"
                "• Send yourself an email\\n"
                "• Take a photo as a memory cue\\n\\n"
                "For the future:\\n"
                "• Same place for keys/wallet/phone\\n"
                "• Calendar EVERYTHING\\n"
                "• Sticky notes in obvious places"
            ),
            suggestions=["Set reminder now", "Write it down", "Create a routine"]
        )
    
    async def handle_time_blindness(self, message: str, context: Dict) -> ChatResponse:
        current_time = datetime.now().strftime("%I:%M %p")
        return ChatResponse(
            response=(
                f"Current time: {current_time}\\n\\n"
                "Time check-in:\\n"
                "• How long did you think that took?\\n"
                "• Have you eaten recently?\\n"
                "• Water break needed?\\n"
                "• Should you transition to something else?\\n\\n"
                "Consider setting hourly alarms as time anchors."
            ),
            suggestions=["Set hourly alarm", "Schedule next break", "Review today's plan"]
        )
    
    async def handle_procrastination(self, message: str, context: Dict) -> ChatResponse:
        return ChatResponse(
            response=(
                "Procrastination often = perfectionism or overwhelm.\\n\\n"
                "Let's lower the bar:\\n"
                "• 'Good enough' > Perfect but never done\\n"
                "• What's the crappiest version you could do?\\n"
                "• Can you do just 10%?\\n\\n"
                "Sometimes our brain needs:\\n"
                "• More information (research for 10 min)\\n"
                "• More energy (take a walk)\\n"
                "• More dopamine (reward yourself after)\\n\\n"
                "What's really stopping you?"
            ),
            suggestions=["Do worst version", "Set tiny goal", "Plan reward"],
            task_breakdown=["Open document", "Write bad first line", "Keep going for 2 min"]
        )
    
    async def llm_response(self, message: str, context: Dict) -> ChatResponse:
        """Get response from LLM if available."""
        
        prompt = f"""You are an ADHD support assistant. Be concise, supportive, and practical.
        User message: {message}
        Context: {json.dumps(context) if context else 'None'}
        
        Provide a helpful response focused on ADHD challenges.
        Keep it under 100 words and actionable."""
        
        try:
            if config.use_local_llm and llm_client:
                # Ollama
                response = llm_client.chat(
                    model=config.ollama_model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                text = response['message']['content']
            elif llm_client:
                # OpenAI
                response = llm_client.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=150
                )
                text = response.choices[0].message.content
            else:
                text = "I want to help. Can you tell me more about what you're struggling with?"
                
            return ChatResponse(response=text)
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return ChatResponse(
                response="Let me help you with that. What's the specific challenge?",
                suggestions=["Break it down", "Set a timer", "Take a break"]
            )

# Initialize support system
adhd_support = ADHDSupport()

# API Endpoints
@app.get("/")
async def root():
    """Serve simple web interface."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ADHDo - ADHD Support</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #4a90e2; }
            .chat-container {
                background: white;
                border-radius: 10px;
                padding: 20px;
                height: 400px;
                overflow-y: auto;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .message {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .user { background: #e3f2fd; text-align: right; }
            .assistant { background: #f5f5f5; }
            .input-container {
                display: flex;
                gap: 10px;
            }
            input {
                flex: 1;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                padding: 12px 24px;
                background: #4a90e2;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover { background: #357abd; }
            .suggestions {
                display: flex;
                gap: 10px;
                margin-top: 10px;
                flex-wrap: wrap;
            }
            .suggestion {
                padding: 8px 12px;
                background: #fff3cd;
                border-radius: 20px;
                cursor: pointer;
                font-size: 14px;
            }
            .suggestion:hover { background: #ffe69c; }
        </style>
    </head>
    <body>
        <h1>🧠 ADHDo Support</h1>
        <div class="chat-container" id="chat"></div>
        <div class="input-container">
            <input type="text" id="message" placeholder="What are you struggling with?" 
                   onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
        <div class="suggestions" id="suggestions"></div>
        
        <script>
            async function sendMessage() {
                const input = document.getElementById('message');
                const message = input.value.trim();
                if (!message) return;
                
                // Add user message to chat
                const chat = document.getElementById('chat');
                chat.innerHTML += `<div class="message user">${message}</div>`;
                input.value = '';
                
                // Send to API
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: message})
                    });
                    
                    const data = await response.json();
                    
                    // Add response to chat
                    chat.innerHTML += `<div class="message assistant">${data.response.replace(/\\n/g, '<br>')}</div>`;
                    
                    // Show suggestions
                    const sugg = document.getElementById('suggestions');
                    sugg.innerHTML = '';
                    if (data.suggestions) {
                        data.suggestions.forEach(s => {
                            sugg.innerHTML += `<span class="suggestion" onclick="quickSend('${s}')">${s}</span>`;
                        });
                    }
                    
                    // Scroll to bottom
                    chat.scrollTop = chat.scrollHeight;
                    
                } catch (err) {
                    chat.innerHTML += `<div class="message assistant">Sorry, something went wrong. Try again?</div>`;
                }
            }
            
            function quickSend(text) {
                document.getElementById('message').value = text;
                sendMessage();
            }
            
            // Focus input on load
            document.getElementById('message').focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "storage": "redis" if redis_client else "memory",
        "llm": config.ollama_model or "pattern-based"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint."""
    try:
        # Store in session
        session_key = f"session:{request.user_id}"
        
        if redis_client:
            await redis_client.lpush(session_key, request.message)
            await redis_client.expire(session_key, 3600)  # 1 hour expiry
        else:
            if request.user_id not in memory_store['sessions']:
                memory_store['sessions'][request.user_id] = []
            memory_store['sessions'][request.user_id].append({
                'message': request.message,
                'timestamp': datetime.now().isoformat()
            })
        
        # Process message
        response = await adhd_support.process_message(request.message, request.context or {})
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            response="I'm having trouble right now. Can you try rephrasing that?",
            suggestions=["Try again", "Simplify the question"]
        )

@app.post("/task", response_model=Task)
async def create_task(task: Task):
    """Create a task with ADHD-friendly breakdown."""
    
    # Auto-generate ID
    task.id = f"task_{int(time.time())}"
    
    # Break down if no steps provided
    if not task.steps:
        task.steps = [
            f"Open anything related to '{task.title}'",
            "Work for just 2 minutes",
            "Save your progress",
            "Celebrate that you started!"
        ]
    
    # Store task
    if redis_client:
        await redis_client.hset(f"tasks:{task.id}", mapping=task.dict())
    else:
        memory_store['tasks'][task.id] = task.dict()
    
    return task

@app.get("/tasks")
async def get_tasks(user_id: str = "default_user"):
    """Get all tasks."""
    tasks = []
    
    if redis_client:
        # Get from Redis
        keys = await redis_client.keys("tasks:*")
        for key in keys:
            task_data = await redis_client.hgetall(key)
            if task_data:
                tasks.append(task_data)
    else:
        tasks = list(memory_store['tasks'].values())
    
    return tasks

@app.post("/nudge")
async def send_nudge(user_id: str = "default_user", message: Optional[str] = None):
    """Send a gentle nudge."""
    
    default_nudges = [
        "Hey! Just checking in. How's it going?",
        "Perfect time for a 2-minute task sprint!",
        "Water break? Stretch? Both? 💧",
        "What's one tiny thing you could do right now?",
        "You're doing better than you think! 🌟"
    ]
    
    import random
    nudge = message or random.choice(default_nudges)
    
    return {"nudge": nudge, "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    
    print("\\n🚀 Starting ADHDo Server...")
    print(f"📍 Open http://localhost:{config.port} in your browser")
    print("\\n✨ Features enabled:")
    print(f"  • Storage: {'Redis' if config.use_redis else 'In-memory'}")
    print(f"  • LLM: {config.ollama_model or config.openai_key[:8]+'...' if config.openai_key else 'Pattern-based'}")
    print(f"  • Database: {config.database_url.split('://')[0]}")
    print("\\n💡 Tips:")
    print("  • Be specific about what you're struggling with")
    print("  • Use the quick suggestions for common issues")
    print("  • Tasks are automatically broken down into small steps")
    print("\\nPress Ctrl+C to stop\\n")
    
    uvicorn.run(app, host="0.0.0.0", port=config.port)
'''
        
        # Write the server file
        server_file = Path('adhdo_server.py')
        server_file.write_text(server_code)
        server_file.chmod(0o755)
        print(f"{GREEN}✓{RESET} Created adhdo_server.py")
    
    def create_launcher(self):
        """Create one-line launcher script."""
        launcher = '''#!/bin/bash
# ADHDo Quick Start - Just run this!

echo "🧠 Starting ADHDo..."

# Use venv if it exists
if [ -d "venv_beta" ]; then
    ./venv_beta/bin/python adhdo_server.py
elif [ -d "venv" ]; then
    ./venv/bin/python adhdo_server.py
else
    python3 adhdo_server.py
fi
'''
        
        launcher_file = Path('start.sh')
        launcher_file.write_text(launcher)
        launcher_file.chmod(0o755)
        print(f"{GREEN}✓{RESET} Created start.sh launcher")
    
    def run(self):
        """Run the complete setup."""
        self.print_header()
        
        # Check environment
        self.check_redis()
        self.check_ollama()
        self.check_postgres()
        self.check_openai()
        
        # Find available port
        self.config['port'] = self.find_free_port()
        print(f"{GREEN}✓{RESET} Port {self.config['port']} is available")
        
        # Create configuration
        print(f"\n{BLUE}Setting up configuration...{RESET}")
        self.create_minimal_env()
        self.install_minimal_deps()
        
        # Create server
        print(f"\n{BLUE}Creating server...{RESET}")
        self.create_simple_server()
        self.create_launcher()
        
        # Done!
        print(f"\n{GREEN}{'='*50}{RESET}")
        print(f"{BOLD}✅ ADHDo is ready!{RESET}")
        print(f"{GREEN}{'='*50}{RESET}")
        print(f"\nTo start the server, run:")
        print(f"  {BOLD}./start.sh{RESET}")
        print(f"\nOr directly:")
        print(f"  {BOLD}python3 adhdo_server.py{RESET}")
        print(f"\nThen open: {BOLD}http://localhost:{self.config['port']}{RESET}")
        
        # Offer to start now
        print(f"\n{YELLOW}Start the server now? (y/n):{RESET} ", end='')
        if input().lower() == 'y':
            print(f"\n{GREEN}Starting server...{RESET}\n")
            os.system('./start.sh')

if __name__ == "__main__":
    bootstrap = ADHDServerBootstrap()
    bootstrap.run()