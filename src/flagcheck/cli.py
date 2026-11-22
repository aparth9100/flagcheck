from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from pathlib import Path

import yaml

from flagcheck import __version__
from flagcheck.schema import extract_argparse, load_schema
from flagcheck.scanner import ScanStats, file_kind, scan_command, scan_text


def _targets(paths: list[Path]):
    seen: set[Path] = set()
    for root in paths:
        if not root.exists():
            raise OSError(f"missing input: {root}")
        candidates = sorted(root.rglob("*")) if root.is_dir() else [root]
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            # Respect explicit files and project roots named e.g. "build".
            # Only ignore generated directories below a recursively scanned root.
            if root.is_dir() and any(p in {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"} for p in path.relative_to(root).parts[:-1]):
                continue
            kind = file_kind(path)
            if kind is None or path.resolve() in seen:
                continue
            seen.add(path.resolve())
            yield path, kind


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="flagcheck", allow_abbrev=False)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="operation", required=True)
    scan = sub.add_parser("scan", help="lint files using a reviewed JSON schema", allow_abbrev=False)
    scan.add_argument("--schema", required=True, type=Path)
    scan.add_argument("--format", choices=("text", "json"), default="text")
    scan.add_argument("--fail-on", choices=("warning", "error"), default="warning")
    scan.add_argument("--cmd", help="scan a single command instead of files")
    scan.add_argument("--summary", action="store_true", help="emit partial scan coverage counters as JSON to stderr")
    scan.add_argument("--require-match", action="store_true", help="return status 2 if no configured command was recognized")
    scan.add_argument("paths", nargs="*", type=Path)
    gen = sub.add_parser("schema-from-source", help="extract literal argparse declarations without executing Python", allow_abbrev=False)
    gen.add_argument("source", type=Path)
    gen.add_argument("--command", required=True)
    gen.add_argument("--receiver", action="append", required=True, help="parser or argument-group variable; repeat as needed")
    gen.add_argument("--complete", action="store_true", help="assert that the selected declarations form the entire parser")
    gen.add_argument("--no-abbrev", action="store_true")
    gen.add_argument("--implicit-help", action="store_true", help="confirm -h/--help for an indirect parser constructor")
    gen.add_argument("--action-arity", action="append", default=[], metavar="NAME=N", help="reviewed custom argparse action's number of value tokens; repeat as needed")
    args = parser.parse_args(argv)
    try:
        if args.operation == "schema-from-source":
            overrides = {}
            for entry in args.action_arity:
                key, sep, number = entry.partition("=")
                if not sep or not key or not number.isdecimal():
                    raise ValueError("--action-arity must have the form NAME=N (N >= 0)")
                overrides[key] = int(number)
            flags, notes = extract_argparse(args.source.read_text(encoding="utf-8"), set(args.receiver),
                                            action_arities=overrides, implicit_help=args.implicit_help)
            if not flags:
                raise ValueError("no literal flags found on selected receiver(s)")
            for note in notes:
                print(f"flagcheck: {note}", file=sys.stderr)
            if args.complete and notes:
                raise ValueError("cannot mark extraction complete: unresolved declarations")
            print(json.dumps({args.command: {"complete": args.complete, "allow_abbrev": not args.no_abbrev, "flags": flags}}, indent=2, sort_keys=True))
            return 0
        if args.cmd is not None and args.paths:
            raise ValueError("choose --cmd or file paths, not both")
        schemas = load_schema(args.schema)
        stats = ScanStats()
        files_scanned = 0
        if args.cmd is not None:
            findings = scan_command(args.cmd, schemas, stats=stats)
        elif args.paths:
            targets = list(_targets(args.paths))
            if not targets:
                raise ValueError("no supported input files found")
            findings = []
            for path, kind in targets:
                findings.extend(scan_text(path.read_text(encoding="utf-8"), schemas, kind, str(path), stats=stats))
                files_scanned += 1
        else:
            raise ValueError("provide --cmd or at least one path")
        if args.summary:
            print(json.dumps({"files_scanned": files_scanned, **asdict(stats)}, sort_keys=True), file=sys.stderr)
        if args.require_match and not stats.matched_invocations:
            raise ValueError("no configured command was recognized")
        if args.format == "json":
            print(json.dumps([f.to_dict() for f in findings], indent=2))
        else:
            for finding in findings:
                print(f"{finding.source}:{finding.line}: {finding.severity} {finding.code}: {finding.command} {finding.flag}: {finding.message}")
        return int(any(f.severity == "error" or args.fail_on == "warning" for f in findings))
    except (OSError, ValueError, SyntaxError, yaml.YAMLError) as exc:
        print(f"flagcheck: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
