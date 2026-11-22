# Phase 1 validation — 22 November 2026

## Local execution results

- Runtime: Linux, CPython 3.12.14, PyYAML 6.0.3.
- `PYTHONPATH=src python -m unittest discover -s tests -v`: 40 tests passed.
- `python -m pip wheel --no-deps --no-build-isolation --no-index ... .`: wheel built successfully (`flagcheck-0.1.0-py3-none-any.whl`).
- Installed the wheel into a separate virtual environment with the preinstalled PyYAML dependency available through system site packages, without downloading packages. All 40 tests passed again from the installed package.
- Installed CLI smoke test: `flagcheck --version` returned `0.1.0`; source extraction emitted the expected schema; a deliberately abbreviated option produced one warning and status 1.
- GitHub Actions and pre-commit are configured, not executed. No claim of Python 3.10, 3.11 or 3.13 runtime verification is made.

## Reproducible targeted benchmark

The test uses exact source files retrieved from GitHub, not synthetic clones or guessed flags.

- Base: [ietf-tools/xml2rfc at 8f07f9e](https://github.com/ietf-tools/xml2rfc/tree/8f07f9ec5876bb0fd90f7f686238ed201e52e52f).
- Reviewed patch: [PR #1363](https://github.com/ietf-tools/xml2rfc/pull/1363), [fork commit b7e56f4](https://github.com/aparth9100/xml2rfc/commit/b7e56f49b2b8bd76745490871cc413a2693fc2e4).
- Inputs: base `xml2rfc/run.py`; base and patched `Makefile` and `.github/workflows/pdfa-verification.yml`.
- 98 literal flag spellings extracted from 11 selected parser/argument group receivers, with zero extractor notes. The complete option list was assumed for this pinned benchmark after comparing the literal declarations.

| File | Original findings | Patched findings |
| --- | ---: | ---: |
| Makefile | 64 | 0 |
| PDF/A workflow | 1 | 0 |
| Total | 65 | 0 |

All 65 findings were the seven abbreviations addressed by the PR: `--skip-config` (39), `--base` (7), `--prep` (6), `--no-inline-version` (6), `--exp` (5), `--doc` (1), `--man` (1). No other findings were observed in the supported scan contexts. The three commented examples are intentionally skipped; Make's `$(shell ...)` expressions are not covered. This result does not establish general precision or recall; the original benchmark informed the implementation.

To reproduce locally after separately obtaining the pinned files (they are not redistributed in this bundle):

```sh
python benchmarks/xml2rfc.py run.py before/Makefile before/pdfa-verification.yml after/Makefile after/pdfa-verification.yml
```

The script asserts the exact finding counts and absence of findings in the patched files. It never executes upstream files.

## Next stage

Validate at least two unrelated projects before release. Pin the commits and tool versions, build complete or explicitly partial schemas, compare findings with actual parser semantics, manually classify false positives and missed issues, and publish the reproducible benchmark methodology. Check packaging-name availability and policies before publication. No external repository, issue, PR or package was created during Phase 1.
