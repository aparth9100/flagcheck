"""Read-only pilot on pinned JMo docs. Never import or run JMo or Docker.

Usage: PYTHONPATH=src python benchmarks/pilot_jmo.py /path/to/jmo-checkout
The reviewed line numbers deliberately target the commit stated in PHASE8_PILOT.md.
"""
import json
import shlex
import sys
from dataclasses import asdict
from pathlib import Path

from flagcheck.scanner import ScanStats, scan_command, scan_text
from flagcheck.schema import Command, Flag, extract_argparse, load_schema


def build_schema(root):
    source = (root / 'scripts/cli/jmo.py').read_text(encoding='utf-8')
    root_flags, notes = extract_argparse(source, {'ap'}, scope='build_parser')
    assert not notes, notes
    flags = {}
    for scope, receivers, groups in [
        ('_add_target_args', {'parser', 'g'}, False),
        ('_add_scan_config_args', {'parser'}, True),
        ('_add_logging_args', {'parser'}, False),
        ('_add_scan_args', {'sp'}, True),
    ]:
        extracted, notes = extract_argparse(source, receivers, scope=scope,
            discover_groups=groups, implicit_help=scope == '_add_scan_args')
        if scope == '_add_scan_config_args':
            assert len(notes) == 2 and all('_ToolNamesAction' in n for n in notes), notes
            # The custom action's token arity is explicitly declared as nargs='*'.
            extracted.update({'--tools': {'nargs': '*'}, '--skip-tools': {'nargs': '*'}})
        else:
            assert not notes, notes
        flags.update(extracted)
    assert len(flags) == 39 and '--results-dir' in flags and '--results' not in flags
    return {'jmo': Command({k: Flag(**v) for k, v in root_flags.items()},
        {'scan': Command({k: Flag(**v) for k, v in flags.items()}, complete=True)},
        complete=True)}


MARKDOWN = ('README.md', 'QUICKSTART.md', 'docs/DOCKER_README.md', 'docs/FAQ.md',
            'docs/SAMPLE_OUTPUTS.md', 'docs/VERSION_MANAGEMENT.md',
            'docs/examples/wizard-examples.md', 'docs/examples/attestation-workflows.md')

# Manually reviewed, literal scan argv excerpts in unsupported contexts:
# Docker image commands, YAML examples in Markdown, multi-document workflow
# examples. This is NOT automated Docker/Compose/YAML-block recognition.
EXCERPTS = {
    'docs/DOCKER_README.md': (309, 318, 328, 505, 585, 625, 638, 1144, 1161, 1207, 1219),
    'docs/VERSION_MANAGEMENT.md': (601,),
    'docs/examples/wizard-examples.md': (534,),
    'docs/examples/attestation-workflows.md': (50, 306, 333, 393, 666),
    'docs/examples/github-actions-docker.yml': (29, 102, 158, 289, 301),
}


def main(root):
    schema = build_schema(root)
    assert schema == load_schema(Path(__file__).resolve().parents[1] / 'examples/jmo-scan-pilot.json')
    stats = ScanStats()
    native = []
    for path in MARKDOWN:
        native.extend(scan_text((root / path).read_text(encoding='utf-8'), schema,
                                'markdown', path, stats=stats))
    assert {(f.source, f.line, f.flag) for f in native} == {
        ('docs/FAQ.md', 63, '--iac'), ('docs/FAQ.md', 72, '--k8s'),
        ('docs/SAMPLE_OUTPUTS.md', 13, '--results'),
    }
    assert not scan_command('jmo scan --repo . --results-dir results', schema)
    assert not scan_command('jmo ci --profile', schema)  # out of scope, not an error
    adapted = []
    for path, numbers in EXCERPTS.items():
        lines = (root / path).read_text(encoding='utf-8').splitlines()
        for number in numbers:
            raw = lines[number-1].strip()
            # Only the scan argv is mapped, with the image entrypoint verified.
            if raw.startswith('jmo scan '):
                command = raw
            elif raw.startswith('scan '):
                command = 'jmo ' + raw
            else:
                assert 'jmo-security:latest scan ' in raw, (path, number, raw)
                command = 'jmo scan ' + raw.split('jmo-security:latest scan ', 1)[1]
            findings = scan_command(command, schema, path, number)
            assert findings, (path, number)
            adapted.extend(findings)
            if all(f.code == 'abbreviation' for f in findings):
                fixed = command.replace('--results ', '--results-dir ')
                assert not scan_command(fixed, schema), (path, number)

    # Read only two reviewed literal Compose argv lists. CI is another parser.
    import yaml
    path = 'docker-compose.yml'
    compose = yaml.safe_load((root / path).read_text(encoding='utf-8'))
    for service, number in [('jmo-scan', 19), ('jmo-scheduled', 65)]:
        spec = compose['services'][service]
        assert spec['image'] == 'ghcr.io/jimmy058910/jmo-security:latest'
        assert 'entrypoint' not in spec and spec['command'][0] == 'scan'
        cmd = shlex.join(['jmo', *spec['command']])
        findings = scan_command(cmd, schema, path, number)
        assert len(findings) == 1 and findings[0].suggestion == '--results-dir'
        adapted.extend(findings)
        assert not scan_command(cmd.replace('--results ', '--results-dir '), schema)

    print(json.dumps({'native_coverage': asdict(stats),
                      'native_findings': [asdict(f) for f in native],
                      'adapted_findings': [asdict(f) for f in adapted]}, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
