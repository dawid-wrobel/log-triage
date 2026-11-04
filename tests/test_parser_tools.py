from agent.parser import parse_text
from agent.tools import LogTools

LOG = """2026-10-25 08:00:01 INFO [hmi] Operator view refreshed
2026-10-25 08:00:03 WARN [comm] Heartbeat missed from PLC-01
2026-10-25 08:00:05 ERROR [comm] Communication lost with PLC-01 (no response 15s)
garbage line
2026-10-25 08:00:09 INFO [db-sync] Synced 5 records
"""

def test_parse_skips_garbage_and_keeps_numbers():
    lines = parse_text(LOG)
    assert [l.no for l in lines] == [1, 2, 3, 5]
    assert lines[2].level == "ERROR" and lines[2].subsystem == "comm"

def test_search_by_level():
    out = LogTools(parse_text(LOG)).search_logs(level="error")
    assert out.startswith("3:") and "Communication lost" in out

def test_get_context():
    out = LogTools(parse_text(LOG)).get_context(3, before=1, after=0)
    assert out.splitlines()[0].startswith("2:")

def test_count_by_subsystem():
    assert "comm: 2" in LogTools(parse_text(LOG)).count_by_subsystem()
