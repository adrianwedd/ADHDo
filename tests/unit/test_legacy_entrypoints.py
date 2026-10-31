"""Boundary regressions for legacy source and dependency repairs."""
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.parametrize('name,path', [
    ('claude_only_endpoint', '/claude'), ('simple_claude_chat', '/claude_chat')])
def test_browser_endpoint_uses_provider_response(monkeypatch, name, path):
    module = importlib.import_module('mcp_server.' + name)
    send = AsyncMock(return_value='Take one small step.')
    monkeypatch.setattr(module, 'get_claude_browser', AsyncMock(
        return_value=SimpleNamespace(send_message=send)))
    app = FastAPI(); app.include_router(module.router)
    response = TestClient(app).post(path, json={'message': 'Help me start'})
    assert response.status_code == 200
    assert response.json()['response'] == 'Take one small step.'
    assert response.json()['success'] is True
    assert 'Help me start' in send.call_args.args[0]


@pytest.mark.parametrize('name,path', [
    ('claude_only_endpoint', '/claude'), ('simple_claude_chat', '/claude_chat')])
def test_browser_endpoint_does_not_fake_success(monkeypatch, name, path):
    module = importlib.import_module('mcp_server.' + name)
    monkeypatch.setattr(module, 'get_claude_browser', AsyncMock(side_effect=RuntimeError('offline')))
    app = FastAPI(); app.include_router(module.router)
    response = TestClient(app).post(path, json={'message': 'Hello'})
    assert response.status_code == 503
    assert response.json() == {'detail': 'Claude browser is unavailable'}


@pytest.mark.asyncio
async def test_context_session_commits_and_closes(monkeypatch):
    from mcp_server import database
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock())
    monkeypatch.setattr(database, 'SessionLocal', lambda: session)
    async with database.get_db_session() as current:
        assert current is session
    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_context_session_rolls_back_on_error(monkeypatch):
    from mcp_server import database
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock())
    monkeypatch.setattr(database, 'SessionLocal', lambda: session)
    with pytest.raises(RuntimeError):
        async with database.get_db_session():
            raise RuntimeError('operation failed')
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_uses_existing_service_lifecycle(monkeypatch):
    import mcp_server.main as main
    monkeypatch.setattr(main.settings, 'background_processing_enabled', False)
    monkeypatch.setattr(main.settings, 'cache_enabled', False)
    monkeypatch.setattr(main, 'should_enable_service', lambda _: False)
    monkeypatch.setattr(main, 'init_database', AsyncMock())
    monkeypatch.setattr(main, 'close_database', AsyncMock())
    monkeypatch.setattr(main.monitoring_system, 'initialize', AsyncMock())
    monkeypatch.setattr(main.monitoring_system, 'shutdown', AsyncMock())
    monkeypatch.setattr(main.alert_manager, 'start_monitoring', AsyncMock())
    monkeypatch.setattr(main.alert_manager, 'stop_monitoring', AsyncMock())
    async with main.lifespan(main.app):
        assert 'startup_metrics' in main.app.state._state
    main.init_database.assert_awaited_once()
    main.monitoring_system.shutdown.assert_awaited_once()
    main.alert_manager.stop_monitoring.assert_awaited_once()
    main.close_database.assert_awaited_once()


def test_health_endpoint_uses_real_health_interface(monkeypatch):
    from mcp_server.routers import health_routes
    monkeypatch.setattr(health_routes.health_monitor, 'get_overall_health',
                        AsyncMock(return_value={'status': 'healthy'}))
    app = FastAPI(); app.include_router(health_routes.health_router)
    response = TestClient(app).get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'


def test_metrics_and_alert_endpoints_accept_sync_services():
    from mcp_server.routers import health_routes
    app = FastAPI(); app.include_router(health_routes.health_router)
    client = TestClient(app)
    response = client.get('/metrics')
    assert response.status_code == 200 and 'mcp_adhd_server' in response.text
    assert client.get('/alerts').status_code == 200
