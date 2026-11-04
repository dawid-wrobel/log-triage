import re
from dataclasses import dataclass

LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (INFO|WARN|ERROR) \[([\w-]+)\] (.*)$"
)

@dataclass
class LogLine:
    no: int
    ts: str
    level: str
    subsystem: str
    msg: str

    def fmt(self) -> str:
        return f"{self.no}: {self.ts} {self.level} [{self.subsystem}] {self.msg}"

def parse_text(text: str) -> list[LogLine]:
    lines = []
    for i, raw in enumerate(text.splitlines(), 1):
        m = LINE_RE.match(raw)
        if m:
            lines.append(LogLine(i, *m.groups()))
    return lines

def parse_file(path: str) -> list[LogLine]:
    with open(path, encoding="utf-8") as f:
        return parse_text(f.read())
