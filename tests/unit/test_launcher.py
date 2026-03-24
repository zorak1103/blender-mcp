"""Unit tests for launcher.py proxy logic."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


async def test_wait_for_blender_succeeds_on_200() -> None:
    """wait_for_blender returns without raising when the endpoint responds with 200."""
    import launcher

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("launcher.RETRY_TIMEOUT", 5.0), patch("launcher.RETRY_INTERVAL", 0.01):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await launcher.wait_for_blender()  # should not raise


async def test_wait_for_blender_raises_after_timeout() -> None:
    """wait_for_blender raises RuntimeError when Blender never becomes reachable."""
    import launcher

    with patch("launcher.RETRY_TIMEOUT", 0.05), patch("launcher.RETRY_INTERVAL", 0.01):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="not reachable"):
                await launcher.wait_for_blender()


async def test_proxy_request_success() -> None:
    """proxy_request returns raw response content on HTTP 200."""
    import launcher

    mock_response = MagicMock()
    mock_response.content = b'{"result": "ok"}'
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await launcher.proxy_request(mock_client, b'{"method":"tools/list","id":1}')
    assert result == b'{"result": "ok"}'


async def test_proxy_request_http_error_returns_error_json() -> None:
    """proxy_request returns a JSON error envelope on HTTP error status."""
    import launcher

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "500 Error", request=MagicMock(), response=mock_response
        )
    )

    result = await launcher.proxy_request(mock_client, b'{"method":"test","id":1}')
    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["error"]["code"] == 500


async def test_proxy_request_generic_error_returns_error_json() -> None:
    """proxy_request returns a JSON error envelope with code -32000 on unexpected errors."""
    import launcher

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=ConnectionResetError("connection lost"))

    result = await launcher.proxy_request(mock_client, b'{"method":"test","id":1}')
    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["error"]["code"] == -32000
