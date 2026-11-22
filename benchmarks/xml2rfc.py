"""Re-run the targeted benchmark on review-supplied pinned upstream files.

No network access, cloning or execution of upstream code is performed.
Pass the parser, original Makefile/workflow and patched Makefile/workflow.
"""
from collections import Counter
from pathlib import Path
import argparse

from flagcheck.schema import _command, extract_argparse
from flagcheck.scanner import scan_text

RECEIVERS = {
    'formatgroup', 'formatoptions', 'help_options', 'htmloptions',
    'input_options', 'pdfoptions', 'plain_options', 'preptooloptions',
    'textoptions', 'v2v3options', 'value_options',
}
EXPECTED = Counter({'--skip-config': 39, '--base': 7, '--prep': 6,
                    '--no-inline-version': 6, '--exp': 5, '--doc': 1, '--man': 1})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ['parser', 'before_make', 'before_workflow', 'after_make', 'after_workflow']:
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    flags, notes = extract_argparse(args.parser.read_text(), RECEIVERS)
    schema = {'xml2rfc': _command({'flags': flags, 'complete': True})}
    before = []
    after = []
    for path, kind, results in [(args.before_make, 'make', before), (args.before_workflow, 'workflow', before),
                                (args.after_make, 'make', after), (args.after_workflow, 'workflow', after)]:
        findings = scan_text(path.read_text(), schema, kind, str(path))
        print(path.name, len(findings), dict(Counter(f.flag for f in findings)))
        results.extend(findings)
    print('Literal flag spellings:', len(flags), 'Extraction notes:', notes)
    print('Before:', len(before), 'After:', len(after))
    assert not notes
    assert all(f.code == 'abbreviation' for f in before)
    assert Counter(f.flag for f in before) == EXPECTED
    assert not after
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
