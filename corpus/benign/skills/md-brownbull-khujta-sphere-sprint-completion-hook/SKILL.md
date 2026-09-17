# Sprint Completion Hook Skill

## Purpose
Automatically triggered at sprint completion to run full regression tests, generate reports, and save results to ai-state/regressions/reports.

## Tier
**Tier 2** - Growth Phase

## Sprint Completion Workflow

### 1. Pre-Completion Checks
```yaml
checks:
  - All tasks completed or moved to backlog
  - No blocking issues remain
  - Sprint goals achieved
  - Documentation updated
```

### 2. Regression Test Execution
```bash
# Run complete regression suite
echo "Sprint ${SPRINT_ID} - Running Regression Tests"

# Execute all domain tests
./ai-state/regressions/backend/run.sh
./ai-state/regressions/frontend/run.sh
./ai-state/regressions/database/run.sh
./ai-state/regressions/devops/run.sh

# Run integration tests
./ai-state/regressions/integration/run.sh

# Run E2E tests
./ai-state/regressions/e2e/run.sh
```

### 3. Report Generation
```yaml
sprint_report:
  sprint_id: "sprint-001"
  completion_date: "2025-11-06"

  metrics:
    tasks_completed: 12
    tasks_carried: 2
    story_points: 38
    velocity: 38

  test_results:
    total_tests: 234
    passed: 230
    failed: 4
    skipped: 0
    coverage: 82.3%

  quality_metrics:
    code_quality: 8.5
    performance: "All endpoints < 200ms"
    security: "No vulnerabilities found"

  issues_found:
    - id: "BUG-001"
      severity: "medium"
      component: "payment"
      status: "fixed"

  recommendations:
    - "Increase test coverage for payment module"
    - "Refactor user service for better performance"
    - "Add monitoring for new endpoints"
```

### 4. Report Storage
```
ai-state/regressions/reports/
├── sprint-001-report.md
├── sprint-001-test-results.json
├── sprint-001-coverage.html
└── sprint-001-metrics.yaml
```

### 5. Notifications
```yaml
notifications:
  success:
    - Update sprint status
    - Log completion in operations.log
    - Generate human docs
    - Notify team

  failure:
    - Create fix tasks
    - Block deployment
    - Alert team
    - Generate action plan
```

## Sprint Velocity Tracking
```yaml
velocity_history:
  sprint-001: 38
  sprint-002: 42
  sprint-003: 40
  average: 40
  trend: "stable"
```

## Integration Points
- **Triggered by**: Sprint end date or manual trigger
- **Executes**: regression-runner skill
- **Generates**: Comprehensive sprint report
- **Updates**: Sprint metrics, team velocity
- **Triggers**: human-docs-generator if milestone reached