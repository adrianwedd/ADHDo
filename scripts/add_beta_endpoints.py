#!/usr/bin/env python3
"""
Add beta onboarding endpoints to main.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def add_beta_endpoints():
    """Add beta endpoints to main.py"""
    
    main_py = Path(__file__).parent.parent / "src" / "mcp_server" / "main.py"
    
    # Read current content
    with open(main_py, 'r') as f:
        content = f.read()
    
    # Check if beta endpoints already exist
    if "beta_onboarding" in content:
        print("✅ Beta endpoints already exist in main.py")
        return
    
    # Add import
    import_line = "from mcp_server.beta_onboarding import beta_onboarding, QuickSetupRequest, BetaInvite"
    
    # Find the imports section
    lines = content.split('\n')
    
    # Find where to add the import (after other mcp_server imports)
    import_index = -1
    for i, line in enumerate(lines):
        if line.startswith("from mcp_server.onboarding"):
            import_index = i + 1
            break
    
    if import_index != -1:
        lines.insert(import_index, import_line)
    else:
        # Add after the last import
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                import_index = i + 1
        if import_index != -1:
            lines.insert(import_index, import_line)
    
    # Add beta endpoints before the last line
    beta_endpoints = '''

# === BETA ONBOARDING ENDPOINTS ===

@app.post("/api/beta/create-invite", tags=["Beta"])
async def create_beta_invite(
    expires_hours: int = 168,
    email: Optional[str] = None,
    name: Optional[str] = None
) -> dict:
    """Create a new beta tester invite."""
    invite = beta_onboarding.create_invite(expires_hours, email, name)
    
    setup_url = beta_onboarding.generate_setup_url(invite.invite_code)
    qr_code = beta_onboarding.generate_qr_code(invite.invite_code)
    
    return {
        "invite_code": invite.invite_code,
        "setup_url": setup_url,
        "qr_code": qr_code,
        "expires_at": invite.expires_at.isoformat(),
        "email": invite.email,
        "name": invite.name
    }


@app.get("/api/beta/invite/{invite_code}", tags=["Beta"])
async def get_beta_invite(invite_code: str) -> dict:
    """Get beta invite details."""
    invite = beta_onboarding.get_invite(invite_code)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    return {
        "invite_code": invite.invite_code,
        "name": invite.name,
        "email": invite.email,
        "expires_at": invite.expires_at.isoformat(),
        "is_valid": beta_onboarding.is_invite_valid(invite_code),
        "used_at": invite.used_at.isoformat() if invite.used_at else None
    }


@app.post("/api/beta/quick-setup", tags=["Beta"])
async def beta_quick_setup(setup_request: QuickSetupRequest) -> dict:
    """Complete automated beta user setup."""
    try:
        result = await beta_onboarding.quick_setup(setup_request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Beta quick setup failed", error=str(e))
        raise HTTPException(status_code=500, detail="Setup failed")


@app.get("/beta/setup", tags=["Beta"])
async def beta_setup_page(invite: str):
    """Serve the beta setup page."""
    # Validate invite
    if not beta_onboarding.is_invite_valid(invite):
        raise HTTPException(status_code=400, detail="Invalid or expired invite")
    
    invite_obj = beta_onboarding.get_invite(invite)
    
    # Return HTML setup page
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP ADHD Server - Beta Setup</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
        <div class="container mx-auto px-4 py-8 max-w-md">
            <div class="bg-white rounded-lg shadow-xl p-6">
                <div class="text-center mb-6">
                    <h1 class="text-2xl font-bold text-gray-900 mb-2">🧠⚡ Welcome Beta Tester!</h1>
                    <p class="text-gray-600">Let's set up your MCP ADHD Server</p>
                </div>
                
                <form id="setup-form">
                    <input type="hidden" name="invite_code" value="{invite}">
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Name</label>
                        <input type="text" name="name" required 
                               value="{invite_obj.name or ''}"
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
                        <input type="email" name="email" required 
                               value="{invite_obj.email or ''}"
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
                        <input type="password" name="password" required 
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <p class="text-xs text-gray-600 mt-1">8+ characters with letters and numbers</p>
                    </div>
                    
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Telegram Chat ID (Optional)
                        </label>
                        <input type="text" name="telegram_chat_id" 
                               class="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <p class="text-xs text-gray-600 mt-1">
                            For nudges! Message @userinfobot to get your ID
                        </p>
                    </div>
                    
                    <button type="submit" 
                            class="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 px-4 rounded-lg font-medium transition">
                        🚀 Set Up My ADHD Assistant
                    </button>
                </form>
                
                <div id="result" class="hidden mt-4"></div>
            </div>
        </div>
        
        <script>
            document.getElementById('setup-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                try {{
                    const response = await fetch('/api/beta/quick-setup', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(data)
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        document.getElementById('result').innerHTML = `
                            <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
                                <h3 class="font-bold">✅ Setup Complete!</h3>
                                <p class="mt-2">${{result.message}}</p>
                                <div class="mt-4">
                                    <a href="/" class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded">
                                        Start Using Your Assistant →
                                    </a>
                                </div>
                            </div>
                        `;
                        document.getElementById('setup-form').style.display = 'none';
                    }} else {{
                        throw new Error(result.detail || 'Setup failed');
                    }}
                    
                    document.getElementById('result').classList.remove('hidden');
                }} catch (error) {{
                    document.getElementById('result').innerHTML = `
                        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                            <h3 class="font-bold">❌ Setup Failed</h3>
                            <p class="mt-2">${{error.message}}</p>
                        </div>
                    `;
                    document.getElementById('result').classList.remove('hidden');
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")


@app.get("/api/beta/stats", tags=["Beta"])
async def get_beta_stats() -> dict:
    """Get beta program statistics."""
    return beta_onboarding.get_invite_stats()

# === END BETA ONBOARDING ENDPOINTS ===
'''
    
    # Insert before the last few lines
    lines.insert(-2, beta_endpoints)
    
    # Write back to file
    content = '\n'.join(lines)
    with open(main_py, 'w') as f:
        f.write(content)
    
    print("✅ Added beta endpoints to main.py")

if __name__ == "__main__":
    add_beta_endpoints()