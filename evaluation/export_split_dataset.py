"""Export input cases and labels derived from the reviewed source dataset."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = json.loads((ROOT / "confirmed_evaluation_dataset.json").read_text(encoding="utf-8"))
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    cases = {
        "source_version": source["version"],
        "cases": [{"case_id": item["case_id"], "category": item["category"], **item["input"]} for item in source["cases"]],
    }
    labels = {
        "source_version": source["version"],
        "labels": [{"case_id": item["case_id"], **item["ground_truth"]} for item in source["cases"]],
    }
    (data_dir / "evaluation_cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Exported 40 reviewed cases and labels to data/.")


if __name__ == "__main__":
    main()
