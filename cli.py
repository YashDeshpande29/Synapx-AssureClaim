"""
Command-line interface for the AssureClaim FNOL processing agent.

Usage:
    python cli.py sample_fnols/fnol_001.txt
    python cli.py --all
    python cli.py --text "Policy Number: POL-2024-00123 ..."
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from agent.pipeline import process_file, process_text


SAMPLE_DIR = Path(__file__).parent / "sample_fnols"

ROUTE_COLORS = {
    "Fast-track":         "\033[92m",   # green
    "Manual Review":      "\033[93m",   # yellow
    "Specialist Queue":   "\033[94m",   # blue
    "Investigation Flag": "\033[91m",   # red
    "Standard Review":    "\033[96m",   # cyan
}
RESET = "\033[0m"


def _colored_route(route: str) -> str:
    color = ROUTE_COLORS.get(route, "")
    return f"{color}{route}{RESET}" if color else route


def _print_result(result: dict, label: str = "") -> None:
    if label:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")

    route = result["recommendedRoute"]
    print(f"  Route     : {_colored_route(route)}")
    print(f"  Reasoning : {result['reasoning']}")

    missing = result["missingFields"]
    if missing:
        print(f"  Missing   : {', '.join(missing)}")
    else:
        print("  Missing   : (none)")

    print("\n  Extracted Fields:")
    for k, v in result["extractedFields"].items():
        if v is not None and v != [] and v != "":
            print(f"    {k}: {v}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AssureClaim — Autonomous Insurance Claims Processing Agent"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="Path to a single FNOL file (.txt or .pdf)")
    group.add_argument("--all", action="store_true", help="Process all sample FNOLs")
    group.add_argument("--text", type=str, help="Process raw FNOL text directly")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output raw JSON")

    args = parser.parse_args()

    if args.text:
        result = process_text(args.text)
        if args.json_out:
            print(json.dumps(result, indent=2))
        else:
            _print_result(result, label="Inline Text Input")

    elif args.all:
        files = sorted(glob.glob(str(SAMPLE_DIR / "*.txt")) + glob.glob(str(SAMPLE_DIR / "*.pdf")))
        if not files:
            print(f"No FNOL files found in {SAMPLE_DIR}")
            sys.exit(1)

        results = []
        for fpath in files:
            result = process_file(fpath)
            results.append(result)
            if args.json_out:
                print(json.dumps(result, indent=2))
            else:
                _print_result(result, label=Path(fpath).name)

        if not args.json_out:
            print(f"\nSummary: processed {len(results)} FNOL(s)")
            for i, r in enumerate(results, 1):
                route = r["recommendedRoute"]
                print(f"  fnol_{i:03d}: {_colored_route(route)}")

    else:
        if not args.file:
            parser.print_help()
            sys.exit(1)
        result = process_file(args.file)
        if args.json_out:
            print(json.dumps(result, indent=2))
        else:
            _print_result(result, label=Path(args.file).name)


if __name__ == "__main__":
    main()
