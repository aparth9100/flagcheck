import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from flagcheck.cli import main
from flagcheck.schema import Command, Flag, extract_argparse, load_schema
from flagcheck.scanner import ScanStats, scan_command, scan_text


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.schema = {"tool": Command({"--verbose": Flag(), "--version": Flag(), "--output": Flag(1),
                                        "--old": Flag(deprecated=True, replacement="--verbose"),
                                        "-o": Flag(1), "--many": Flag("+")}, complete=True)}

    def scan(self, command):
        return scan_command(command, self.schema)

    def test_exact(self):
        self.assertEqual([], self.scan("tool --verbose --output file"))

    def test_abbreviation(self):
        f, = self.scan("tool --verbos")
        self.assertEqual((f.code, f.suggestion), ("abbreviation", "--verbose"))

    def test_ambiguous(self):
        f, = self.scan("tool --ver")
        self.assertEqual(f.code, "ambiguous")

    def test_unknown(self):
        f, = self.scan("tool --bogus")
        self.assertEqual(f.code, "unknown")

    def test_deprecated(self):
        f, = self.scan("tool --old")
        self.assertEqual((f.code, f.suggestion), ("deprecated", "--verbose"))

    def test_no_abbrev(self):
        self.assertEqual("unknown", scan_command("tool --verb", {"tool": Command(self.schema["tool"].flags, complete=True, allow_abbrev=False)})[0].code)

    def test_partial(self):
        self.assertEqual([], scan_command("tool --verb", {"tool": Command(self.schema["tool"].flags)}))

    def test_end_options(self):
        self.assertEqual([], self.scan("tool -- --bogus"))

    def test_value_is_not_option(self):
        self.assertEqual([], self.scan("tool --output '--bogus' --verbose"))

    def test_short_value(self):
        self.assertEqual([], self.scan("tool -o --bogus --verbose"))

    def test_unknown_short_is_conservative(self):
        self.assertEqual([], self.scan("tool -z --bogus"))

    def test_inline_dynamic_value(self):
        self.assertEqual([], self.scan('tool --output="$DIR/file" --verbose'))

    def test_dynamic_argument(self):
        self.assertEqual([], self.scan("tool $FLAGS --bogus"))

    def test_dynamic_option(self):
        self.assertEqual([], self.scan("tool --${FLAG}"))

    def test_variadic(self):
        self.assertEqual([], self.scan("tool --many a --bogus"))

    def test_optional_value_followed_by_flag(self):
        schema = {"tool": Command({"--desc": Flag("?"), "--verbose": Flag()}, complete=True)}
        for cmd in ("tool --desc --verb", "tool --desc on --verb", "tool --desc=on --verb"):
            self.assertEqual(["--verb"], [f.flag for f in scan_command(cmd, schema)])

    def test_optional_dynamic_value_conservative(self):
        schema = {"tool": Command({"--desc": Flag("?"), "--verbose": Flag()}, complete=True)}
        self.assertEqual([], scan_command("tool --desc $MODE --bogus", schema))

    def test_known_short_cluster_and_attached_value(self):
        schema = {"tool": Command({"-v": Flag(), "-o": Flag(1), "--verbose": Flag()}, complete=True)}
        for cmd in ("tool -vv --verb", "tool -vofile --verb", "tool -vo file --verb"):
            self.assertEqual(["--verb"], [f.flag for f in scan_command(cmd, schema)])

    def test_exact_multichar_short_has_priority(self):
        schema = {"tool": Command({"-vv": Flag(1), "-v": Flag(), "--verbose": Flag()}, complete=True)}
        self.assertEqual([], scan_command("tool -vv --verb", schema))

    def test_chained(self):
        self.assertEqual(["--verb", "--old"], [f.flag for f in self.scan("tool --verb && tool --old")])

    def test_quoted_operator(self):
        self.assertEqual([], self.scan("echo '&&' tool --bogus"))

    def test_comments(self):
        self.assertEqual([], self.scan("tool --verbose # --bogus"))

    def test_single_quoted_literal(self):
        self.assertEqual([], self.scan("tool '$NOT_A_FLAG' --verbose"))

    def test_unbalanced_quote(self):
        self.assertEqual([], self.scan("tool --unknown '"))

    def test_shell_wrapper(self):
        self.assertEqual(["--verb"], [f.flag for f in self.scan('PS4=" " /bin/bash -cx "tool --verb --output \\"$DIR\\""')])

    def test_python_module(self):
        self.assertEqual("abbreviation", self.scan("python3 -m tool --verb")[0].code)

    def test_literal_project_runners(self):
        for command in ("pipenv run tool --verb", "uv run tool --verb", "uvx --from package tool --verb", "uvx tool --verb"):
            self.assertEqual(["--verb"], [f.flag for f in self.scan(command)])

    def test_unknown_project_runner_options(self):
        self.assertEqual([], self.scan("uvx --unknown tool --bogus"))

    def test_unknown_command(self):
        self.assertEqual([], self.scan("unrelated tool --bogus"))

    def test_summary_partial_coverage(self):
        stats = ScanStats()
        findings = scan_text("tool --verbose\necho hi\ntool --verb $FLAGS\ntool 'unclosed", self.schema, stats=stats)
        self.assertEqual(1, len(findings))
        self.assertEqual((3, 2, 1, 2, 1, 1), (stats.logical_commands, stats.matched_invocations, stats.unmatched_segments, stats.checked_long_options, stats.lexer_failures, stats.incomplete_invocations))

    def test_subcommands(self):
        schema = {"tool": Command({"--global": Flag()}, {"run": Command({"--fast": Flag()}, complete=True)}, complete=True)}
        f, = scan_command("tool --global run --fas", schema)
        self.assertEqual(("tool run", "--fast"), (f.command, f.suggestion))
        self.assertEqual([], scan_command("tool unknown --bogus", schema))

    def test_make_recipe(self):
        fs = scan_text("VAR = tool --bogus\nall:\n\t@tool --verb \\\n\t  --output file\n# tool --bogus", self.schema, "make")
        self.assertEqual([(3, "--verb")], [(f.line, f.flag) for f in fs])

    def test_make_automatic_var(self):
        self.assertEqual(["--verb"], [f.flag for f in scan_text("all:\n\t@tool $< --verb", self.schema, "make")])

    def test_make_loop(self):
        self.assertEqual(["--verb"], [f.flag for f in scan_text("all:\n\tfor x in *.xml; do tool --verb $$x; done", self.schema, "make")])

    def test_make_continuation_without_tab(self):
        self.assertEqual(["--verb"], [f.flag for f in scan_text("all:\n\ttool \\\n --verb\n", self.schema, "make")])

    def test_markdown(self):
        doc = "```python\ntool --bogus\n```\nText tool --bogus\n~~~bash\n$ tool --verb\n~~~\n"
        self.assertEqual([(6, "--verb")], [(f.line, f.flag) for f in scan_text(doc, self.schema, "markdown")])

    def test_yaml(self):
        doc = "jobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          tool --verb\n          tool --verbose\n      - run: 'tool --old'\n      - run: tool --bogus\n        shell: pwsh\n"
        self.assertEqual([(6, "--verb"), (8, "--old")], [(f.line, f.flag) for f in scan_text(doc, self.schema, "workflow")])

    def test_workflow_windows_default(self):
        self.assertEqual([], scan_text("jobs:\n  test:\n    runs-on: windows-latest\n    steps:\n      - run: tool --bogus\n", self.schema, "workflow"))

    def test_heredoc_payload_not_commands(self):
        self.assertEqual(["--verb"], [f.flag for f in scan_text("cat <<EOF\ntool --bogus\nEOF\ntool --verb", self.schema)])

    def test_console_output_not_commands(self):
        self.assertEqual(["--verb"], [f.flag for f in scan_text("```console\n$ tool --verb\ntool --bogus\n```", self.schema, "markdown")])

    def test_workflow_ignores_non_job_run(self):
        self.assertEqual([], scan_text("run: tool --bogus", self.schema, "workflow"))


class SchemaAndCLITests(unittest.TestCase):
    def test_static_extraction(self):
        flags, notes = extract_argparse("p.add_argument('-v','--verbose',action='store_true')\np.add_argument('--output')\nq.add_argument('--ignored')", {"p"})
        self.assertEqual({"-v": {"nargs": 0}, "--verbose": {"nargs": 0}, "--output": {"nargs": 1}}, flags)
        self.assertEqual([], notes)

    def test_implicit_help(self):
        flags, notes = extract_argparse("p = argparse.ArgumentParser()\np.add_argument('--foo')", {"p"})
        self.assertEqual({"-h", "--help", "--foo"}, set(flags))
        self.assertEqual([], notes)

    def test_disabled_help(self):
        flags, _ = extract_argparse("p = argparse.ArgumentParser(add_help=False)\np.add_argument('--foo')", {"p"})
        self.assertEqual({"--foo"}, set(flags))

    def test_factory_help_explicit(self):
        flags, _ = extract_argparse("p = factory()\np.add_argument('--foo')", {"p"}, implicit_help=True)
        self.assertIn("--help", flags)

    def test_custom_action_arity(self):
        source = "p.add_argument('-q','--quiet', action=NegativeCountAction)"
        flags, notes = extract_argparse(source, {"p"})
        self.assertFalse(flags)
        self.assertIn("NegativeCountAction", notes[0])
        flags, notes = extract_argparse(source, {"p"}, action_arities={"NegativeCountAction": 0})
        self.assertEqual({"-q": {"nargs": 0}, "--quiet": {"nargs": 0}}, flags)
        self.assertFalse(notes)

    def test_boolean_optional_action_matches_argparse(self):
        source = "p.add_argument('-c', '--cache', '--cache-enabled', action=argparse.BooleanOptionalAction)"
        flags, notes = extract_argparse(source, {"p"})
        parser = argparse.ArgumentParser(add_help=False)
        action = parser.add_argument('-c', '--cache', '--cache-enabled', action=argparse.BooleanOptionalAction)
        self.assertEqual({name: {"nargs": 0} for name in action.option_strings}, flags)
        self.assertFalse(notes)
        self.assertFalse(parser.parse_args(['--no-cache']).cache)
        self.assertEqual([], scan_command("app --no-cache --cache-enabled", {"app": Command({name: Flag() for name in flags}, complete=True)}))

    def test_boolean_optional_action_negative_declaration_requires_review(self):
        flags, notes = extract_argparse("p.add_argument('--no-cache', action=argparse.BooleanOptionalAction)", {"p"})
        self.assertFalse(flags)
        self.assertIn("requires review", notes[0])

    def test_boolean_optional_action_custom_name_requires_review(self):
        flags, notes = extract_argparse("p.add_argument('--cache', action=BooleanOptionalAction)", {"p"})
        self.assertFalse(flags)
        self.assertIn("unsupported action", notes[0])

    def test_inherited_options_require_review(self):
        _, notes = extract_argparse("p = argparse.ArgumentParser(parents=[parent])\np.add_argument('--foo')", {"p"})
        self.assertIn("inherited", notes[0])

    def test_explicit_file_in_build_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'build'
            root.mkdir()
            f = root / 'README.md'
            f.write_text('```sh\napp --verb\n```')
            schema = root / 'schema.json'
            schema.write_text(json.dumps({"app": {"complete": True, "flags": {"--verbose": {}}}}))
            for path in (f, root):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(1, main(["scan", "--schema", str(schema), str(path)]))

    def test_dynamic_declaration(self):
        flags, notes = extract_argparse("p.add_argument(*some_flags)", {"p"})
        self.assertFalse(flags)
        self.assertEqual(1, len(notes))

    def test_no_code_execution(self):
        flags, _ = extract_argparse("raise RuntimeError('never executed')\np.add_argument('--foo')", {"p"})
        self.assertIn("--foo", flags)

    def test_cli_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text(json.dumps({"app": {"complete": True, "flags": {"--verbose": {}}}}))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["scan", "--schema", str(path), "--cmd", "app --verb", "--format", "json"])
            self.assertEqual(1, code)
            self.assertEqual("abbreviation", json.loads(out.getvalue())[0]["code"])

    def test_cli_summary_does_not_corrupt_findings_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text(json.dumps({"app": {"complete": True, "flags": {"--verbose": {}}}}))
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["scan", "--schema", str(path), "--cmd", "app --verb", "--format", "json", "--summary"])
            self.assertEqual(1, code)
            self.assertEqual("abbreviation", json.loads(out.getvalue())[0]["code"])
            self.assertEqual(1, json.loads(err.getvalue())["checked_long_options"])

    def test_require_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text('{"app": {"flags": {}}}')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, main(["scan", "--schema", str(path), "--cmd", "echo nothing", "--require-match"]))

    def test_invalid_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text('{"x": {"complete": "yes"}}')
            with self.assertRaises(ValueError):
                load_schema(path)

    def test_cli_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text('{"x": {"flags": {}}}')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, main(["scan", "--schema", str(path), str(Path(tmp)/"missing")]))
