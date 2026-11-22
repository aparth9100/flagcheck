# Opt-in pilot guide

Flagcheck is an experimental command-line option linter. The goal of a pilot is
to find whether it saves maintainers time, including discovering when it does not.
No external adoption is claimed. You do not need to install a GitHub app or give
Flagcheck access to your repository, and scanned commands are never executed.

## A small, reversible trial

1. In an existing Python environment, install the published alpha:

   ```sh
   python -m pip install flagcheck==0.2.0a2
   ```

2. Use a reviewed schema for one CLI you maintain. For a simple argparse parser,
   the published second alpha can extract literal declarations; examine the output before
   using it. For a parser built in a function, the same version supports
   `--scope` and `--discover-groups` as explained in the README.

   ```sh
   flagcheck schema-from-source path/to/cli.py --command mytool --receiver parser
   ```

   Save the output as `cli-schema.json`. Only mark `complete: true` once you've
   checked the entire option inventory, including option arity and aliases.
   Set `allow_abbrev` to match the parser. Incomplete schemas deliberately avoid
   reporting unknown or abbreviated options.

3. Run against a small, real file with known invocations, not the entire repo:

   ```sh
   flagcheck scan --schema cli-schema.json --summary --require-match README.md
   ```

   Keep this advisory initially. Review any warnings/errors and the coverage
   counters. Incomplete invocations and unsupported syntax can hide flags.
   A successful scan is not a general shell or CLI correctness guarantee.

4. If useful, run the same command in an existing CI job; only enable a hard
   failure after reviewing findings. Remove the step at any time. No telemetry
   is collected by Flagcheck.

## What feedback would be useful?

If you choose to share results in a GitHub issue, please include the version,
the relevant minimal command and a sanitized schema, whether the result was
correct, and how much review effort was required. Don't include credentials,
private source, or other confidential material. A finding that isn't useful or
a missed command is just as valuable as a true positive. Repeated independent
use, rather than stars or simulated downloads, is the meaningful milestone.

## Maintainer's pilot tracking

| Pilot | Status | Evidence |
| --- | --- | --- |
| Flagcheck | Self-use | Reviewed CLI schema, CI self-check and mutation regression |
| JMo Security | Developer-run external trial; no adoption; feedback requested | [Pinned case study](PHASE8_PILOT.md), [Docker/YAML follow-up](PHASE9_VALIDATION.md), [issue discussion](https://github.com/jimmy058910/jmo-security-repo/issues/1050) |
| JUnit2Context | Developer-run clean baseline; no adoption | [Pinned case study](PHASE8_PILOT.md) reports zero actual README findings |
| Independent external projects | Not yet established | Record only voluntary usage or public, verifiable integrations |

The project benchmarks are documented separately. They are not pilot adopters.
