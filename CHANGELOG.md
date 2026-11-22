# Changelog

## 0.2.0a2 — second public alpha (22 November 2026)

- Extract positive and generated negative aliases of directly qualified `argparse.BooleanOptionalAction` declarations without importing or executing target code.
- Clarify installation from the verified initial-alpha commit and publish the actual CI evidence.
- Add opt-in function-scoped extraction and automatic discovery of directly assigned argument groups, with unresolved-assignment notes.
- Add pinned Bandit and PyPA Installer schema and scanner benchmarks; record the successful PyPI alpha release.
- Add explicit literal Docker image-to-command mappings, Compose argv scanning, multi-document workflows, and opt-in YAML example scanning.
- Recover 24 of 25 previously manually adapted JMo pilot findings; detect four additional candidates from the same pinned source. PowerShell remains unsupported.

## 0.2.0a1 — first public alpha (22 November 2026)

- Static long-option validation with an explicit, reviewed JSON command schema.
- Non-executing extraction of literal argparse declarations, implicit help and reviewed custom action arities.
- Shell, Makefile, Markdown examples and GitHub Actions run-step support; limited literal project runner forms.
- `--summary` exposes partial coverage counters on stderr; `--require-match` detects a scan in which no configured invocation was recognized.
- JSON output, configurable warning threshold, Python packaging and a pre-commit hook.
- Reproducible, pinned-source benchmark for xml2rfc and three unrelated CLI projects. Results are bounded checks, not claims of universal accuracy.

Known limitations are listed in the README. No automated fixes, network requests, execution of scanned commands or arbitrary CLI semantics are claimed.
