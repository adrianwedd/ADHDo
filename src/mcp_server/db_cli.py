#!/usr/bin/env python3
"""
Database CLI utilities for MCP ADHD Server.

Provides commands for database management, migrations, and maintenance.
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mcp_server import __version__
from mcp_server.config import settings
from mcp_server.database import init_database, get_database_session, close_database
from mcp_server.db_service import DatabaseService

app = typer.Typer(
    name="mcp-db",
    help="Database management utilities for MCP ADHD Server",
    add_completion=False
)
console = Console()


@app.command()
def version():
    """Show version information."""
    console.print(f"MCP ADHD Server Database CLI v{__version__}")


@app.command()
def status():
    """Check database connection status."""
    async def _check_status():
        console.print("🔍 Checking database status...")
        
        try:
            await init_database()
            console.print("✅ Database connection successful", style="green")
            console.print(f"   URL: {settings.database_url}")
            
            async with get_database_session() as session:
                db_service = DatabaseService(session)
                system_status = await db_service.get_system_status()
                
                # Create status table
                table = Table(title="System Health Status")
                table.add_column("Component", style="cyan")
                table.add_column("Status", style="magenta")
                table.add_column("Last Check", style="dim")
                table.add_column("Response Time", style="yellow")
                
                for component, status_info in system_status.items():
                    status_color = {
                        'healthy': 'green',
                        'degraded': 'yellow', 
                        'unhealthy': 'red',
                        'unknown': 'dim'
                    }.get(status_info['status'], 'white')
                    
                    table.add_row(
                        component.title(),
                        f"[{status_color}]{status_info['status'].upper()}[/{status_color}]",
                        str(status_info.get('last_check', 'Never'))[:19] if status_info.get('last_check') else 'Never',
                        f"{status_info.get('response_time_ms', 0):.1f}ms" if status_info.get('response_time_ms') else 'N/A'
                    )
                
                console.print(table)
                
            await close_database()
            
        except Exception as e:
            console.print(f"❌ Database connection failed: {e}", style="red")
            return False
        
        return True
    
    return asyncio.run(_check_status())


@app.command()
def migrate(
    revision: Optional[str] = typer.Argument(None, help="Target revision (default: head)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show SQL without executing")
):
    """Run database migrations."""
    import subprocess
    
    target = revision or "head"
    
    try:
        if dry_run:
            console.print(f"🔍 Showing migration SQL for {target}...")
            cmd = ["alembic", "upgrade", target, "--sql"]
        else:
            console.print(f"🚀 Running migrations to {target}...")
            cmd = ["alembic", "upgrade", target]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("✅ Migration completed successfully", style="green")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print("❌ Migration failed", style="red")
            if result.stderr:
                console.print(result.stderr, style="red")
            raise typer.Exit(1)
            
    except FileNotFoundError:
        console.print("❌ Alembic not found. Install with: pip install alembic", style="red")
        raise typer.Exit(1)


@app.command()
def rollback(
    revision: str = typer.Argument(..., help="Target revision to rollback to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show SQL without executing")
):
    """Rollback database to previous revision."""
    import subprocess
    
    try:
        if dry_run:
            console.print(f"🔍 Showing rollback SQL to {revision}...")
            cmd = ["alembic", "downgrade", revision, "--sql"]
        else:
            console.print(f"⏪ Rolling back to {revision}...")
            cmd = ["alembic", "downgrade", revision]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("✅ Rollback completed successfully", style="green")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print("❌ Rollback failed", style="red")
            if result.stderr:
                console.print(result.stderr, style="red")
            raise typer.Exit(1)
            
    except FileNotFoundError:
        console.print("❌ Alembic not found. Install with: pip install alembic", style="red")
        raise typer.Exit(1)


@app.command()
def create_user(
    name: str = typer.Argument(..., help="User name"),
    email: Optional[str] = typer.Option(None, "--email", help="User email"),
    telegram_id: Optional[str] = typer.Option(None, "--telegram", help="Telegram chat ID"),
    admin: bool = typer.Option(False, "--admin", help="Make user admin")
):
    """Create a new user."""
    async def _create_user():
        try:
            await init_database()
            
            async with get_database_session() as session:
                db_service = DatabaseService(session)
                
                user = await db_service.create_user(
                    name=name,
                    email=email,
                    telegram_chat_id=telegram_id,
                    is_admin=admin
                )
                
                console.print("✅ User created successfully", style="green")
                console.print(f"   ID: {user.user_id}")
                console.print(f"   Name: {user.name}")
                console.print(f"   Email: {user.email or 'Not set'}")
                console.print(f"   Telegram: {user.telegram_chat_id or 'Not set'}")
                console.print(f"   Admin: {'Yes' if user.is_admin else 'No'}")
                
                await session.commit()
                
            await close_database()
            
        except Exception as e:
            console.print(f"❌ Failed to create user: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(_create_user())


@app.command()
def list_users(
    limit: int = typer.Option(10, "--limit", help="Number of users to show")
):
    """List users in the database."""
    async def _list_users():
        try:
            await init_database()
            
            async with get_database_session() as session:
                # Simple query to list users
                from sqlalchemy import select
                from mcp_server.db_models import User as DBUser
                
                result = await session.execute(
                    select(DBUser)
                    .where(DBUser.is_active == True)
                    .order_by(DBUser.created_at.desc())
                    .limit(limit)
                )
                users = result.scalars().all()
                
                if not users:
                    console.print("No users found", style="yellow")
                    return
                
                # Create users table
                table = Table(title=f"Users (showing {len(users)} of max {limit})")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Email", style="blue")
                table.add_column("Telegram", style="green")
                table.add_column("Admin", style="red")
                table.add_column("Created", style="dim")
                
                for user in users:
                    table.add_row(
                        user.user_id[:8] + "...",
                        user.name,
                        user.email or "-",
                        user.telegram_chat_id or "-",
                        "Yes" if user.is_admin else "No",
                        str(user.created_at)[:19]
                    )
                
                console.print(table)
                
            await close_database()
            
        except Exception as e:
            console.print(f"❌ Failed to list users: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(_list_users())


@app.command()
def cleanup(
    days: int = typer.Option(90, "--days", help="Days of data to keep"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleaned without doing it")
):
    """Clean up old traces and health records."""
    async def _cleanup():
        try:
            await init_database()
            
            async with get_database_session() as session:
                db_service = DatabaseService(session)
                
                if dry_run:
                    console.print(f"🔍 Would clean up data older than {days} days")
                else:
                    console.print(f"🧹 Cleaning up data older than {days} days...")
                    
                    # Clean up old traces
                    trace_count = await db_service.traces.cleanup_old_traces(days)
                    console.print(f"   Cleaned {trace_count} old trace records")
                    
                    # Clean up old health records
                    health_count = await db_service.health.cleanup_old_health_records(days)
                    console.print(f"   Cleaned {health_count} old health records")
                    
                    # Clean up expired sessions
                    session_count = await db_service.sessions.cleanup_expired_sessions()
                    console.print(f"   Cleaned {session_count} expired sessions")
                    
                    console.print("✅ Cleanup completed", style="green")
                    await session.commit()
                
            await close_database()
            
        except Exception as e:
            console.print(f"❌ Cleanup failed: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(_cleanup())


@app.command()
def test_connection():
    """Test database connection and basic operations."""
    async def _test():
        console.print("🧪 Testing database connection and operations...")
        
        try:
            # Import and run the test
            from test_database import test_database_integration
            await test_database_integration()
            
        except Exception as e:
            console.print(f"❌ Test failed: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(_test())


@app.command()
def init_schema():
    """Initialize database schema (create tables)."""
    async def _init():
        try:
            await init_database()
            
            # Import all models to ensure they're registered
            from mcp_server.db_models import (
                User, Task, TraceMemory, Session, APIKey, SystemHealth
            )
            from mcp_server.database import engine, Base
            
            console.print("🏗️ Creating database schema...")
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            console.print("✅ Database schema created successfully", style="green")
            await close_database()
            
        except Exception as e:
            console.print(f"❌ Schema initialization failed: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(_init())


if __name__ == "__main__":
    app()