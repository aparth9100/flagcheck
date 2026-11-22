# Contributing

Flagcheck is an alpha project focused on catching drift between command-line option declarations and literal invocations in source-controlled files. Real reproductions are especially helpful.

For a bug, include a minimal command, the reviewed schema, expected output, actual output and Flagcheck/Python versions. Redact credentials and private filenames. Please discuss broad features or rewrites before starting them.

For a fix:

1. Add a regression test that fails before the change.
2. Keep the change focused; run `python -m unittest discover -s tests -v` after installing the package.
3. Explain limitations and manual verification. Avoid speculative or mass-generated changes that add review burden.
4. AI-assisted contributions are welcome when the human contributor understands, verifies and takes responsibility for the whole change. Disclose material AI assistance. Do not submit unattended agent PRs or comments.

Treat other contributors respectfully. Good-faith questions and useful reproductions matter more than contribution counts.
