import json, pytest
from agent.evaluate import score
from agent.agent import validate

def test_score_perfect():
    truth = [{"fault": "comm_loss", "lines": [10, 11, 12]}]
    inc = [{"fault_class": "comm_loss", "evidence_lines": [10, 11, 12]}]
    s = score(truth, inc)
    assert s["class_accuracy"] == 1 and s["evidence_recall"] == 1 and s["false_positives"] == 0

def test_score_wrong_class_and_false_positive():
    truth = [{"fault": "comm_loss", "lines": [10, 11]}]
    inc = [{"fault_class": "db_timeout", "evidence_lines": [10]},
           {"fault_class": "config_error", "evidence_lines": [99]}]
    s = score(truth, inc)
    assert s["class_accuracy"] == 0 and s["false_positives"] == 1

def test_validate_drops_invented_lines_and_classes():
    data = {"incidents": [
        {"fault_class": "comm_loss", "evidence_lines": [1, 500]},
        {"fault_class": "nonsense", "evidence_lines": [1]}]}
    out = validate(data, {1, 2, 3})
    assert len(out) == 1 and out[0]["evidence_lines"] == [1]

@pytest.mark.llm
def test_agent_end_to_end():
    from agent.parser import parse_file
    from agent.agent import triage
    truth = json.load(open("data/truth.json"))
    s = score(truth, triage(parse_file("data/logs.txt")))
    assert s["class_accuracy"] >= 0.6
