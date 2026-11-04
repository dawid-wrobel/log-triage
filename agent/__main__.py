import argparse, json
from .parser import parse_file
from .agent import triage

def main():
    ap = argparse.ArgumentParser(prog="agent")
    ap.add_argument("logfile")
    ap.add_argument("--out", default="data/triage.json")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    lines = parse_file(a.logfile)
    by_no = {l.no: l for l in lines}
    incidents = triage(lines, verbose=a.verbose)

    for i, inc in enumerate(incidents, 1):
        print(f"\n#{i} {inc['fault_class']} [{inc['subsystem']}]")
        print(f"   cause: {inc['root_cause']}")
        for n in inc["evidence_lines"]:
            print(f"   {by_no[n].fmt()}")
    json.dump(incidents, open(a.out, "w"), indent=2)
    print(f"\nZapisano: {a.out}")

if __name__ == "__main__":
    main()
