---
name: test-ci-pipeline
description: CI/CD pipeline configuration for monorepo testing including GitHub Actions workflows, Turborepo integration, quality gates, and preview deployments
allowed-tools: ["Read", "Write", "Edit", "Bash"]
triggers: ["CI configuration", "github actions testing", "CI pipeline", "turborepo CI", "quality gates", "preview integration", "CI troubleshooting", "workflow configuration", "test pipeline", "CI/CD setup"]
---

===TEST_CI_PIPELINE===
META:
  TYPE::SKILL
  VERSION::1.0
  STATUS::ACTIVE
  COMPRESSION_TIER::AGGRESSIVE
  DOMAIN::HEPHAESTUS[tool_crafting]⊕HERMES[coordination]

§1::PRIMARY_SOURCE_MANDATORY_FIRST

SOURCE::.hestai/state/context/test-context/RULES.md
PRINCIPLE::"POC-proven pattern post-it note - ALWAYS consult BEFORE infrastructure decisions"

CONTAINS::[
  CI_pipeline[2-tier_strategy],
  environment_variables,
  port_assignments,
  TRACED_protocol
]

§2::DETAILED_DOCUMENTATION

CI_PIPELINE::.hestai/state/context/test-context/CI-PIPELINE-CONFIGURATION.md->[turborepo_config, github_actions, quality_gates[typecheck->lint->test], secret_management, parallel_execution, artifact_storage]

§3::POC_REFERENCE_WHEN_NEEDED

PROVEN_CI::/Volumes/HestAI-Projects/eav-ops/eav-apps/scripts-web/.github/workflows/ci.yml
KEY_SECTIONS::[
  lines_43-120::local_supabase_setup[retry_logic],
  lines_100-109::migration_application[supabase_db_reset],
  lines_144-161::test_user_creation[auth_admin_api],
  lines_236-489::preview_branch_integration,
  lines_258-285::preview_ready_wait[graceful_skip]
]

§4::CRITICAL_PATTERNS_POC_PROVEN

PATTERN_1::CI_STRATEGY_TWO_TIER::[
  TIER_1::quality_gates[all_commits]::[
    local_supabase_start,
    migrations_via_reset,
    create_test_users,
    RUN::typecheck->lint->test_unit->build,
    EVIDENCE::POC_ci.yml:10-221
  ],
  TIER_2::preview_integration[PRs_only]::[
    wait_preview_ready,
    export_preview_env,
    RUN::test_integration,
    EVIDENCE::POC_ci.yml:236-489
  ]
]

PATTERN_2::RETRY_LOGIC::[
  PATTERN::supabase_start[3_attempts+300s_timeout+GoTrue_health_check],
  BECAUSE::"Handles transient Docker/network failures in CI",
  IMPLEMENTATION::loop[cleanup_between_attempts+health_check_before_proceed],
  EVIDENCE::POC_ci.yml:52-98
]

PATTERN_3::PREVIEW_BRANCH_GRACEFUL_SKIP::[
  PATTERN::CI_handles_missing_preview[exit_0≠failure],
  BECAUSE::"Preview branches deleted after merge OR not created for docs-only PRs",
  CODE::"if(!preview_exists)->echo('No preview - skipping')->exit_0",
  EVIDENCE::POC_ci.yml:[336-345, 376-392]
]

§5::TURBOREPO_CONFIGURATION

PIPELINE::[
  typecheck::{dependsOn:[^typecheck]},
  lint::{dependsOn:[^lint,typecheck]},
  test::{dependsOn:[^test,lint], outputs:[coverage/**]},
  build::{dependsOn:[^build,test], outputs:[dist/**]}
]

QUALITY_GATE_SEQUENCE::typecheck->lint->test->build[ALL_BLOCKING]

§6::ENVIRONMENT_CONFIGURATION

ROOT_ENV::[
  APP_URLS::[VITE_APP_URL_SCRIPTS:http://localhost:3001, VITE_APP_URL_SCENES:http://localhost:3002, ports_3003-3007]
]

CI_OVERRIDES::[
  SUPABASE_PREVIEW_URL:https://preview-branch.supabase.co,
  SUPABASE_PREVIEW_ANON_KEY:sb_publishable_preview_*,
  VITEST_INTEGRATION:true
]

§7::DIRECTORY_STRUCTURE

TIER_1::OPERATIONAL_CI_SCRIPTS::[
  scripts/create-test-users-via-api.mjs::"Used by GitHub Actions (ci.yml:158)",
  PURPOSE::CI_operational_scripts[run_outside_vitest]
]

TIER_2::TEST_SETUP_VALIDATION::[
  tests/migration-validation/::"Migration testing",
  tests/setup/create-test-users.ts::"Auth Admin API setup helper",
  PURPOSE::test_setup_scripts+validation_helpers
]

§8::AGENT_CONSULTATION

CONSULT::[
  test-methodology-guardian::"TDD workflow alignment, RED->GREEN->REFACTOR compliance",
  technical-architect::"Test harness architecture decisions, shared utilities structure",
  critical-engineer::"Production risk from test infrastructure failures"
]

§9::KNOWLEDGE_BASE_REFERENCES

PRIMARY::.hestai/state/context/test-context/RULES.md[POC_proven_patterns]->CONSULT_FIRST

DOCUMENTATION::[
  .hestai/state/context/test-context/CI-PIPELINE-CONFIGURATION.md
]

POC_REFERENCE::[
  /Volumes/HestAI-Projects/eav-ops/eav-apps/scripts-web/.github/workflows/ci.yml
]

NORTH_STAR::.hestai/north-star/000-UNIVERSAL-EAV_SYSTEM-D1-NORTH-STAR.md[I7:TDD_RED_discipline, I8:production_grade_quality]


§10::WISDOM

CORE_RULE::"POC-proven patterns are post-it notes - consult BEFORE infrastructure decisions"
INTEGRATION::[test-infrastructure, supabase-test-harness, build-execution]

===END===
