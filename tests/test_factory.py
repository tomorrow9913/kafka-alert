import pytest
from unittest.mock import AsyncMock, MagicMock
from core.factory import AlertFactory

@pytest.mark.asyncio
async def test_process_success(factory_reset, mocker):
    # Setup
    factory = AlertFactory()
    
    # Mock renderer to return a dict
    factory.renderer = MagicMock()
    factory.renderer.render.return_value = {"content": "test message"}
    
    # Mock provider
    mock_discord = AsyncMock()
    mock_discord.send.return_value = True
    factory.providers["discord"] = mock_discord
    
    payload = {
        "provider": "discord",
        "template": "test_template",
        "destination": "http://webhook",
        "data": {"foo": "bar"}
    }
    
    # Execute
    await factory.process(payload)
    
    # Verify
    factory.renderer.render.assert_called_once()
    mock_discord.send.assert_called_once_with("http://webhook", {"content": "test message"})

@pytest.mark.asyncio
async def test_process_fallback(factory_reset, mocker):
    # Setup
    factory = AlertFactory()
    
    # Mock renderer to raise exception
    factory.renderer = MagicMock()
    factory.renderer.render.side_effect = Exception("Rendering failed")
    
    # Mock provider
    mock_discord = AsyncMock()
    factory.providers["discord"] = mock_discord
    
    payload = {
        "provider": "discord",
        "template": "test_template",
        "destination": "http://webhook",
        "data": {"foo": "bar"}
    }
    
    # Execute
    await factory.process(payload)
    
    # Verify
    # Should call send with fallback message
    assert mock_discord.send.call_count == 1
    call_args = mock_discord.send.call_args
    assert call_args[0][0] == "http://webhook"
    assert "Alert Rendering Failed" in call_args[0][1]["content"]

@pytest.mark.asyncio
async def test_process_invalid_provider(factory_reset):
    factory = AlertFactory()
    factory.renderer = MagicMock()
    
    payload = {
        "provider": "unknown",
        "template": "test",
        "data": {}
    }
    
    # Execute (should just log error and return, no exception)
    await factory.process(payload)
    
    # Verify renderer not called
    factory.renderer.render.assert_not_called()
