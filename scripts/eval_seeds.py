"""Evaluate the agent on several generated logs and print mean metrics."""
import argparse, json, subprocess, sys, tempfile

from agent.parser import parse_file
from agent.agent import triage
from agent.evaluate import score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--lines", type=int, default=300)
    a = ap.parse_args()

    rows = []
    with tempfile.TemporaryDirectory() as d:
        for i, s in enumerate(a.seeds):
            logs, truth = f"{d}/logs_{s}.txt", f"{d}/truth_{s}.json"
            subprocess.run(
                [sys.executable, "generate_logs.py", "--seed", str(s),
                 "--lines", str(a.lines), "--out", logs, "--truth", truth],
                check=True)
            if i == 0:  # warm-up run on the first log, result discarded
                triage(parse_file(logs))
            sc = score(json.load(open(truth)), triage(parse_file(logs)))
            rows.append(sc)
            print(f"seed {s}: class_accuracy={sc['class_accuracy']:.2f} "
                  f"evidence_recall={sc['evidence_recall']:.2f} "
                  f"false_positives={sc['false_positives']}")

    n = len(rows)
    print(f"MEAN ({n} seeds): "
          f"class_accuracy={sum(r['class_accuracy'] for r in rows) / n:.2f} "
          f"evidence_recall={sum(r['evidence_recall'] for r in rows) / n:.2f} "
          f"false_positives={sum(r['false_positives'] for r in rows)}")


if __name__ == "__main__":
    main()
