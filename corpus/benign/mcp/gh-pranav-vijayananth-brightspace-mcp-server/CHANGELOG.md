# Changelog

## [1.0.0] - 2025-10-14

### Added
- ✅ Initial release of Brightspace MCP Server
- ✅ Playwright-based web scraper for Purdue Brightspace
- ✅ Duo Mobile 2FA authentication support
- ✅ Course list extraction functionality
- ✅ MCP server integration with Claude Desktop
- ✅ Automated setup script with Python 3.12 support
- ✅ Environment-based credential management
- ✅ Comprehensive README and setup guide
- ✅ Example Claude Desktop configuration

### Features
- **Authentication**: Automated login with Duo Mobile 2FA
- **Course Scraping**: Extract list of enrolled courses with names, codes, and URLs
- **MCP Tools**: `hello` tool for testing integration
- **Data Export**: Save scraped data to JSON format

### Technical Details
- Python 3.12 required (compatibility with greenlet dependency)
- Playwright for browser automation
- MCP Python SDK for Claude Desktop integration
- Works on macOS (tested), should work on other platforms

### Known Issues
- Assignment scraping needs CSS selector testing
- Grade extraction not yet implemented
- Course content/syllabus extraction not yet implemented

### Coming Soon
- `get_courses` MCP tool - List all enrolled courses
- `get_assignments` MCP tool - Get assignments for a course  
- `get_grades` MCP tool - Get grade information
- `get_announcements` MCP tool - Get course announcements
- Better error handling and retry logic
- Session persistence and caching

## Development Notes

### What Worked
- Playwright successfully handles Duo Mobile 2FA
- Course scraping works with CSS selector: `d2l-enrollment-card .d2l-card-container`
- MCP integration successful using `claude_desktop_config.json` (NOT `config.json`)
- Python 3.12 resolves greenlet compatibility issues (3.13 doesn't work)

### Lessons Learned
- Brightspace uses custom web components (`<d2l-my-courses>`) that load dynamically
- Must wait for JavaScript to render before scraping
- Claude Desktop's "Edit Config" button opens the correct MCP configuration file
- MCP server configuration must be in `claude_desktop_config.json`, not `config.json`
- Environment variables can be passed through Claude Desktop config or `.env` file

### Credits
- Built for Purdue University students
- Uses Model Context Protocol for Claude Desktop integration
- Playwright for reliable browser automation
