import json, sys
from .parser import parse_file
from .agent import triage

def score(truth, incidents):
    rows = []
    for t in truth:
        tl = set(t["lines"])
        best = max(incidents, key=lambda i: len(tl & set(i["evidence_lines"])), default=None)
        ov = len(tl & set(best["evidence_lines"])) if best else 0
        rows.append({
            "fault": t["fault"],
            "predicted": best["fault_class"] if best and ov else None,
            "class_correct": bool(best and ov and best["fault_class"] == t["fault"]),
            "evidence_recall": ov / len(tl),
            "evidence_precision": ov / len(best["evidence_lines"]) if best and ov else 0.0,
        })
    all_truth = {n for t in truth for n in t["lines"]}
    false_pos = sum(1 for i in incidents if not (set(i["evidence_lines"]) & all_truth))
    n = len(rows) or 1
    return {
        "class_accuracy": sum(r["class_correct"] for r in rows) / n,
        "evidence_recall": sum(r["evidence_recall"] for r in rows) / n,
        "evidence_precision": sum(r["evidence_precision"] for r in rows) / n,
        "false_positives": false_pos,
        "details": rows,
    }

def main():
    logfile, truthfile = sys.argv[1], sys.argv[2]
    truth = json.load(open(truthfile))
    incidents = triage(parse_file(logfile))
    print(json.dumps(score(truth, incidents), indent=2))

if __name__ == "__main__":
    main()
