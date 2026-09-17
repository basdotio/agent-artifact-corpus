---
name: "dotnet-ci-foundation"
description: "Patterns for setting up a .NET CI pipeline with GitHub Actions and xUnit test projects"
domain: "testing"
confidence: "low"
source: "earned"
---

## Context
When bootstrapping a .NET project's CI pipeline and initial test infrastructure. Applies to any .NET solution using GitHub Actions and xUnit.

## Patterns
- CI workflow at `.github/workflows/ci.yml` with three steps: `dotnet restore`, `dotnet build --no-restore`, `dotnet test --no-build`
- Run at repo root so the solution file is discovered automatically — new projects added to the solution are automatically included in CI
- Use `dotnet new xunit` template to generate test projects — it produces correct package versions and includes global `<Using Include="Xunit" />`
- Test projects go in a `tests/` directory, added to solution under a `/tests/` folder
- Always include a smoke test (`Assert.True(true)`) so CI has something to run from day one — proves the pipeline is wired end to end
- Set `<IsTestProject>true</IsTestProject>` in csproj so `dotnet test` discovers the project

## Examples
```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '10.0.x'
      - run: dotnet restore
      - run: dotnet build --no-restore
      - run: dotnet test --no-build --verbosity normal
```

## Anti-Patterns
- Don't hardcode solution file paths in CI — let `dotnet` discover them at the repo root
- Don't skip the test step even if no real tests exist yet — the placeholder test validates the pipeline
- Don't use `dotnet test` without `--no-build` when a build step already ran — wastes CI minutes
- Don't manually author xUnit csproj files — use `dotnet new xunit` to get correct, compatible package versions
