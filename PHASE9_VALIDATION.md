# Docker and YAML pilot follow-up

22 November 2026 — development branch, AI-assisted. This is the Flagcheck
developer's read-only case study, not an external user's deployment or adoption.

## Reproduction

Use the same pinned JMo Security source (`8628e5ccda3a783e2b8aca033f9869a9eac6480f`)
and reviewed `examples/jmo-scan-pilot.json` as in PHASE8_PILOT.md. From this
checkout:

```sh
PYTHONPATH=src python benchmarks/pilot_jmo.py /path/to/jmo-checkout
```

The benchmark first repeats the historical direct and manually mapped scans.
It then scans the eight Markdown files, multi-document GitHub Actions example,
and Compose file directly with `yaml_examples=True` and explicit image mappings
for `ghcr.io/jimmy058910/jmo-security:latest` and `jmo-security:latest` to `jmo`.
The mapping assumes the pinned source's entrypoint; it does not verify the
registry tag. No source imports, shell commands, containers, or scanners from
JMo are executed. The CLI equivalent uses `--yaml` and two `--docker-image`
arguments.

## Results

| Measurement | Count |
| --- | ---: |
| Historical native findings | 3 |
| Historical manually adapted findings | 25 |
| Adapted findings now recovered natively | 24 |
| Unrecovered PowerShell example | 1 |
| Additional candidates in the same files | 4 |
| Total automatic findings | 31 |

The 31 findings comprise 21 abbreviated, 9 unknown, and 1 ambiguous long
option. Four additional candidates are in a Compose YAML fence in
`docs/DOCKER_README.md:659` (`--results`), and workflow command starts
`docs/examples/attestation-workflows.md:107`, `:462`, `:566` (`--attest`).
The benchmark asserts exact per-file logical-start, flag, and diagnostic-code
matches. PowerShell at `docs/DOCKER_README.md:1161` remains deliberately
unsupported. The finding's location is the start of its logical command or
Compose list, not necessarily the physical flag line.

Coverage: 409 logical commands, 194 matched invocations, 224 unmatched segments,
192 long options checked, 123 incomplete invocations, 1 lexical failure and
0 malformed fenced YAML blocks. These counters are not a completeness guarantee.
Variadic options remain an intentional stopping point; the scanner does not
assert the flags match every released image, resolve shell expansions, or
infer missing options. Additional unknown flags should be reviewed with the
target maintainer before proposing fixes.

## Release readiness

Local unit tests include exact image matching, option value handling, entrypoint
override and dynamic image skips, multi-document workflow line mapping, YAML
fence opt-in and parse failure counters, literal Compose argv handling and
invalid CLI mapping input. The development version was `0.2.0a2.dev0`.
[Cross-platform CI](https://github.com/aparth9100/flagcheck/actions/runs/45026750249)
passed. The second alpha is prepared separately and still requires release
review and the existing tag-specific publication workflow.
