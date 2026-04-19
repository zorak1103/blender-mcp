"""Unit tests for launcher.py proxy logic."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

_AUTH = {"Authorization": "Bearer test-token"}


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
            await launcher.wait_for_blender(_AUTH)  # should not raise


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
                await launcher.wait_for_blender(_AUTH)


async def test_proxy_request_success() -> None:
    """proxy_request returns raw response content on HTTP 200."""
    import launcher

    mock_response = MagicMock()
    mock_response.content = b'{"result": "ok"}'
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await launcher.proxy_request(
        mock_client, b'{"method":"tools/list","id":1}', _AUTH
    )
    assert result == b'{"result": "ok"}'


async def test_proxy_request_sends_auth_header() -> None:
    """proxy_request includes the Authorization header in the POST request."""
    import launcher

    mock_response = MagicMock()
    mock_response.content = b'{"result": "ok"}'
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    await launcher.proxy_request(mock_client, b'{"id":1}', _AUTH)
    call_headers = mock_client.post.call_args.kwargs["headers"]
    assert call_headers.get("Authorization") == "Bearer test-token"


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

    result = await launcher.proxy_request(mock_client, b'{"method":"test","id":1}', _AUTH)
    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["error"]["code"] == 500


async def test_proxy_request_generic_error_returns_error_json() -> None:
    """proxy_request returns a JSON error envelope with code -32000 on unexpected errors."""
    import launcher

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=ConnectionResetError("connection lost"))

    result = await launcher.proxy_request(mock_client, b'{"method":"test","id":1}', _AUTH)
    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["error"]["code"] == -32000


async def test_main_reads_stdin_and_writes_stdout() -> None:
    """main() proxies one line from stdin to Blender and writes the response to stdout."""
    import io

    import launcher

    line = b'{"jsonrpc":"2.0","method":"tools/list","id":1}\n'
    response_bytes = b'{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}'

    stdin_buf = io.BytesIO(line + b"")  # one line then EOF on second read

    def fake_readline() -> bytes:
        return stdin_buf.read(len(line)) or b""

    stdout_buf = io.BytesIO()

    with patch("launcher.wait_for_blender", new=AsyncMock()):
        with patch("launcher.proxy_request", new=AsyncMock(return_value=response_bytes)):
            with patch("launcher._read_token", return_value="test-token"):
                with patch("sys.stdin", MagicMock(buffer=MagicMock(readline=fake_readline))):
                    with patch("sys.stdout", MagicMock(buffer=stdout_buf)):
                        await launcher.main()

    stdout_buf.seek(0)
    written = stdout_buf.read()
    assert response_bytes in written


def test_read_token_returns_none_when_file_missing(tmp_path: pathlib.Path) -> None:
    """_read_token returns None when the token file does not exist."""
    import launcher

    with patch("launcher._TOKEN_PATH", tmp_path / "nonexistent" / "token"):
        assert launcher._read_token() is None


def test_read_token_returns_content(tmp_path: pathlib.Path) -> None:
    """_read_token returns the token string when the file exists."""
    import launcher

    token_file = tmp_path / "token"
    token_file.write_text("abc123\n", encoding="ascii")

    with patch("launcher._TOKEN_PATH", token_file):
        assert launcher._read_token() == "abc123"
