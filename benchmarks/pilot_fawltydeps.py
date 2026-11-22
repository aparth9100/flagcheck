"""Read-only FawltyDeps #293 case study (no target code execution).

Run from this repository: PYTHONPATH=src python benchmarks/pilot_fawltydeps.py CHECKOUT
The checkout must be the pinned 6b57917cc4824ebae253303dd004d990eb569ba4 source.
"""
import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from flagcheck.scanner import ScanStats, scan_command, scan_text
from flagcheck.schema import Command, Flag, extract_argparse


PINNED_BLOBS = {
    'fawltydeps/cli_parser.py': 'a477e21a46583df0ea317bbc193d48df13103acd',
    'README.md': 'b453d52779ed4f38cd80a77d5189f1aef0b01513',
    'docs/usage.md': 'a228b07e5584b6e34c4bae16c4ec1d51b6d6e0a3',
    'docs/configuration.md': 'e4565c03a4d0d6369456860abbccc6f6d901594e',
    'docs/how_to_guides.md': 'ef80673b1230e2b1e30dbb8af06651f12fdc2ace',
    'docs/FAQ.md': 'e0d00851152da7134492f3ea3f1ea754e0ad1eed',
    'docs/installation.md': '7e9cda419fd89ee9b784550315f07f6ddf986a61',
}


def read_pinned(root, path):
    raw = (root / path).read_bytes()
    git_blob = f'blob {len(raw)}\0'.encode() + raw
    assert hashlib.sha1(git_blob).hexdigest() == PINNED_BLOBS[path], path
    return raw.decode('utf-8')


def build_schema(source):
    flags, notes = extract_argparse(source, {'parser'})
    # The eight custom actions have explicit nargs='+'; their action combines
    # values, but does not change how many tokens argparse consumes.
    variadic = {'--code', '--deps', '--pyenv', '--exclude', '--exclude-from',
                '--custom-mapping-file', '--ignore-undeclared', '--ignore-unused'}
    assert len(notes) == len(variadic) and all("unsupported action 'union'" in n for n in notes)
    flags.update({name: {'nargs': '+'} for name in variadic})
    assert len(flags) == 30 and '--custom-mapping-file' in flags
    return {'fawltydeps': Command({k: Flag(**v) for k, v in flags.items()}, complete=True)}


def main(root):
    schema = build_schema(read_pinned(root, 'fawltydeps/cli_parser.py'))
    stats = ScanStats()
    findings = []
    paths = ('README.md', 'docs/usage.md', 'docs/configuration.md',
             'docs/how_to_guides.md', 'docs/FAQ.md', 'docs/installation.md')
    for path in paths:
        findings.extend(scan_text(read_pinned(root, path), schema,
                                  'markdown', path, stats=stats))
    print('Original docs:', json.dumps([asdict(f) for f in findings]))
    print('Coverage:', json.dumps(asdict(stats), sort_keys=True))
    assert not findings
    assert stats.matched_invocations == 17 and stats.checked_long_options == 14
    # These are issue reproductions, not findings from the docs above.
    for flag, value, expected in [('--ignore-undec', 'pandas', '--ignore-undeclared'),
                                  ('--custom-mapping', 'mapping.toml', '--custom-mapping-file')]:
        finding, = scan_command(f'fawltydeps {flag} {value}', schema)
        assert (finding.code, finding.suggestion) == ('abbreviation', expected)
        assert not scan_command(f'fawltydeps {expected} {value}', schema)
        # Standalone stdlib parser oracle using only the relevant declaration.
        # This tests prefix resolution, not FawltyDeps' runtime semantics.
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(expected, nargs='+')
        assert parser.parse_args([flag, value]) == parser.parse_args([expected, value])
        strict = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
        strict.add_argument(expected, nargs='+')
        _, remainder = strict.parse_known_args([flag, value])
        assert flag in remainder
        print(f'{flag}: {finding.code} -> {finding.suggestion}; oracle agrees')
    return findings


if __name__ == '__main__':
    main(Path(sys.argv[1]))
