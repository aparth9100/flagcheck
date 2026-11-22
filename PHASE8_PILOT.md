# External read-only pilot: JMo Security and JUnit2Context

22 November 2026. AI-assisted, maintainer review pending. These are independent
codebases evaluated by the Flagcheck developer, **not external adopters**.
No upstream repositories or issues were modified and no project commands,
Docker containers, scanners, or network targets were executed.

## JMo Security — a documented need

The maintainership issue [#1050](https://github.com/jimmy058910/jmo-security-repo/issues/1050)
and its October 24 update establish a real need to distinguish abbreviated and
invalid `jmo scan` options from legitimate options on other subcommands. The
source was retrieved at commit
[`8628e5ccda3a783e2b8aca033f9869a9eac6480f`](https://github.com/jimmy058910/jmo-security-repo/tree/8628e5ccda3a783e2b8aca033f9869a9eac6480f).

### Method and scope

Review `build_parser`, `_add_scan_args`, `_add_target_args`,
`_add_scan_config_args`, and `_add_logging_args` in `scripts/cli/jmo.py`.
The development extractor yields the root option inventory and 37 scan spellings;
two custom action options, `--tools` and `--skip-tools`, are manually reviewed
as variadic (`nargs='*'`). The complete *scan* schema contains 39 spellings
including help. Other subcommands are out of scope. The root and scan parsers
use argparse's default abbreviation behavior; an obsolete `--profile` on scan
must not be conflated with the valid `--profile` on ci or report.

`examples/jmo-scan-pilot.json` is compatible with the published first alpha.
In a pinned JMo checkout after copying that reviewed schema locally:

```sh
python -m pip install flagcheck==0.2.0a1
flagcheck scan --schema jmo-scan-pilot.json --summary --require-match docs/FAQ.md docs/SAMPLE_OUTPUTS.md
```

Verified with installed 0.2.0a1: three expected findings, exit 1. The two files
have 14 recognized invocations and 15 checked long options. This does not
assert every CLI invocation is covered. The scanner skips other subcommands,
Docker commands, unsupported syntax, and stops conservatively on variadic args.

For the more extensive, pinned trial, from the Flagcheck development checkout:

```sh
PYTHONPATH=src python benchmarks/pilot_jmo.py /path/to/jmo-checkout
```

The harness statically extracts the schema, checks it against the reviewed JSON,
scans eight Markdown files, then separately checks 23 manually reviewed argv
excerpts from Docker and embedded YAML examples and two literal Compose lists.
The pinned Dockerfile declares `ENTRYPOINT ["jmo"]`; the CLI tail is mapped to
`jmo scan`. No container is launched, and this does not verify whether a registry
image tagged `latest` was built from the pinned source.
The multi-document workflow example is not directly supported by the native
workflow reader, and `--attest` after variadic `--tools` can be missed. The
selected excerpt numbers are specific to the pinned source. This is a
reproducible case study, not a complete repository audit.

### Findings

| Surface | Abbreviated | Invalid/ambiguous | Total |
| --- | ---: | ---: | ---: |
| Direct fenced Markdown scans | 1 | 2 | 3 |
| Manually mapped literal excerpts / Compose argv | 20 | 5 | 25 |
| Total reviewed occurrences | 21 | 7 | 28 |

Direct source lines: `docs/FAQ.md:63` (`--iac`, unknown), `:72` (`--k8s`,
ambiguous among four choices); `docs/SAMPLE_OUTPUTS.md:13` (`--results`,
suggestion `--results-dir`). Docker README lines 309, 318, 328, 505, 585,
625, 638, 1144, 1161, 1207, 1219; VERSION_MANAGEMENT.md:601; wizard-examples.md:534;
github-actions-docker.yml:29,102,158,289,301; docker-compose.yml:19,65 all
have `--results`. attestation-workflows.md:50,306,333,393,666 have `--attest`.
The scanner reports the first unknown flag per invocation; `--sign`, when it
follows `--attest`, is not separately counted. Unknown options need developer
review rather than a guessed automatic fix.

All 20 mapped `--results` substitutions were checked against the reviewed
schema and returned zero findings; the direct substitution was checked too.
No source changes were made. Native coverage across eight Markdown files:
326 logical commands, 108 recognized invocations, 78 checked long options,
74 incomplete invocations, and 1 lexical failure. Counts are partial, and
recognized does not mean all flags were inspected. These findings reproduce a
known issue, not discovery of 28 new defects. The issue's later `--profile`
update was respected.

## JUnit2Context — clean baseline

At [`d8f28712a5cdaa16b5a4ab85b89d3fb54b50daf2`](https://github.com/HafidIdrissi/junit2context/tree/d8f28712a5cdaa16b5a4ab85b89d3fb54b50daf2),
static extraction of `_parser` gave 11 exact option spellings, including help.
Scanning the actual README had zero findings (5 recognized invocations, 5 long
options checked, no incomplete invocations or lexical failures). A synthetic
command with `--max-cha` was flagged as a prefix of `--max-chars`. The open
[proposal #57](https://github.com/HafidIdrissi/junit2context/issues/57) requests
discussion of compatibility before changing the parser. No bug or adoption
is claimed from this clean baseline; no submission is warranted yet.

## Feedback and success criteria

The JMo maintainer is the strongest candidate for an opt-in trial because the
existing issue explicitly asks for exact per-subcommand classification. The
project has its own parser-based guard, so Flagcheck must add value beyond that
guard, e.g. by handling reviewed Docker and embedded YAML commands without
executing them. Ask for feedback, do not request stars, and do not add a
dependency or CI workflow on their behalf. One voluntary independent run or
explicit maintainer response counts as initial engagement; only actual
independent recurring use counts as adoption. No external adoption is verified.
