"""Low-level sidecar HTTP calls used by the agentic loop."""
import httpx
from typing import Any


async def query_sidecar_raw(host: str, port: int, payload: dict[str, Any]) -> dict[str, Any]:
    """POST payload directly to sidecar /search and return the parsed JSON or an error dict."""
    url = f"http://{host}:{port}/search"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        return {"error": f"Timeout connecting to {host}:{port}", "results": [], "total_files_searched": 0}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code} from {host}:{port}", "results": [], "total_files_searched": 0}
    except Exception as e:
        return {"error": str(e), "results": [], "total_files_searched": 0}
