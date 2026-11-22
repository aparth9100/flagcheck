# Security

Flagcheck does not intentionally execute or upload scanned commands. It reads files locally and uses a safe YAML loader for workflow syntax. It is not a sandbox, a complete shell parser or a general security scanner. It should not be used as proof that a script is safe to run.

Never share authentication material or confidential source in a public issue or benchmark. For a potential security vulnerability, use the repository's private vulnerability reporting feature once it is enabled. If private reporting is unavailable, wait for a private contact channel rather than posting exploitable details publicly.

Only the latest alpha release is intended to receive fixes. No security support SLA is promised.
