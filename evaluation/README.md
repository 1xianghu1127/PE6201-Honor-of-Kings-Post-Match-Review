# Evaluation guide

This folder contains the scripts used to compare the rule baseline and the RAG system on the same 40 cases. The comparison reports four checks separately rather than collapsing them into one score.

## Data used

`../confirmed_evaluation_dataset.json` is the source dataset. It contains 30 `none`, 6 `partial`, and 4 `full` abstention cases. `../evaluation_dataset_readme.md` records the review status and interpretation rules. The files in `../data/` are derived exports and should not be edited directly.

`../guardrail_cases.json` is a separate set of validation, API, malformed-output, and semantic-consistency cases. It is not included in the main 40-case quality comparison.

## Measures

- **Match-data consistency:** claims agree with the submitted statistics.
- **Grounding correctness:** RAG claims are supported by the input or retrieved knowledge. This is not applicable to the non-retrieval baseline.
- **Actionability:** the review gives a concrete next-match action or an appropriate request for missing data.
- **Correct abstention:** the output uses the expected `none`, `partial`, or `full` level.

Human scores are recorded as `yes`, `no`, or `n/a` in the two scoring CSV files. The metrics script reports passed, applicable, unscored, and not-applicable counts so missing ratings cannot silently count as passes.

## Scripts and outputs

| Script | Purpose | Output |
|---|---|---|
| `run_guardrail_eval.py` | Run deterministic guardrail cases | `results/guardrail_results.json` |
| `run_baseline_eval.py` | Run all 40 cases through the rule system | `results/baseline_outputs.json`, baseline scoring CSV |
| `run_rag_eval.py` | Run the same cases through retrieval and GPT-4o-mini | `results/rag_outputs.json`, RAG scoring CSV |
| `summarise_scores.py` | Count each human-scored measure | printed JSON summary |
| `export_split_dataset.py` | Regenerate the derived data exports | files under `../data/` |

The checked-in result files are the final run used in the report. Re-running either main evaluation overwrites its output and scoring template.

## Final observed results

| Measure | Baseline | RAG |
|---|---:|---:|
| Match-data consistency | 40/40 | 40/40 |
| Grounding correctness | N/A | 33/40 |
| Actionability | 36/40 | 38/40 |
| Correct abstention | 40/40 | 40/40 |

The baseline cost was $0 and its mean latency was 0.000134 seconds. The RAG run used 96,966 tokens, cost $0.019059, and averaged 6.608 seconds per case. All 9 automated guardrail checks passed. Three additional cases require manual or integration-level observation.

## Reproduction order

1. Run the offline unit suite from the repository root.
2. Run `run_guardrail_eval.py`.
3. Run the baseline and score its CSV.
4. Run a two-case RAG smoke test with `--limit 2`.
5. Run the full RAG evaluation and score its CSV.
6. Run `summarise_scores.py` once for each scoring file.

The RAG script requires `--confirm-api-spend` and asks for an OpenRouter key in the terminal. The key is not saved by the project.

## Evaluation caveats

The cases are synthetic and the project owner performed the final review, so there is no independent second-rater agreement measure. The knowledge base is small and partly project-authored. In addition, the RAG pipeline retried 31 cases and applied deterministic repair to 24; the reported scores therefore evaluate the complete guarded system rather than the uncorrected first model draft.
