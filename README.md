# Honor of Kings Post-Match Review Assistant

This project turns one player's structured post-match statistics into three short sections: what went well, what to improve, and what to focus on in the next match. It compares a deterministic, non-AI baseline with a retrieval-augmented GPT-4o-mini pipeline on the same 40-case evaluation set.

The current scope is deliberately narrow. It accepts manually entered statistics; it does not upload screenshots, infer unrecorded match events, or operate as an autonomous agent.

## Product definition

**Persona.** A casual or intermediate Honor of Kings player who can read the post-match statistics screen but wants a concise interpretation of their own performance.

**Input.** Hero, role, match duration, result, K/D/A, gold and gold share, damage dealt and share, damage taken and share, and kill participation.

**Output.** Both systems return the same review structure:

- `What went well`
- `What to improve`
- `Next-match focus`

Each review also records an abstention level. `none` means a complete review, `partial` means only supported dimensions are reviewed, and `full` means the system explains why it cannot judge performance.

## Architecture

```text
                         +-----------------------------+
                         | Manually entered match data |
                         +--------------+--------------+
                                        |
                              validation / abstention
                                        |
                   +--------------------+--------------------+
                   |                                         |
          +--------v---------+                     +---------v----------+
          | Fixed role rules |                     | Local TF-IDF search |
          | and thresholds   |                     | over knowledge base |
          +--------+---------+                     +---------+----------+
                   |                                         |
                   |                                analytical facts
                   |                                         |
                   |                              GPT-4o-mini generation
                   |                                         |
                   |                              deterministic checks
                   |                                         |
          +--------v---------+                     +---------v----------+
          | Non-AI baseline  |                     | RAG + LLM review   |
          +------------------+                     +--------------------+
```

The two branches use the same input cases and output headings, making the comparison direct. The RAG branch may retry once when a generated review contradicts a threshold or role rule. A deterministic repair is applied if the second draft still fails the checks.

## Evaluation results

The target metrics are reported separately as counts; they are not combined into a single "useful and correct" score. No numeric pass threshold was declared in advance.

| Metric | Rule baseline | RAG + GPT-4o-mini |
|---|---:|---:|
| Match-data consistency | 40/40 | 40/40 |
| Grounding correctness | N/A | 33/40 |
| Actionability | 36/40 | 38/40 |
| Correct abstention | 40/40 | 40/40 |

| Operational measure | Rule baseline | RAG + GPT-4o-mini |
|---|---:|---:|
| Mean latency per case | 0.000134 s | 6.608 s |
| Maximum latency | 0.000483 s | 11.254 s |
| Total tokens | 0 | 96,966 |
| Total API cost | $0 | $0.019059 |

The RAG run made 67 model calls for 40 cases. Thirty-one cases needed the permitted retry, and 24 still needed deterministic repair. This is an important limitation: the final scores describe the guarded pipeline, not the raw first model response.

The 40-case dataset contains 30 complete-review cases, 6 partial-abstention cases, and 4 full-abstention cases. The cases are synthetic. They were reviewed and accepted by the project owner before the final comparison; AI assistance used while drafting labels is disclosed in the dataset documentation. See [evaluation_dataset_readme.md](evaluation_dataset_readme.md) and [evaluation/README.md](evaluation/README.md) for the data and evaluation protocols.

## Repository guide

```text
app.py                              Streamlit demonstration interface
confirmed_evaluation_dataset.json  40 reviewed cases and labels
guardrail_cases.json                separate validation and reliability cases
baseline/                           deterministic comparison system
knowledge_base/                     local RAG documents and source record
rag/                                retrieval, analytical facts, and generation
guardrails/                         input, structure, and consistency checks
evaluation/                         evaluation scripts and methodology
evaluation/results/                 final outputs and scoring records
tests/                              offline unit and Streamlit smoke tests
start_app.ps1                       secure terminal-key launcher for Windows
```

Python files contain short module-level descriptions so the responsibility of each module can be scanned without reading every function.

## Setup

The project was tested with Python 3.12.6. The commands below assume Windows PowerShell and that the terminal is open in the project directory.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The project does not use a `.env` file. Do not place an API key in source code, documentation, screenshots, or submitted files.

## Offline checks

These checks do not call OpenRouter and do not use API credit.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe evaluation\run_guardrail_eval.py
```

The current suite reports `Ran 31 tests` and `OK`. The guardrail script reports 9/9 automatic checks passed; three API or malformed-output scenarios remain manual/integration checks.

## Run the web demonstration

```powershell
.\start_app.ps1
```

Enter an OpenRouter API key when prompted. The input is hidden and the key is kept only in the process environment until Streamlit exits. Open the local URL printed by Streamlit, normally `http://localhost:8501`.

The page can run the rule baseline, the RAG pipeline, or both. The baseline is free. The RAG option calls `openai/gpt-4o-mini` through OpenRouter and may incur a small charge.

## Reproduce the evaluation

The final result files are already included for inspection. Re-running an evaluation overwrites its output and scoring CSV, so copy the existing files first if they must be preserved.

Run the non-AI baseline:

```powershell
.\.venv\Scripts\python.exe evaluation\run_baseline_eval.py
```

Before a full paid run, test two cases:

```powershell
.\.venv\Scripts\python.exe evaluation\run_rag_eval.py --confirm-api-spend --limit 2
```

Run all 40 RAG cases:

```powershell
.\.venv\Scripts\python.exe evaluation\run_rag_eval.py --confirm-api-spend
```

The terminal prompts for the API key with hidden input. After a run, complete the human-scoring CSV and summarise each system separately:

```powershell
.\.venv\Scripts\python.exe evaluation\summarise_scores.py evaluation\results\baseline_human_scoring.csv
.\.venv\Scripts\python.exe evaluation\summarise_scores.py evaluation\results\rag_human_scoring.csv
```

## Limitations

- Manual entry can introduce transcription errors.
- Summary statistics cannot establish positioning, skill accuracy, objective control, communication, or teammate behaviour.
- The role thresholds are project assumptions, not official competitive standards.
- TF-IDF retrieval is transparent and reproducible but has limited semantic matching.
- The synthetic cases and labels were reviewed by the project owner rather than independent raters, so inter-rater reliability was not measured.
- Grounding was checked against a small knowledge base that includes project-authored guidance.
- The final RAG output still depends heavily on deterministic checks and repair.
