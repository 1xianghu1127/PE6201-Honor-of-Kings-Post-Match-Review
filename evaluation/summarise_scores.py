"""Command-line entry point for counting human evaluation ratings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics import summarise_scoring_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarise_scoring_csv(args.csv_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
