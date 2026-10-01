# Evaluation data exports

`evaluation_cases.json` and `labels.json` are generated derivatives of `../confirmed_evaluation_dataset.json`.

Do not edit these files directly. If `confirmed_evaluation_dataset.json` is corrected, regenerate both exports with:

```bash
.\.venv\Scripts\python.exe evaluation\export_split_dataset.py
```
