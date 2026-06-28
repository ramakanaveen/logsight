import json
from typing import Any
import anthropic
from app.config import settings

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def identify_processes(question: str, processes: list[dict[str, Any]]) -> dict[str, Any]:
    """LLM call 1: determine which processes are relevant and what keywords to search."""
    process_list = json.dumps(
        [{"id": str(p["id"]), "name": p["name"], "description": p["description"], "example_qa": p.get("example_qa", [])}
         for p in processes],
        indent=2,
    )

    prompt = f"""You are a routing agent for a log intelligence system at a trading firm.

Available processes:
{process_list}

Trader question: "{question}"

Return a JSON object with:
- "relevant_process_ids": list of process IDs that likely have relevant logs (can be empty if none apply)
- "keywords": list of 3-8 search keywords to grep in log files

Return ONLY valid JSON, no markdown.
"""

    client = get_client()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    return json.loads(text)


def summarize_results(question: str, sidecar_results: list[dict[str, Any]]) -> str:
    """LLM call 2: synthesize log snippets into a plain-English answer."""
    log_data = []
    for r in sidecar_results:
        if not r.get("ok"):
            log_data.append(f"[{r['process_name']} @ {r['host']}] UNREACHABLE: {r.get('error', 'unknown error')}")
            continue
        data = r.get("data", {})
        for file_result in data.get("results", []):
            if file_result.get("error"):
                log_data.append(f"[{r['process_name']} @ {r['host']}] {file_result['path']}: ERROR {file_result['error']}")
                continue
            lines = file_result.get("matched_lines", [])
            if lines:
                snippets = "\n".join(f"  L{l['line_number']}: {l['content']}" for l in lines[:20])
                log_data.append(
                    f"[{r['process_name']} @ {r['host']}] {file_result['path']} "
                    f"({file_result['total_matched']} matches):\n{snippets}"
                )

    if not log_data:
        context = "No matching log entries were found across any searched machines."
    else:
        context = "\n\n".join(log_data)

    prompt = f"""You are a log intelligence assistant for a trading firm.

Trader question: "{question}"

Log evidence gathered from machines:
{context}

Give a concise, plain-English answer to the trader's question based on this evidence.
Be specific about times, machines, and statuses when the data supports it.
If no relevant logs were found, say so clearly.
"""

    client = get_client()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return msg.content[0].text.strip()
