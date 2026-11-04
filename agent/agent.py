import json, os, re
from openai import OpenAI
from .tools import LogTools, TOOL_SCHEMAS

FAULT_CLASSES = ["db_timeout", "invalid_input", "calc_exception", "comm_loss", "config_error"]
MAX_STEPS = 12

SYSTEM = """You are a log triage agent for an industrial SCADA system.
Find ALL incidents in the log using the tools. Follow every step:
1. Call search_logs with level=ERROR, then again with level=WARN.
2. Group lines into clusters: lines from the same subsystem within a few seconds
   belong to one incident. WARN lines usually come right before the ERROR lines.
3. Call get_context for EVERY cluster (not just some of them).
4. Every ERROR line must belong to exactly one incident. Do not skip any cluster.
5. evidence_lines must include ALL WARN and ERROR lines of that incident.

Fault classes (use exactly these names):
- db_timeout: database connection timeouts / slow queries
- invalid_input: missing or invalid input data (e.g. setpoint out of range)
- calc_exception: unhandled exception / traceback in the calculation module
- comm_loss: lost communication with a PLC / device
- config_error: missing or wrong configuration

Rules:
- evidence_lines must be line numbers taken from tool output, never invented.
- One incident per fault.
- When done, answer with JSON only, no other text:
{"incidents": [{"fault_class": "...", "subsystem": "...", "root_cause": "one sentence", "evidence_lines": [1, 2]}]}
"""

def make_client():
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
    )

def extract_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

def validate(data, valid_lines):
    result = []
    for inc in (data or {}).get("incidents", []):
        if inc.get("fault_class") not in FAULT_CLASSES:
            continue
        ev = sorted({int(x) for x in inc.get("evidence_lines", [])
                     if str(x).isdigit() and int(x) in valid_lines})
        if not ev:
            continue
        result.append({
            "fault_class": inc["fault_class"],
            "subsystem": str(inc.get("subsystem", "")),
            "root_cause": str(inc.get("root_cause", "")),
            "evidence_lines": ev,
        })
    return result

def triage(lines, verbose=False):
    tools = LogTools(lines)
    valid = {l.no for l in lines}
    client = make_client()
    model = os.environ.get("LLM_MODEL", "qwen2.5:3b")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"The log has {len(lines)} lines. Find all incidents."},
    ]
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=TOOL_SCHEMAS, temperature=0)
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    if name not in ("search_logs", "get_context", "count_by_subsystem"):
                        raise ValueError(f"unknown tool {name}")
                    result = getattr(tools, name)(**args)
                except Exception as e:
                    result = f"tool error: {e}"
                if verbose:
                    print(f"[tool] {name}({tc.function.arguments}) -> {len(result)} chars")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue
        incidents = validate(extract_json(msg.content), valid)
        if incidents:
            return incidents
        messages.append({"role": "user",
                         "content": "Return ONLY the JSON object in the required format."})
    return []
