"""Held-out schema checks against pinned Bandit and PyPA Installer sources.

Inputs are local copies of upstream files. No target parser is imported or run.
The explicit inventories were reviewed from the parser declarations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from flagcheck.schema import _command, extract_argparse
from flagcheck.scanner import ScanStats, scan_text
from independent import inventory, oracle, format_inputs


PROJECTS = {
    "bandit": {
        "scope": "main", "command": "bandit", "invocation": "bandit",
        "flags": inventory(
            "-h --help -r --recursive -l --level -i --confidence -v --verbose -d --debug -q --quiet --silent --ignore-nosec --exit-zero --version",
            "-a --aggregate -n --number -c --configfile -p --profile -t --tests -s --skip --severity-level --confidence-level -f --format --msg-template -x --exclude -b --baseline --ini",
            "-o --output"),
    },
    "installer": {
        "scope": "_get_main_parser", "command": "installer", "invocation": "python -m installer",
        "flags": inventory("-h --help --no-compile-bytecode --overwrite-existing",
                           "--destdir -d --prefix -p --compile-bytecode --validate-record"),
    },
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data", type=Path)
    root = p.parse_args().data
    totals = Counter()
    schemas = {}
    for name, cfg in PROJECTS.items():
        source = (root / name / "cli.py").read_text(encoding="utf-8")
        flags, notes = extract_argparse(source, {"parser"}, scope=cfg["scope"], discover_groups=True)
        assert not notes, (name, notes)
        assert flags == cfg["flags"], (name, set(flags) ^ set(cfg["flags"]))
        schema = {cfg["command"]: _command({"flags": flags, "complete": True})}
        schemas.update(schema)
        print(name, "reviewed spellings", len(flags))
        longs = {flag: metadata for flag, metadata in flags.items() if flag.startswith("--")}
        ref = argparse.ArgumentParser(add_help=False)
        for flag in sorted(longs):
            ref.add_argument(flag, action="store_true", dest=flag)
        candidates = set(longs) | {f[:n] for f in longs for n in range(3, len(f))} | {f + "-flagcheck-invalid" for f in longs}
        for candidate in sorted(candidates):
            expected, suggestion = oracle(ref, candidate)
            canonical = candidate if expected is None else suggestion
            token = candidate + ("=sample" if canonical and longs[canonical]["nargs"] != 0 else "")
            for kind, snippet in format_inputs(cfg["invocation"] + " " + token):
                findings = scan_text(snippet, schema, kind)
                actual = (findings[0].code, findings[0].suggestion) if len(findings) == 1 else (None, None) if not findings else ("multiple", None)
                totals["cases"] += 1
                totals["correct"] += actual == (expected, suggestion)
                assert actual == (expected, suggestion), (name, kind, token, actual, expected, suggestion)

    # RST is not a supported input format. Test only these manually reviewed
    # literal shell snippets, not the RST files as a whole.
    examples = {"start.rst": (53, 75, 100, 106, 115, 121), "config.rst": (59, 63, 71, 164, 226)}
    stats = ScanStats()
    snippets = []
    for filename, line_numbers in examples.items():
        lines = (root / "bandit" / filename).read_text(encoding="utf-8").splitlines()
        for number in line_numbers:
            command = lines[number - 1].strip()
            assert "bandit " in command, (filename, number, command)
            snippets.append(command)
            assert not scan_text(command, schemas, "shell", stats=stats), (filename, number, command)
    assert stats.matched_invocations == len(snippets), (stats, snippets)
    literal = next(command for command in snippets if "--ini" in command)
    findings = scan_text(literal.replace("--ini", "--flagcheck-invalid"), schemas)
    assert [(f.flag, f.code) for f in findings] == [("--flagcheck-invalid", "unknown")]
    print("Bandit extracted documentation snippets:", len(snippets), "matched", stats.matched_invocations, "findings 0; deliberate mutation 1/1")
    print("Generated argparse name checks:", dict(totals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
