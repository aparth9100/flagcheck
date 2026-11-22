import json
import io
import shlex
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from flagcheck.cli import main
from flagcheck.schema import extract_argparse, load_schema
from flagcheck.scanner import ScanStats, scan_text


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'examples/flagcheck-schema.json'


class SelfCheckTests(unittest.TestCase):
    def test_reviewed_schema_matches_cli_declarations(self):
        source = (ROOT / 'src/flagcheck/cli.py').read_text(encoding='utf-8')
        schema = json.loads(SCHEMA.read_text(encoding='utf-8'))['flagcheck']
        for receiver, spec in [('parser', schema),
                               ('scan', schema['subcommands']['scan']),
                               ('gen', schema['subcommands']['schema-from-source'])]:
            with self.subTest(receiver=receiver):
                flags, notes = extract_argparse(source, {receiver}, scope='main',
                                                implicit_help=receiver != 'parser')
                self.assertEqual(notes, [])
                self.assertEqual(flags, spec['flags'])
                self.assertTrue(spec['complete'])
                self.assertFalse(spec['allow_abbrev'])

    def test_documented_commands_and_mutation(self):
        schema = load_schema(SCHEMA)
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        stats = ScanStats()
        self.assertEqual([], scan_text(readme, schema, 'markdown', stats=stats))
        self.assertGreater(stats.matched_invocations, 0)
        self.assertGreater(stats.checked_long_options, 0)
        mutated = readme.replace('flagcheck scan --schema ', 'flagcheck scan --schem ', 1)
        self.assertNotEqual(readme, mutated)
        finding, = scan_text(mutated, schema, 'markdown')
        self.assertEqual((finding.code, finding.flag, finding.suggestion),
                         ('unknown', '--schem', '--schema'))

    def test_ci_step_is_scanned(self):
        schema = load_schema(SCHEMA)
        workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        stats = ScanStats()
        self.assertEqual([], scan_text(workflow, schema, 'workflow', stats=stats))
        self.assertGreater(stats.checked_long_options, 0)

    def test_documented_docker_example_runs_against_example_schema(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        example, = (line for line in readme.splitlines()
                    if line.startswith('flagcheck scan --schema examples/schema.json --docker-image '))
        argv = shlex.split(example)[1:]
        argv[argv.index('--schema') + 1] = str(ROOT / 'examples/schema.json')
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(1, main([*argv, '--format', 'json']))
        finding, = json.loads(output.getvalue())
        self.assertEqual((finding['command'], finding['flag'], finding['suggestion']),
                         ('mytool', '--verb', '--verbose'))
