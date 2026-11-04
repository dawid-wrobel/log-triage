# AI Log Triage Agent

An LLM agent that reads an industrial (SCADA-style) log file, finds incidents, classifies them and returns a probable root cause **with evidence: the exact log lines**. It runs fully locally in Docker (Ollama + a 3B model, 4 GB VRAM is enough) and is evaluated against ground-truth labels produced by a synthetic log generator.

Detected fault classes: `db_timeout`, `invalid_input`, `calc_exception`, `comm_loss`, `config_error`.

**Stack:** Python 3.11, Ollama (`qwen2.5:3b`, tool calling), OpenAI-compatible API client, Docker Compose, pytest.

## Architecture

```
 logs.txt --> [ parser ] --> LogLine list
                                  |
                                  v
 +-----------------------------------------------+
 |                   LogTools                    |
 |   find_incident_clusters    search_logs       |
 |   get_context               count_by_subsystem|
 +-----------------------+-----------------------+
                         ^   tool calls / results
                         v
               +--------------------+
               |   LLM (Ollama)     |
               +---------+----------+
                         | JSON answer
                         v
               +--------------------+
               |    validate()      |   drops invented classes / lines
               +---------+----------+
                         |
                         v
               +--------------------+   uncovered clusters
               |   coverage check   | ----------------------> back to LLM (max 2x)
               +---------+----------+
                         | all clusters covered
                         v
               incidents + evidence lines (JSON)
```

- **Tool-calling loop:** the model never sees the whole file, only what its tools return, so every evidence line is traceable to tool output.
- **Deterministic clustering:** WARN/ERROR lines of one subsystem that are close in time (default gap: 10 s) are grouped into clusters, so the small model only has to classify and explain.
- **Validation:** unknown fault classes and line numbers that do not exist in the log are dropped (anti-hallucination).
- **Coverage check:** clusters not covered by any reported incident are sent back to the model, which must return the complete answer.
- **Safety limits:** max 12 agent steps, capped tool output size, tool errors returned to the model as text.
- **Provider-agnostic:** the OpenAI-compatible client works with Ollama or any compatible API by changing three environment variables.

## Quick start

Requirements: Docker (on Windows: Docker Desktop with WSL2 backend; keep the project in the WSL filesystem, e.g. `~/log-triage`, not in `/mnt/c`).

```bash
git clone https://github.com/dawid-wrobel/log-triage.git
cd log-triage

docker compose build
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:3b

# generate synthetic logs + ground truth (data/logs.txt, data/truth.json)
docker compose run --rm agent python generate_logs.py

# run the agent (-v shows tool calls); the result is printed and saved to data/triage.json
docker compose run --rm agent python -m agent data/logs.txt -v
```

`docker-compose.yml` reserves an NVIDIA GPU for Ollama. Without a GPU, delete the `deploy:` block of the `ollama` service (the model then runs on CPU, slower).

Stop the stack with `docker compose stop` (the model stays in the `ollama` volume).

### Using a cloud LLM instead of Ollama

Create `.env` next to `docker-compose.yml` (it is git-ignored):

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=<model with tool calling>
LLM_API_KEY=<your key>
```

The code does not change. Check the provider's current free-tier limits.

## Tests and evaluation

```bash
# unit tests (no LLM needed): parser, tools, scoring, validation
docker compose run --rm agent pytest -m "not llm" -v

# end-to-end test with the real model
docker compose run --rm agent pytest -m llm -v

# evaluate on one log against data/truth.json
docker compose run --rm agent python -m agent.evaluate data/logs.txt data/truth.json

# evaluate on several freshly generated logs (default seeds 1-5), prints per-seed and mean metrics
docker compose run --rm agent python -m scripts.eval_seeds
docker compose run --rm agent python -m scripts.eval_seeds --seeds 11 12 13
```

`generate_logs.py` injects the faults itself, so `truth.json` (fault type, subsystem, line numbers) is exact and no manual labelling is needed. A fixed `--seed` makes datasets reproducible.

### Metrics

Each ground-truth incident is matched to the agent incident that shares the most log lines with it.

- `class_accuracy`: share of true incidents with the correct fault class (a missed incident counts as wrong)
- `evidence_recall`: share of the true incident's lines reported as evidence
- `evidence_precision`: share of the reported lines that belong to that true incident
- `false_positives`: reported incidents that touch no true incident

## Results

Model `qwen2.5:3b`, 300-line logs with 5 injected faults each. Mean over 5 generated logs (seeds 1-5, not used for tuning); `false_positives` is the total over the 5 logs. Each version includes the previous one.

|hash | Version | class_accuracy | evidence_recall | false_positives |
|---|---|---|---|---|
|b8746bc|Improve prompt: require WARN search and context per cluster| 0.68 | 0.58 | 1 |
|4d1ea7b|Improve prompt: Add find_incident_clusters tool| 0.96 | 0.97 | 0 |
|ec9faf9|Add coverage check: ask the model to cover missing incident clusters| 0.96 | 0.97 | 0 |

Moving incident grouping from the prompt into the deterministic `find_incident_clusters` tool gave the largest gain (class accuracy 0.68 to 0.96, evidence recall 0.58 to 0.97, false positives 1 to 0), while the coverage check did not change the means on these five logs.

## Limitations

- **Synthetic, easy data:** every log contains one incident of each of the five types, built from fixed message templates. Real logs are noisier.
- **Small sample:** 5 logs x 5 incidents = 25 incidents; one incident moves a metric by 4-20 points.
- **Non-determinism:** even at `temperature=0`, a cold and a warm model in Ollama gave slightly different answers on the same log. Measurements use a warm-up run first.
- **Merged incidents:** on seed 5 the model reported two separate `calc-module` incidents (`config_error` and `calc_exception`, 93 s apart, in two different clusters) as one incident labelled `calc_exception`, giving evidence precision 0.5 for `config_error`. The coverage check does not catch this, because every cluster is covered.
- No comparison yet with larger models.