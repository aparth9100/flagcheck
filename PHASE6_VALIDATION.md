# Phase 6 — scoped extraction and adoption readiness

The first public alpha, `0.2.0a1`, was published on 22 November 2026 via the protected PyPI trusted-publishing workflow. Its tag points to `0ebd42df3ef5e311f754f141c9babca1e2574b8b`; [the build and publishing job](https://github.com/aparth9100/flagcheck/actions/runs/45020748186) succeeded. The development work below does not modify that release or upload another distribution.

## Extractor usability

`--scope FUNCTION --discover-groups --receiver parser` replaces manual enumeration of literal, uniquely assigned argparse argument groups in a named module-level function. Discovery traverses nested argument-group assignments, not nested Python scopes. It never executes the target. Ambiguous bindings or unassigned group calls generate review notes. Scope selection does not imply a complete parser: dynamic arguments, helpers, aliases and runtime behavior still require review.

| Dataset | Reviewed spellings | Explicit group receivers previously required | New explicit receivers |
| --- | ---: | ---: | ---: |
| PyPA Build | 27 | 7 | 1 |
| pip-audit | 36 | 2 | 1 |
| Microsoft MarkItDown | 28 | 2 | 1 |

The updated Phase 2 benchmark matched all 91 spellings, with the existing reviewer-confirmed custom-action arity for Build. It reproduced 18 clean unmodified files, 24/24 detected deliberate README mutations, and 3,080/3,080 generated argparse name-resolution checks.

Local verification on Python 3.12.14: 65 unit tests passed, an offline wheel and source distribution built successfully, and the installed development wheel passed all 65 tests and both multi-project benchmarks with PyYAML 6.0.3. The original xml2rfc regression remained 65 findings before the patch and zero afterward.

## Additional held-out project sources

| Project | Reviewed option spellings | Result |
| --- | ---: | --- |
| [Bandit](https://github.com/PyCQA/bandit/tree/2d5467c45c3189f4d7d07e8022276bc73a478abd) | 42 | Exact inventory match, including three mutually exclusive groups |
| [PyPA Installer](https://github.com/pypa/installer/tree/d8b9c446604811a3e3e3b2eec6d0223f51cd867a) | 10 | Exact inventory match |

The new benchmark exercises 1,144 generated name checks across shell, Makefile, Markdown, and workflow contexts, all matching the independent argparse spelling oracle. Eleven **manually selected literal shell snippets** from Bandit's reStructuredText docs were recognized with no findings. The scanner does not support RST directly; this checks only the extracted commands. One intentionally altered real long option (`--ini`) was detected. These are bounded validation results, not discovered upstream bugs, usage statistics or third-party endorsement.

## Reproduction

Obtain the following files at the exact commits above, with no modifications. Save them inside a local dataset directory:

| Local path | Upstream path |
| --- | --- |
| `bandit/cli.py` | `bandit/cli/main.py` |
| `bandit/start.rst` | `doc/source/start.rst` |
| `bandit/config.rst` | `doc/source/config.rst` |
| `installer/cli.py` | `src/installer/__main__.py` |

Run the suite from the repository root, using an installed development package:

```sh
python -m unittest discover -s tests -v
python benchmarks/independent.py /path/to/phase2-dataset
python benchmarks/scoped.py /path/to/phase6-dataset
```

## Pilot plan

Start with a developer who owns an argparse CLI and its CI/docs. Generate a schema in review-only mode, compare the inventory against their actual parser, then run on their repository without committing the schema or changing CI. Record supported commands, recognized invocations, real findings, false positives, time spent reviewing, and whether the developer requests a follow-up. Only propose a hook installation when the owner explicitly opts in. Never create unsolicited pull requests, manufacture downloads or contributor counts, or claim synthetic tests as real adoption.

No external pilot, feedback, merged upstream contribution or Claude program eligibility is claimed here.
