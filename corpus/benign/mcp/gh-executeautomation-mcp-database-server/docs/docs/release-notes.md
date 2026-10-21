# Release Notes

## Version 1.0.2 (Current)

**Release Date:** April 2025

### New Features
- Complete overhaul of documentation with new Docusaurus implementation
- Updated branding with blue color scheme
- Added comprehensive connection reference guide
- Improved database tools documentation
- New getting started guide for easier onboarding

### Improvements
- Better error handling for database connections
- Enhanced SQL query performance, particularly for large result sets
- Updated Node.js dependencies to the latest stable versions
- Improved security for credential handling
- Added environment variable support for sensitive connection information

### Bug Fixes
- Fixed connection issue with SQL Server when using Windows Authentication
- Corrected error in PostgreSQL RETURNING clause handling
- Addressed memory leak in connection pooling
- Fixed date formatting in SQLite exports

## Version 1.0.1

**Release Date:** April 2025

### New Features
- Initial support for PostgreSQL databases
- Added export functionality for CSV and JSON formats
- Introduced business insights tracking with memo feature

### Improvements
- Enhanced error reporting for failed queries
- Better handling of large result sets
- Optimized connection pooling for SQL Server

### Bug Fixes
- Fixed SQL Server authentication with special characters in password
- Addressed timeout issues with long-running queries
- Resolved schema detection problems with certain table names

## Version 1.0.0

**Release Date:** April 2025

### Initial Release Features
- Support for SQLite and SQL Server databases
- Basic SQL query execution (SELECT, INSERT, UPDATE, DELETE)
- Table management (CREATE, ALTER, DROP)
- Schema introspection
- MCP integration for Claude Desktop
- Node.js-based implementation for cross-platform support

## 1.1.0 (2024-05-30)

### Features
- Added MySQL database support (read/write/query, schema, etc.)
- Support for passing MySQL port via CLI and config
- Improved port validation and debug logging for MySQL
- Updated documentation and examples for MySQL and port usage 