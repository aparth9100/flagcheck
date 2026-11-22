# Flagcheck — CLI option drift linter

**0.2.0a2.dev0 — next-alpha development build.**

Flagcheck detects brittle long-option abbreviations, unknown long options, and explicitly marked deprecated options in static shell commands. It checks against a schema you review, not against a guessed universal list of CLI flags.

It is intended for maintainers who control a CLI and want their own Makefile, CI and documentation examples to use stable option names. The scanner never runs a scanned command, imports a target package or makes network requests.

## Quick start

Python 3.10+ and PyYAML are required. Install from this source directory:

```sh
python -m pip install .
```

To try the verified first-alpha source directly without cloning, use its pinned Git commit:

```sh
python -m pip install "git+https://github.com/aparth9100/flagcheck.git@0ebd42df3ef5e311f754f141c9babca1e2574b8b"
```

The verified first alpha is now [available on PyPI](https://pypi.org/project/flagcheck/0.2.0a1/). Install that exact release with `python -m pip install flagcheck==0.2.0a1`. The scoped group discovery described below is a development feature, not part of that published alpha.

Use the included example schema:

```sh
flagcheck scan --schema examples/schema.json --cmd 'mytool --verb --output result.txt'
```

Expected output: a warning suggesting `--verbose`. The command exits with code 1 because the default threshold includes warnings.

```sh
flagcheck scan --schema examples/schema.json --format json --summary --require-match examples/sample.sh
```

Exit codes: 0 = no finding at the selected severity; 1 = finding; 2 = input/configuration error. `--fail-on error` permits warnings without failing CI. An exit code of 0 is **not** proof that all commands are valid.

`--summary` writes JSON counters to stderr, keeping findings-only JSON on stdout intact. It reports supported logical commands, recognized invocations, checked long options, lexical failures, unmatched segments and invocations whose scanning stopped early. It is partial coverage, not a measure of all unsupported syntax. `--require-match` returns status 2 when no configured command was recognized; use it on a specific file or path expected to invoke your CLI.

## Generate a schema from source

```sh
flagcheck schema-from-source examples/cli_example.py --command mytool --receiver parser --complete
```

The command emits JSON to stdout. Save it into a schema file after inspecting it. Repeat `--receiver` for explicitly identified argument groups. The AST extractor recognizes literal `add_argument` declarations, aliases, common actions, value counts and literal deprecation metadata. It never imports the Python file. It recognizes default `-h`/`--help` in a direct `argparse.ArgumentParser` constructor unless disabled; use `--implicit-help` only after verifying an indirect constructor. A directly qualified `argparse.BooleanOptionalAction` with positive long options generates their `--no-...` aliases; already-negative declarations or unqualified action names require review. For a custom action whose arity you have reviewed, specify, for example, `--action-arity NegativeCountAction=0`. For parsers with abbreviation disabled, pass `--no-abbrev`. It cannot infer dynamically constructed arguments, inherited parsers, plugin options or arbitrary runtime behavior. It combines conditional declarations. Only use `--complete` when you have independently verified the parser's complete option inventory; omissions could cause incorrect reports.

For a parser constructed inside a module-level function, select that function and automatically follow direct, uniquely assigned argument groups:

```sh
flagcheck schema-from-source path/to/cli.py --command mytool --receiver parser --scope create_parser --discover-groups
```

`--scope` excludes nested functions, classes and comprehensions from extraction. `--discover-groups` follows direct `add_argument_group` and `add_mutually_exclusive_group` assignments, including nested groups. It requires an explicit scope and reports unresolved group assignments for review rather than assuming their contents. This is not general Python dataflow analysis: aliases, dynamic declarations, helper calls, nested scopes, reassignment and runtime behavior may require manual inspection. The schema remains incomplete by default; add `--complete` only after reviewing the full parser inventory and all notes.

An example schema:

```json
{
  "mytool": {
    "complete": true,
    "allow_abbrev": true,
    "flags": {
      "--verbose": {"nargs": 0},
      "--output": {"nargs": 1},
      "--legacy": {"nargs": 0, "deprecated": true, "replacement": "--verbose"}
    }
  }
}
```

Each command can also specify `subcommands`, a mapping of subcommand names to command-schema objects. A subcommand has its own options, with no implicit inheritance. `complete` defaults to false: incomplete schemas only report explicitly known deprecated flags and stop at unrecognized options. `allow_abbrev` controls whether a unique prefix is a warning or an invalid-option error. `nargs` supports nonnegative integer counts and `?`, `*`, `+`, `...`; optional values are consumed when statically recognizable, and the scanner stops after variadic options rather than guessing their extent.

## Supported input

- Shell scripts (`.sh`, `.bash`, `.zsh`): simple literal command lines, common wrappers, chains, pipelines and backslash continuations. Limited literal `pipenv run`, `uv run` and `uvx [--from PACKAGE] COMMAND` forms are recognized.
- Makefiles and `.mk`: tab-prefixed recipes, simple loops, continued lines, literal `bash -c`/`-cx` wrappers, automatic filename variables.
- GitHub Actions workflows: `jobs.*.steps.*.run` scalar values for explicit `bash`/`sh` or default Ubuntu/macOS runners; literal multiline blocks.
- Markdown: explicitly shell-tagged fenced snippets; console fences with `$ ` prompts.

The scanner intentionally skips unsupported formats, unrecognized commands and ambiguous dynamic arguments. It is not a shell parser, a CLI semantic validator, or a substitute for actual CI. It consumes recognized argparse-style short-option clusters and attached values to avoid false long-option matches, but does not lint short option spellings. It does not support custom Make recipe prefixes, arbitrary Make `$(shell ...)` expansions, folded YAML blocks, PowerShell, fish, shell functions, aliases, dynamically constructed commands or all possible nested shell syntax. A finding's line refers to the beginning of the logical command; it can be the first line of a continuation. Treat results as review prompts, not automatic edits.

## Testing

```sh
python -m unittest discover -s tests -v
```

The test suite uses the standard library `unittest`. The [initial alpha CI](https://github.com/aparth9100/flagcheck/actions/runs/45015271703) passed on Linux with Python 3.10–3.13 and on Windows and macOS with Python 3.12. To try the pre-commit hook from the pinned initial alpha commit, configure it as follows (replace the example schema path with your reviewed schema):

```yaml
repos:
  - repo: https://github.com/aparth9100/flagcheck
    rev: 0ebd42df3ef5e311f754f141c9babca1e2574b8b
    hooks:
      - id: flagcheck
        args: [--schema, path/to/schema.json]
```

## Evidence and next milestone

See `VALIDATION.md` for the original xml2rfc benchmark, `PHASE2_VALIDATION.md` for validation against PyPA Build, pip-audit and Microsoft MarkItDown, and `PHASE6_VALIDATION.md` for the scoped extractor checks against Bandit and PyPA Installer. These measurements cover reviewed literal option inventories, selected original files or snippets, deliberate mutations and a Python argparse option-resolution oracle. They are not a general-accuracy claim or independent external adoption evidence. The next milestone is feedback from a real, opt-in pilot integration. The first registry release passed its [build and publish workflow](https://github.com/aparth9100/flagcheck/actions/runs/45020748186).

MIT licensed; source, docs and tests prepared with AI assistance for human review. The source is public; no external adoption is claimed.

## Try a pilot in your own CLI project

Flagcheck's own development CI checks the documented commands using a reviewed
schema. It also tests that the schema agrees with the literal parser declarations.
Try the same self-check from a checkout of this development branch:

```sh
flagcheck scan --schema examples/flagcheck-schema.json --summary --require-match README.md PILOT.md .github/workflows/ci.yml
```

For an opt-in pilot in another project, start with the released alpha and one file
that contains real CLI examples. See [PILOT.md](PILOT.md) for a small, reversible
trial and how to report false positives or missed options. Self-use and benchmark
results are not independent adoption.
