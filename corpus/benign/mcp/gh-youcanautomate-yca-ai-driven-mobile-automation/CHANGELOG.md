# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.11] - 2024-12-19

### Fixed
- **Improved .env File Discovery**: Replace `load_dotenv()` with `find_dotenv()` for robust environment file discovery
  - Now searches up the directory tree from current directory
  - Falls back to home directory (~/.env)
  - Fixes CLI command issue where .env couldn't be found from arbitrary working directories
  - Applied to: chatbot.py, run_yaml.py, app.py, generate_test_from_workflow.py

## [1.0.10] - 2024-12-18

### Fixed
- **Hardcoded Model Names Removed**: All hardcoded model references eliminated from codebase
  - orchestrator.py: Removed default `anthropic.claude-3-5-haiku-20241022-v1:0`
  - bedrock_client.py: Removed default `anthropic.claude-3-sonnet-20240229-v1:0`
  - All models now require BEDROCK_MODEL_ID environment variable
- **Environment Variable Validation**: Added strict validation for required configuration
  - BEDROCK_MODEL_ID: Required for Bedrock client initialization
  - Clear error messages guide users to set missing variables
- **Error Handling in Entry Points**: Added try-except blocks with helpful diagnostics
  - run_yaml.py: Graceful error handling for orchestrator initialization
  - app.py: Clear error messages for missing configuration
  - chatbot.py: Improved error context for CLI usage
- **Configuration Files**: Removed Quick Start sections recommending hardcoded defaults
  - README.md: Removed Quick Start section (30 lines)
  - YAML_GUIDE.md: Removed Quick Start subsection (32 lines)
  - CHATBOT_GUIDE.md: Removed Quick Start subsection (10 lines)

## [1.0.0] - 2026-04-17

### Added
- **Page Object Model (POM)**: Automated generation and management of page objects for mobile apps
- **Interactive Chatbot**: User-friendly interface for exploring apps and generating tests
- **Session Management**: Create and manage multiple Appium sessions
- **Element Interactions**: Comprehensive element interaction tools (click, tap, long press, drag, type text)
- **Navigation Tools**: Scroll, swipe, and navigate through mobile app UI
- **App Management**: Install, uninstall, activate, and terminate apps
- **Context Switching**: Switch between native and web contexts
- **iOS Support**: iOS simulator management and WebDriverAgent integration
- **Screenshot Capture**: Full page and element-specific screenshot capabilities
- **Test Generation**: Auto-generate regression tests from recorded workflows
- **AWS Bedrock Integration**: AI-powered test generation and validation
- **YAML Workflow Support**: Define and execute test workflows in YAML format
- **Test Regression Detection**: Automatically detect and report regressions
- **Locator Generation**: Parse page source and generate element locators
- **CLI Commands**: Command-line interface for all operations
- **MCP Server**: Model Context Protocol server for AI integration

### Features
- **AI-Driven Automation**: Leverage AWS Bedrock for intelligent test generation
- **Multiple Platforms**: Support for iOS and Android
- **Multi-Session Support**: Run multiple test sessions in parallel
- **Rich Logging**: Comprehensive logging with emoji indicators
- **Auto-Recovery**: Built-in error handling and recovery mechanisms
- **Type Hints**: Full Python type hints for better IDE support
- **Comprehensive Documentation**: Detailed guides and examples

### Documentation
- CHATBOT_GUIDE.md: Interactive chatbot usage guide
- POM_GUIDE.md: Page Object Model guide
- POM_QUICKSTART.md: Quick start for POM
- QUICKSTART_CAPTURE_REPLAY.md: Capture and replay workflow guide
- PYTEST_CONVERSION_GUIDE.md: Convert tests to pytest format
- VALIDATION_ARCHITECTURE.md: Architecture and validation approaches

## [0.1.4] - 2026-04-10

### Initial Release
- Beta version with core Appium MCP functionality
- Basic test generation capabilities
- Session management support
