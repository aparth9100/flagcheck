# Flagcheck — CLI option drift linter

**0.2.0a1 — experimental alpha.**

Flagcheck detects brittle long-option abbreviations, unknown long options, and explicitly marked deprecated options in static shell commands. It checks against a schema you review, not against a guessed universal list of CLI flags.

It is intended for maintainers who control a CLI and want their own Makefile, CI and documentation examples to use stable option names. The scanner never runs a scanned command, imports a target package or makes network requests.

## Quick start

Python 3.10+ and PyYAML are required. Install from this source directory:

```sh
python -m pip install .
```

After the alpha is available on PyPI, the equivalent registry installation is `python -m pip install --pre flagcheck`.

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

The command emits JSON to stdout. Save it into a schema file after inspecting it. Repeat `--receiver` for explicitly identified argument groups. The AST extractor recognizes literal `add_argument` declarations, aliases, common actions, value counts and literal deprecation metadata. It never imports the Python file. It recognizes default `-h`/`--help` in a direct `argparse.ArgumentParser` constructor unless disabled; use `--implicit-help` only after verifying an indirect constructor. For a custom action whose arity you have reviewed, specify, for example, `--action-arity NegativeCountAction=0`. For parsers with abbreviation disabled, pass `--no-abbrev`. It cannot infer dynamically constructed arguments, inherited parsers, plugin options or arbitrary runtime behavior. It combines conditional declarations. Only use `--complete` when you have independently verified the parser's complete option inventory; omissions could cause incorrect reports.

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

The test suite uses the standard library `unittest`. The included CI workflow targets Python 3.10–3.13 but has not been run on GitHub. The pre-commit hook is configured but is not publicly installable yet. When a repository and release tag exist, configure the hook with `args: [--schema, path/to/schema.json]`. For now you can invoke the CLI directly or use a local pre-commit hook passing that schema.

## Evidence and next milestone

See `VALIDATION.md` for the original xml2rfc benchmark and `PHASE2_VALIDATION.md` for validation against PyPA Build, pip-audit and Microsoft MarkItDown. The Phase 2 measurements cover reviewed literal option inventories, original files, deliberate mutations and a Python argparse option-resolution oracle. They are not a general-accuracy claim or independent external adoption evidence. The next milestone is review of a release candidate, check for existing similar tools and distribution-name availability, and decide whether to release. The distribution name is provisional; registry availability is not verified.

MIT licensed; source, docs and tests prepared with AI assistance for human review. No publication or external adoption is claimed.
