"""Phase 2 benchmark against pinned, separately downloaded source files.

The reviewed inventories below come from the actual parser declarations, not
from Flagcheck's extractor. No upstream code is imported or executed. The
oracle uses Python argparse to test option-spelling resolution only.
"""
from __future__ import annotations

import argparse
import contextlib
import io
from collections import Counter
from pathlib import Path

from flagcheck.schema import _command, extract_argparse
from flagcheck.scanner import scan_text


def inventory(zero: str, one: str, optional: str = "") -> dict[str, dict]:
    return {name: {"nargs": arity} for names, arity in ((zero, 0), (one, 1), (optional, "?"))
            for name in names.split()}


PROJECTS = {
    "build": {
        "receivers": {"parser"}, "scope": "main_parser",
        "actions": {"NegativeCountAction": 0},
        "commands": ("build", "pyproject-build"),
        "flags": inventory(
            "-h --help -V --version -q --quiet -v --verbose -s --sdist -w --wheel --metadata -n --no-isolation -x --skip-dependency-check",
            "-o --outdir --sdist-extract-dir --report -C --config-setting --config-json --installer --env-dir --dependency-constraints-txt"),
    },
    "audit": {
        "receivers": {"parser"}, "scope": "_parser", "actions": {}, "commands": ("pip-audit",),
        "flags": inventory(
            "-h --help -V --version -l --local --locked -d --dry-run -S --strict -v --verbose --fix --require-hashes --skip-editable --no-deps --disable-pip",
            "-r --requirement -f --format -s --vulnerability-service --osv-url --cache-dir --progress-spinner --timeout --path --index-url --extra-index-url -o --output --ignore-vuln",
            "--desc --aliases"),
    },
    "markitdown": {
        "receivers": {"parser"}, "scope": "main", "actions": {}, "commands": ("markitdown",),
        "flags": inventory(
            "-h --help -v --version -d --use-docintel --use-cu --use-content-understanding -p --use-plugins --list-plugins --keep-data-uris",
            "-o --output -x --extension -m --mime-type -c --charset -e --endpoint --cu-endpoint --cu-analyzer --cu-file-types --docintel-model-id --docintel-query-fields --docintel-features"),
    },
}

# Manually reviewed exact long-option occurrences in supported README shell
# examples. Each tuple is (physical line, logical command start, option, count).
# The count handles repeated literal options at the same location.
REAL_OPTIONS = {
    "build": [(79, 79, "--installer", 1)],
    "audit": [(132,132,"--help",1), (303,303,"--locked",1), (324,324,"--aliases",1),
              (335,335,"--desc",1), (408,408,"--fix",1), (443,443,"--ignore-vuln",1),
              (454,454,"--ignore-vuln",2), (475,475,"--local",1), (488,488,"--no-deps",1),
              (491,491,"--require-hashes",1)],
    "markitdown": [(120,120,"--list-plugins",1), (126,126,"--use-plugins",1),
                   (189,189,"--use-cu",1), (189,189,"--cu-endpoint",1), (196,196,"--use-cu",1),
                   (268,268,"--use-docintel",1), (269,268,"--endpoint",1),
                   (270,268,"--docintel-model-id",1), (271,268,"--docintel-features",1),
                   (272,268,"--docintel-query-fields",1), (415,415,"--list-plugins",1),
                   (416,416,"--use-plugins",1)],
}

WORKFLOWS = {
    'build': ('cd.yml', 'pre-release.yml', 'reusable-change-detection.yml', 'reusable-docs.yml', 'reusable-pytest.yml', 'reusable-type.yml', 'test.yml'),
    'audit': ('ci.yml', 'docs.yml', 'lint.yml', 'release.yml', 'scorecards.yml', 'zizmor.yml'),
    'markitdown': ('pre-commit.yml', 'tests.yml'),
}


def oracle(parser: argparse.ArgumentParser, candidate: str) -> tuple[str | None, str | None]:
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            ns, rest = parser.parse_known_args([candidate])
        except SystemExit:
            return "ambiguous", None
    if rest:
        return "unknown", None
    matched = next(k for k, value in vars(ns).items() if value)
    return (None, None) if candidate == matched else ("abbreviation", matched)


def format_inputs(command: str):
    yield "shell", command
    yield "make", "all:\n\t@" + command + "\n"
    yield "markdown", "```bash\n" + command + "\n```\n"
    yield "workflow", "jobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          " + command + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="directory with build/, audit/, markitdown/ inputs")
    data = parser.parse_args().data
    schemas = {}
    for name, cfg in PROJECTS.items():
        flags, notes = extract_argparse((data/name/"cli.py").read_text(), cfg["receivers"], action_arities=cfg["actions"], scope=cfg["scope"], discover_groups=True)
        assert not notes, (name, notes)
        assert flags == cfg["flags"], (name, set(flags) ^ set(cfg["flags"]), {k:(flags[k],cfg["flags"][k]) for k in flags.keys() & cfg["flags"].keys() if flags[k]!=cfg["flags"][k]})
        print(name, "reviewed spellings", len(flags), "long options", sum(f.startswith('--') for f in flags))
        for command in cfg["commands"]:
            schemas[command] = _command({"flags": flags, "complete": True})

    natural = Counter()
    real_mutations = Counter()
    for name in PROJECTS:
        files = [(data/name/"README.md", "markdown"), *((data/name/".github/workflows"/p,"workflow") for p in WORKFLOWS[name])]
        for path, kind in files:
            findings = scan_text(path.read_text(), schemas, kind, str(path))
            natural["files"] += 1
            natural["false_positive_findings"] += len(findings)
            assert not findings, (path, findings)
        lines = (data/name/"README.md").read_text().splitlines(keepends=True)
        for physical, logical, option, count in REAL_OPTIONS[name]:
            original = lines[physical-1]
            assert original.count(option) == count, (name, physical, option, original)
            start = 0
            for _ in range(count):
                offset = original.index(option, start)
                changed = lines.copy()
                changed[physical-1] = original[:offset] + '--flagcheck-benchmark-invalid' + original[offset+len(option):]
                findings = scan_text(''.join(changed), schemas, "markdown")
                real_mutations["cases"] += 1
                if [(f.flag,f.code,f.line) for f in findings] == [("--flagcheck-benchmark-invalid","unknown",logical)]:
                    real_mutations["detected"] += 1
                else:
                    print("MISSED OR EXTRA", name, physical, option, findings)
                start = offset + len(option)
    print("Natural files:", dict(natural))
    print("Mutation of real README option tokens:", dict(real_mutations))

    synthetic = Counter()
    for name, cfg in PROJECTS.items():
        long = {f: meta for f,meta in cfg["flags"].items() if f.startswith('--')}
        ref = argparse.ArgumentParser(add_help=False, allow_abbrev=True)
        for flag in sorted(long):
            ref.add_argument(flag, action='store_true', dest=flag)
        names = set(long)
        candidates = names | {f[:n] for f in names for n in range(3,len(f))} | {f+'-flagcheck-test-invalid' for f in names}
        for candidate in sorted(candidates):
            expected, suggestion = oracle(ref, candidate)
            canonical = candidate if expected is None else suggestion
            token = candidate + ('=sample' if canonical and long[canonical]['nargs'] != 0 else '')
            for command in cfg['commands']:
                command = 'python -m build' if command == 'build' else command
                for kind, text in format_inputs(command + ' ' + token):
                    findings = scan_text(text, schemas, kind)
                    actual = (findings[0].code,findings[0].suggestion) if len(findings)==1 else (None,None) if not findings else ('multiple',None)
                    synthetic['cases'] += 1
                    synthetic['expected_' + (expected or 'clean')] += 1
                    if actual == (expected,suggestion):
                        synthetic['correct'] += 1
                    else:
                        synthetic['mismatches'] += 1
                        print('MISMATCH', name, kind, candidate, (expected,suggestion), actual)
    print("Synthetic argparse oracle:", dict(synthetic))
    assert real_mutations['cases'] == real_mutations['detected']
    assert natural['files'] == 18 and real_mutations['cases'] == 24
    assert synthetic['cases'] == synthetic['correct']
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
