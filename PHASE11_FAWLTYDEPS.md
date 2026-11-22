# FawltyDeps: an independent-codebase trial, not adoption

23 November 2026. Developer-run, AI-assisted validation against the MIT-licensed
[FawltyDeps repository](https://github.com/tweag/FawltyDeps) at
[`6b57917`](https://github.com/tweag/FawltyDeps/tree/6b57917cc4824ebae253303dd004d990eb569ba4).
The existing [issue #293](https://github.com/tweag/FawltyDeps/issues/293) describes
unexpected argparse prefix acceptance. The current parser still leaves
`allow_abbrev` enabled by default; the full mapping flag is now
`--custom-mapping-file`, unlike the historical issue's spelling.

## Reproduce

Obtain that exact upstream checkout and run the following from the Flagcheck
development checkout. The harness verifies the Git blob hashes before it reads
the parser source and six original documentation files. It does not import or
run FawltyDeps, install dependencies into it, or execute scanned commands.

```sh
PYTHONPATH=src python benchmarks/pilot_fawltydeps.py /path/to/fawltydeps-checkout
```

The reviewed CLI inventory has 30 flag spellings. The static extractor finds
22; the eight custom `union` actions explicitly declare `nargs='+'` and are
manually reviewed and added. This is an actual setup cost in today's Flagcheck.

| Measurement | Result |
|---|---:|
| Original Markdown files | 6 |
| Recognized invocations | 17 |
| Long options checked | 14 |
| Incomplete invocations | 11 |
| Warnings/errors in the supported original commands | 0 |
| Issue reproductions flagged as abbreviations | 2 |

The issue examples `--ignore-undec pandas` and `--custom-mapping mapping.toml`
are detected with the respective suggestions `--ignore-undeclared` and
`--custom-mapping-file`. The full names produce no findings. Independent
stdlib argparse parser instances using the relevant option declarations confirm
the prefix resolution and the rejection of abbreviated names when disabled.
This is an option-resolution check, not execution of the real tool or its tests.

There are no verified new documentation defects in the scanned scope. The
scanner stops conservatively at variadic values, ignores inline prose snippets,
and does not demonstrate all examples are correct. We have not submitted
an upstream patch or contacted the maintainer; disabling abbreviations changes
compatibility, so maintainer preference should be established before that work.
No independent usage, external adoption, or download growth is claimed.
