"""
CLI Entry Point for the Multi-Source Candidate Data Transformer.

Usage:
    python -m app.cli transform [OPTIONS]
    python -m app.cli diff-gold OUTPUT GOLD [--threshold 0.8]

Examples:
    python -m app.cli transform \\
        --csv data/recruiter.csv \\
        --resume data/sample_resume.pdf \\
        --linkedin data/linkedin_stub.json \\
        --config config/projection_config.json \\
        --merge-config config/merge_config.json \\
        --out output/result.json

    python -m app.cli diff-gold output/result.json data/gold_profile.json --pretty
"""

import argparse
import json
import logging
import os
import sys


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s  %(name)s  %(message)s",
    )


def cmd_transform(args) -> int:
    _setup_logging(args.verbose)
    from app.services.transformation_service import TransformationService

    service = TransformationService()
    try:
        result = service.transform(
            csv_path=args.csv,
            resume_path=args.resume,
            config_path=args.config,
            linkedin_path=args.linkedin,
            merge_config_path=args.merge_config,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Emit result
    indent = 2 if args.pretty else None
    output_str = json.dumps(result, indent=indent, ensure_ascii=False, default=str)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"Result written to {args.out}")
    else:
        print(output_str)

    # Print summary to stderr so it's visible even when piping JSON
    report = result.get("data_quality_report", {})
    print(
        f"\n--- Quality Report ---\n"
        f"  Sources processed : {report.get('sources_processed')}\n"
        f"  Sources failed    : {report.get('sources_failed')}\n"
        f"  Fields missing    : {report.get('fields_missing')}\n"
        f"  Fields conflicted : {report.get('fields_conflicted')}\n"
        f"  Overall confidence: {report.get('overall_confidence')}\n"
        f"  Skills found      : {report.get('skill_count')}\n"
        f"----------------------",
        file=sys.stderr,
    )
    return 0


def cmd_diff_gold(args) -> int:
    _setup_logging(False)
    # Delegate to tools/diff_gold.py logic
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.diff_gold import diff

    try:
        with open(args.output, "r", encoding="utf-8") as f:
            raw_output = json.load(f)
        with open(args.gold, "r", encoding="utf-8") as f:
            gold = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if "projected_output" in raw_output:
        output = raw_output["projected_output"]
        if "overall_confidence" not in output and "canonical_profile" in raw_output:
            output["overall_confidence"] = raw_output["canonical_profile"].get(
                "overall_confidence", 0.0
            )
    else:
        output = raw_output

    report = diff(output, gold, args.threshold)
    indent = 2 if args.pretty else None
    print(json.dumps(report, indent=indent))

    summary = report["summary"]
    wbc = summary["wrong_but_confident"]
    print(
        f"\nAccuracy: {summary['accuracy_pct']}%  |  "
        f"Wrong-but-confident: {wbc}  |  "
        f"Threshold: {args.threshold}",
        file=sys.stderr,
    )
    return 1 if wbc > 0 else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Multi-Source Candidate Data Transformer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── transform ─────────────────────────────────────────────────────────────
    t = sub.add_parser("transform", help="Run the full transformation pipeline")
    t.add_argument("--csv",          required=True,  help="Path to recruiter CSV")
    t.add_argument("--resume",       required=True,  help="Path to resume PDF")
    t.add_argument("--linkedin",     default=None,   help="Path to LinkedIn stub JSON (optional)")
    t.add_argument("--config",       default="config/projection_config.json",
                   help="Path to projection config JSON")
    t.add_argument("--merge-config", default="config/merge_config.json",
                   dest="merge_config", help="Path to merge strategy config JSON")
    t.add_argument("--out",          default=None,   help="Output file path (default: stdout)")
    t.add_argument("--pretty",       action="store_true", help="Pretty-print JSON output")
    t.add_argument("--verbose",      action="store_true", help="Enable debug logging")
    t.set_defaults(func=cmd_transform)

    # ── diff-gold ─────────────────────────────────────────────────────────────
    d = sub.add_parser("diff-gold", help="Compare output against a gold reference profile")
    d.add_argument("output",    help="Path to pipeline output JSON (full result or projected_output)")
    d.add_argument("gold",      help="Path to gold reference profile JSON")
    d.add_argument("--threshold", type=float, default=0.80,
                   help="Confidence threshold for wrong-but-confident (default: 0.80)")
    d.add_argument("--pretty",    action="store_true", help="Pretty-print JSON output")
    d.set_defaults(func=cmd_diff_gold)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
