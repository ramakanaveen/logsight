"""Tests for the low-level sidecar HTTP call layer."""
import pytest
import respx
import httpx

from app.services.fanout import query_sidecar_raw

pytestmark = pytest.mark.anyio


async def test_query_sidecar_raw_success():
    payload = {"keywords": ["error"], "log_paths": ["/var/log/*.log"]}
    expected = {"results": [], "total_files_searched": 0}

    with respx.mock:
        respx.post("http://server1:9000/search").mock(
            return_value=httpx.Response(200, json=expected)
        )
        result = await query_sidecar_raw("server1", 9000, payload)

    assert result == expected


async def test_query_sidecar_raw_timeout():
    payload = {"keywords": ["error"], "log_paths": ["/var/log/*.log"]}

    with respx.mock:
        respx.post("http://server1:9000/search").mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        result = await query_sidecar_raw("server1", 9000, payload)

    assert "error" in result
    assert "Timeout" in result["error"]
    assert result["results"] == []


async def test_query_sidecar_raw_http_error():
    payload = {"keywords": ["error"], "log_paths": ["/var/log/*.log"]}

    with respx.mock:
        respx.post("http://server1:9000/search").mock(
            return_value=httpx.Response(500)
        )
        result = await query_sidecar_raw("server1", 9000, payload)

    assert "error" in result
    assert "500" in result["error"]


async def test_query_sidecar_raw_connection_refused():
    payload = {"keywords": ["error"], "log_paths": ["/var/log/*.log"]}

    with respx.mock:
        respx.post("http://server1:9000/search").mock(
            side_effect=ConnectionRefusedError("refused")
        )
        result = await query_sidecar_raw("server1", 9000, payload)

    assert "error" in result
    assert result["total_files_searched"] == 0
