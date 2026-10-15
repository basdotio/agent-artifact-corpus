# Release build

`1.0.0` is a source Skill package. Python 3.9+ and PyYAML 6.x are required to
run the bundled auditor. The audit itself does not access the network, execute
inspected scripts, install dependencies, or change inspected files. Heuristic
candidates require human review.

The release archive contains exactly these tracked files under an
`instruction-audit/` directory:

```text
.github/workflows/validate.yml
.gitignore
CHANGELOG.md
CONTRIBUTING.md
LICENSE
README.md
README.zh-CN.md
RELEASE.md
SKILL.md
agents/openai.yaml
pyproject.toml
references/official-guidance.md
references/report-schema.md
references/token-criteria.md
scripts/audit_instructions.py
scripts/validate_package.py
tests/test_audit_instructions.py
```

After the `1.0.0` tag points to the CI-approved commit, create `dist/` and
build from that exact tag. The same commit and Git version produce the same
ZIP bytes:

```text
git archive --format=zip --prefix=instruction-audit/ --output=dist/instruction-audit-1.0.0.zip v1.0.0
```

Compare `git ls-tree -r --name-only v1.0.0` with the manifest above. Compute a
SHA-256 digest of the ZIP (`sha256sum` on Linux/macOS or `Get-FileHash` in
PowerShell), publish that digest with the release asset, and verify the ZIP by
extracting it, running the tests and package validator, then running the
auditor in strict mode on the extracted directory. The GitHub source archive
and this ZIP contain source files; `pyproject.toml` installs only the scanner's
PyYAML dependency, so invoke the bundled script by its file path.
