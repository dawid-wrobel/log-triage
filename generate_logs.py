import argparse, json, random
from datetime import datetime, timedelta

INFO = [("calc-module", "Computation cycle {n} completed"),
        ("db-sync", "Synced {n} records"),
        ("hmi", "Operator view refreshed"),
        ("comm", "Heartbeat OK from PLC-0{p}")]

FAULTS = {
 "db_timeout": ("db-sync", [
   ("WARN", "Query slow: {ms} ms"),
   ("ERROR", "Connection to database timed out after 30s"),
   ("ERROR", "Retry 3/3 failed: database timeout")]),
 "invalid_input": ("hmi", [
   ("WARN", "Input 'setpoint' out of range: {v}"),
   ("ERROR", "Invalid input: setpoint rejected ({v})")]),
 "calc_exception": ("calc-module", [
   ("ERROR", "Unhandled exception in compute_flow: ZeroDivisionError"),
   ("ERROR", "Traceback: calc.py line 88 in compute_flow")]),
 "comm_loss": ("comm", [
   ("WARN", "Heartbeat missed from PLC-0{p}"),
   ("ERROR", "Communication lost with PLC-0{p} (no response 15s)"),
   ("ERROR", "Reconnect to PLC-0{p} failed")]),
 "config_error": ("calc-module", [
   ("ERROR", "Configuration error: missing key 'sampling_rate' in config.yaml"),
   ("WARN", "Falling back to defaults failed")]),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=300)
    ap.add_argument("--faults", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/logs.txt")
    ap.add_argument("--truth", default="data/truth.json")
    a = ap.parse_args()
    random.seed(a.seed)

    kinds = random.sample(list(FAULTS), min(a.faults, len(FAULTS)))
    pos = dict(zip(sorted(random.sample(range(a.lines), len(kinds))), kinds))
    t = datetime(2026, 10, 25, 8, 0, 0)
    out, truth = [], []

    def emit(level, sub, msg):
        nonlocal t
        t += timedelta(seconds=random.randint(1, 5))
        out.append(f"{t:%Y-%m-%d %H:%M:%S} {level} [{sub}] {msg}")

    for i in range(a.lines):
        if i in pos:
            kind = pos[i]
            sub, steps = FAULTS[kind]
            start = len(out) + 1
            for lvl, m in steps:
                emit(lvl, sub, m.format(ms=random.randint(2000, 9000),
                     v=random.choice(["-999", "1e9"]), p=random.randint(1, 3)))
            truth.append({"fault": kind, "subsystem": sub,
                          "lines": list(range(start, len(out) + 1))})
        else:
            sub, m = random.choice(INFO)
            emit("INFO", sub, m.format(n=random.randint(1, 999), p=random.randint(1, 3)))

    open(a.out, "w").write("\n".join(out) + "\n")
    json.dump(truth, open(a.truth, "w"), indent=2)

if __name__ == "__main__":
    main()
