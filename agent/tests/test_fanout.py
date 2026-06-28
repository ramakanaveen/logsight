import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.fanout import query_sidecar, fanout_search


pytestmark = pytest.mark.anyio


async def test_query_sidecar_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [], "total_files_searched": 0}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await query_sidecar(mock_client, "server1", 9000, ["error"], ["/var/log/*.log"])

    assert result["ok"] is True
    assert result["host"] == "server1"
    assert result["port"] == 9000
    assert "data" in result


async def test_query_sidecar_timeout():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    result = await query_sidecar(mock_client, "server1", 9000, ["error"], ["/var/log/*.log"])

    assert result["ok"] is False
    assert "Timeout" in result["error"]
    assert result["host"] == "server1"


async def test_query_sidecar_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response)
    )

    result = await query_sidecar(mock_client, "server1", 9000, ["error"], ["/var/log/*.log"])

    assert result["ok"] is False
    assert "500" in result["error"]


async def test_query_sidecar_generic_exception():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=ConnectionRefusedError("refused"))

    result = await query_sidecar(mock_client, "server1", 9000, ["error"], ["/var/log/*.log"])

    assert result["ok"] is False
    assert result["error"] is not None


async def test_fanout_search_attaches_process_names():
    targets = [
        {"host": "h1", "port": 9000, "log_paths": ["/a.log"], "process_name": "ProcA"},
        {"host": "h2", "port": 9000, "log_paths": ["/b.log"], "process_name": "ProcB"},
    ]

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [], "total_files_searched": 0}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.fanout.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        results = await fanout_search(targets, ["error"])

    assert len(results) == 2
    assert results[0]["process_name"] == "ProcA"
    assert results[1]["process_name"] == "ProcB"


async def test_fanout_search_runs_in_parallel():
    """All sidecar calls are issued even when one fails."""
    targets = [
        {"host": "ok-host", "port": 9000, "log_paths": ["/a.log"], "process_name": "A"},
        {"host": "bad-host", "port": 9000, "log_paths": ["/b.log"], "process_name": "B"},
    ]

    async def fake_post(url, **kwargs):
        if "bad-host" in url:
            raise httpx.TimeoutException("timeout")
        mock = MagicMock()
        mock.json.return_value = {"results": [], "total_files_searched": 1}
        mock.raise_for_status = MagicMock()
        return mock

    with patch("app.services.fanout.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = fake_post
        mock_cls.return_value = mock_client

        results = await fanout_search(targets, ["error"])

    assert len(results) == 2
    ok = next(r for r in results if r["host"] == "ok-host")
    bad = next(r for r in results if r["host"] == "bad-host")
    assert ok["ok"] is True
    assert bad["ok"] is False
