# Change-aware verification (default)

- Match validation to the modified contract and the relevant failure modes.
- During implementation run focused tests, lint or incremental compile when necessary.
- Do not repeatedly run the same expensive full suite on unchanged sources and environment.
- Integration and release milestones require an appropriate broader validation of a frozen revision.
- Do not suppress failing tests or skip mandatory security, signing, packaging, migration or accessibility checks to save tokens.
- Recheck when code, test inputs, compiler options, dependency lockfile or environment changes.
- Record command, exit code, revision, skipped tests and scope of validation; state remaining live/hardware gaps explicitly.
- Stop and request user decisions for risky operations, rather than guessing.
