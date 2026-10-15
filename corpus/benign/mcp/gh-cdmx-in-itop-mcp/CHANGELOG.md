# Changelog

All notable changes to the iTop MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-07-16

### Added
- **Smart Query Processor V2**: Complete rewrite with class-specific handlers for enhanced natural language query processing
- **Specialized Class Handlers**: Dedicated handlers for 12+ iTop classes including:
  - **Ticket Management**: UserRequest, Ticket, Change, Incident, Problem
  - **Infrastructure**: Server, PC, VirtualMachine, NetworkDevice  
  - **People & Organization**: Person, Team, Organization
- **Advanced Query Features**:
  - Automatic class detection from natural language queries
  - Real-time schema discovery using `*+` output fields
  - Intelligent field mapping with user-friendly aliases
  - Enhanced filtering with regex pattern matching
  - Sophisticated grouping and breakdown capabilities
  - SLA compliance analysis and deadline tracking
  - Multi-server name detection with fuzzy matching
- **Enhanced Result Formatting**:
  - Class-specific output formatting with relevant icons
  - Detailed vs summary view modes
  - Grouped results with statistical breakdowns
  - Software-focused results for infrastructure queries
  - Improved error handling with actionable suggestions
- **Generic Handler Framework**: Fallback support for classes without specific handlers
- **Extensible Architecture**: Easy addition of new class handlers following the base pattern

### Enhanced
- **Query Intelligence**: Improved natural language understanding for complex ITSM scenarios
- **Field Mappings**: Comprehensive field mappings for each supported class
- **Error Handling**: Better error messages with troubleshooting guidance
- **Performance**: Optimized queries with targeted field selection

### Technical Improvements
- **Code Organization**: Modular handler-based architecture for better maintainability
- **Type Safety**: Enhanced type annotations and validation
- **Documentation**: Inline documentation for all handler classes and methods

## [1.1.0] - 2025-07-10

### Added
- Smart Query Processor: Accepts natural language ITSM queries and maps them to iTop classes and fields automatically.
- Dynamic Schema Discovery: Automatically detects available iTop classes and their fields for flexible, schema-aware queries.
- Advanced Query Features: Supports grouping, filtering, SLA-based stats, and relationship navigation in natural language queries.
- Enhanced User-Facing Features: Added support for queries such as PC/Server/VM counts, status breakdowns, SLA compliance, and more.
- Extensibility: Framework for adding new query types and custom logic with minimal code changes.
- Improved Documentation: Comprehensive rewrite of README.md, including advanced usage, extensibility, and feature documentation.

### Changed
- README.md updated for clarity, completeness, and alignment with new features and usage patterns.

### Fixed
- Minor documentation and usage guide corrections.

## [1.0.0] - 2025-06-15

### Added
- Initial release of iTop MCP Server
- Complete Model Context Protocol server for iTop ITSM integration
- 8 comprehensive tools for iTop REST API operations:
  - `list_operations`: List available API operations
  - `get_objects`: Search and retrieve iTop objects  
  - `create_object`: Create new tickets/CIs/users
  - `update_object`: Update existing objects
  - `delete_object`: Safe deletion with simulation mode
  - `apply_stimulus`: Apply state transitions
  - `get_related_objects`: Find dependencies/impacts
  - `check_credentials`: Validate API access
- Full CRUD support (create, read, update, delete)
- State management with stimulus application
- Relationship discovery and impact analysis
- Comprehensive error handling and validation
- Safety features (simulation mode for deletions)
- Complete documentation (README, USAGE guide, PUBLISHING guide)
- Development tools (Makefile, test scripts)
- Configuration templates
- Claude Desktop integration examples
- MIT License
- PyPI publishing configuration
- Production-ready error handling

### Technical Features
- FastMCP framework for MCP protocol
- httpx for async HTTP requests
- Comprehensive type hints and documentation
- Environment-based configuration
- Python 3.10+ support

### Documentation
- Comprehensive README with installation and usage
- Detailed USAGE guide with examples
- Publishing guide for maintainers
- Project summary and architecture overview
- Configuration templates for easy setup

[1.0.0]: https://github.com/roneydsilva/itop-mcp/releases/tag/v1.0.0
