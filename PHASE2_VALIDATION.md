# Flagcheck 0.2.0 — Phase 2 validation (22 November 2026)

## Executive result

Three unrelated open-source argparse CLIs were evaluated. Flagcheck discovered weaknesses in its own extractor and scanner, corrected those weaknesses, and preserved the original xml2rfc result. No upstream change, repository creation, publication, download count or adoption is claimed.

| Project | Reviewed flag spellings | Long options | Unchanged files | Deliberately modified real option tokens detected |
| --- | ---: | ---: | ---: | ---: |
| PyPA Build | 27 | 17 | 8 | 1/1 |
| pip-audit | 36 | 26 | 7 | 11/11 |
| Microsoft MarkItDown | 28 | 19 | 3 | 12/12 |
| Total | 91 | 62 | 18 | 24/24 |

No findings on the 18 unmodified files. The 24 manually enumerated exact long-option occurrences in supported README contexts were individually replaced with an invented invalid spelling; all were reported on the expected line. These were controlled local mutations, not actual upstream bugs. The remainder of each file was unchanged for every mutation. This only establishes coverage for those 24 reviewed occurrences; unsupported shell constructs, commands and unenumerated examples may be skipped.

## Changes made after Phase 1

- Fixed a false warning on pip-audit's legitimate `--help`: direct argparse constructors implicitly add help unless disabled. Manual confirmation is supported for indirect constructors.
- PyPA Build's custom `NegativeCountAction` could not be extracted automatically. Added an explicit, reviewer-provided arity mapping; no custom code is executed. Verified its `nargs=0` in the pinned source.
- Handle simple optional option arguments, known short-option clusters and attached values; do not lint unknown short flags.
- Recognize literal `pipenv run`, `uv run` and `uvx --from PACKAGE COMMAND` forms; arbitrary wrapper arguments are not parsed.
- Fixed a path filter that mistakenly skipped explicitly requested files located below a directory named `build`.
- Added 12 regression tests (52 total, versus 40 in Phase 1).

## Option spelling oracle

The three inventories were manually transcribed from their parser declarations, including implicit help and the reviewed Build custom action. The extraction result was asserted equal to each inventory, including option arity. Separately, standard Python `argparse` parsers with these known long option names resolved exact names, all proper long-name prefixes, and invented unknown names. Those parsers deliberately model name-resolution only, using boolean actions to isolate spelling behavior; they do not model actual package side effects, value validation or mutual constraints. Each case was evaluated in shell, Makefile, Markdown, and workflow contexts, including both Build invocation aliases.

| Expected class | Cases | Correct |
| --- | ---: | ---: |
| Exact / clean | 316 | 316 |
| Unique abbreviation | 2,188 | 2,188 |
| Ambiguous abbreviation | 260 | 260 |
| Unknown | 316 | 316 |
| Total | 3,080 | 3,080 |

Observed false positives: 0 among 316 clean synthetic cases. Observed missed findings: 0 among 2,764 positive synthetic cases. These are systematic, generated test cases with known labels, **not 3,080 independently discovered real bugs or a population-level accuracy estimate**. Phase 2 files were also used to improve the implementation, so the result is not a held-out benchmark. The original Phase 1 regression remained 65 before / 0 after.

## Reproducibility

Working copies of upstream inputs are not redistributed. Obtain the named files from the following exact commits; put the source in `cli.py` and the root README in `README.md` under each local dataset subdirectory. Preserve `.github/workflows/` paths. No upstream code is imported, installed, run or modified by the benchmark.

| Dataset directory | Pinned commit | Parser path |
| --- | --- | --- |
| `build` | [pypa/build@c0b4f18](https://github.com/pypa/build/tree/c0b4f18acc16971d9856a273cd1ddd2233de9774) | `src/build/__main__.py` |
| `audit` | [pypa/pip-audit@864264b](https://github.com/pypa/pip-audit/tree/864264baeb9a9e30115a0f2838fe4769cf5a0840) | `pip_audit/_cli.py` |
| `markitdown` | [microsoft/markitdown@ed17895](https://github.com/microsoft/markitdown/tree/ed178952a6672abdfd35b5f9e76a80b6cefc086e) | `packages/markitdown/src/markitdown/__main__.py` |

Workflow filenames are listed in `benchmarks/independent.py` and form an explicit 15-file manifest (7 Build, 6 pip-audit, 2 MarkItDown). Three README files complete the 18 natural scan inputs. Run from the Flagcheck package root after installation:

```sh
python benchmarks/independent.py /path/to/dataset
```

The benchmark asserts completeness of the manual option inventories, all expected inputs, exact mutation locations, natural findings, and generated classifications. A mismatch exits nonzero. For the earlier regression, use `benchmarks/xml2rfc.py` as documented in `VALIDATION.md`.

## Release gate

Verified locally on Linux, Python 3.12.14, PyYAML 6.0.3: the 0.2.0 wheel built offline using the existing build dependencies, installed into a separate virtual environment with system site packages providing PyYAML, reported version `0.2.0`, passed all 52 unit tests, and reproduced both benchmarks from the installed package. CI and the pre-commit hook are configured but have not been run on GitHub; Python 3.10, 3.11 and 3.13 were not exercised in this environment.

The project is a credible alpha, not a production-ready universal shell linter. Before publishing, review existing competing tools and distribution-name availability; validate additional held-out projects, especially those with complex commands; check support for Python versions declared in CI; ask maintainers or developers for real usability feedback. General OSS program eligibility is not established by these local results alone.
