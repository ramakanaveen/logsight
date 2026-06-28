import asyncio
import httpx
from typing import Any


async def query_sidecar(
    client: httpx.AsyncClient,
    host: str,
    port: int,
    keywords: list[str],
    log_paths: list[str],
    time_window_minutes: int = 60,
    max_lines: int = 50,
) -> dict[str, Any]:
    url = f"http://{host}:{port}/search"
    payload = {
        "keywords": keywords,
        "log_paths": log_paths,
        "time_window_minutes": time_window_minutes,
        "max_lines": max_lines,
    }
    try:
        resp = await client.post(url, json=payload, timeout=10.0)
        resp.raise_for_status()
        return {"ok": True, "data": resp.json(), "host": host, "port": port}
    except httpx.TimeoutException:
        return {"ok": False, "error": f"Timeout connecting to {host}:{port}", "host": host, "port": port}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "error": f"HTTP {e.response.status_code} from {host}:{port}", "host": host, "port": port}
    except Exception as e:
        return {"ok": False, "error": str(e), "host": host, "port": port}


async def fanout_search(
    targets: list[dict[str, Any]],
    keywords: list[str],
) -> list[dict[str, Any]]:
    """targets: list of {host, port, log_paths, process_name}"""
    async with httpx.AsyncClient() as client:
        tasks = [
            query_sidecar(
                client,
                t["host"],
                t["port"],
                keywords,
                t["log_paths"],
            )
            for t in targets
        ]
        results = await asyncio.gather(*tasks)

    # Attach process names
    for result, target in zip(results, targets):
        result["process_name"] = target.get("process_name", "unknown")

    return list(results)
