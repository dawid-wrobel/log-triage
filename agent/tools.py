from collections import Counter
from datetime import datetime

class LogTools:
    def __init__(self, lines):
        self.lines = lines

    def search_logs(self, level=None, subsystem=None, keyword=None, limit=20):
        limit = min(int(limit), 40)
        res = [
            l for l in self.lines
            if (not level or l.level == str(level).upper())
            and (not subsystem or l.subsystem == subsystem)
            and (not keyword or str(keyword).lower() in l.msg.lower())
        ]
        out = "\n".join(l.fmt() for l in res[:limit])
        if len(res) > limit:
            out += f"\n... {len(res) - limit} more matches, narrow the filters"
        return out or "no results"

    def get_context(self, line_no, before=3, after=3):
        line_no, before, after = int(line_no), min(int(before), 10), min(int(after), 10)
        sel = [l for l in self.lines if line_no - before <= l.no <= line_no + after]
        return "\n".join(l.fmt() for l in sel) or "no results"

    def count_by_subsystem(self, level=None):
        c = Counter(
            l.subsystem for l in self.lines
            if not level or l.level == str(level).upper()
        )
        return ", ".join(f"{k}: {v}" for k, v in c.most_common()) or "no results"

    def find_incident_clusters(self, gap_seconds=10):
        gap = int(gap_seconds)
        fmt = "%Y-%m-%d %H:%M:%S"
        clusters = []
        for l in self.lines:
            if l.level == "INFO":
                continue
            t = datetime.strptime(l.ts, fmt)
            c = clusters[-1] if clusters else None
            if c and c["sub"] == l.subsystem and (t - c["last"]).total_seconds() <= gap:
                c["lines"].append(l)
                c["last"] = t
            else:
                clusters.append({"sub": l.subsystem, "last": t, "lines": [l]})
        out = []
        for i, c in enumerate(clusters, 1):
            out.append(f"Cluster {i} [{c['sub']}]:")
            out.extend("  " + l.fmt() for l in c["lines"])
        return "\n".join(out[:120]) or "no results"

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_logs",
        "description": "Search log lines. Returns lines prefixed with their line number.",
        "parameters": {"type": "object", "properties": {
            "level": {"type": "string", "enum": ["INFO", "WARN", "ERROR"]},
            "subsystem": {"type": "string"},
            "keyword": {"type": "string"},
            "limit": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "get_context",
        "description": "Get log lines around a given line number.",
        "parameters": {"type": "object", "properties": {
            "line_no": {"type": "integer"},
            "before": {"type": "integer"},
            "after": {"type": "integer"}},
            "required": ["line_no"]}}},
    {"type": "function", "function": {
        "name": "count_by_subsystem",
        "description": "Count log lines per subsystem, optionally for one level.",
        "parameters": {"type": "object", "properties": {
            "level": {"type": "string", "enum": ["INFO", "WARN", "ERROR"]}}}}},
    {"type": "function", "function": {
        "name": "find_incident_clusters",
        "description": "Group all WARN and ERROR lines into incident clusters (same subsystem, close in time). Call this first.",
        "parameters": {"type": "object", "properties": {
            "gap_seconds": {"type": "integer"}}}}},
]
