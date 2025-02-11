# Changelog

All notable changes to this project will be documented in this file.

## [0.5.1] - 2025-02-11

### Changed
- Update extraction prompts for batch and lot number handling

### Removed
- Remove Azure Functions configuration support

## [0.5.0] - 2025-02-09

### Added
- Add Google Vertex AI Gemini support

## [0.4.3] - 2025-02-06

### Added
- Add model invoke timing logging
- Identify model as a trace attribute
- Log model name with extraction progress

## [0.4.2] - 2025-02-03

### Changed
- Async call chain and parallelize calls to expert LLMs

## [0.4.1] - 2025-01-26

### Added
- Improve logging - support OTEL and App Insights
- Add configurable auth disabled mode
- Improve characteristic mapper prompt

### Removed
- Remove old dotenv references

## [0.4.0] - 2025-01-22

### Added
- Add estimated usage costs to logs and response
- Include client ID in logging context
- Implement basic API-key based security
- Implement mock-mode based on multiple signals
- Add basic flow logging
- Document mock-mode and authentication

### Fixed
- Fix LangChain dependency conflict
- Fix potential circular dependency problem with the logging module
- Improve logger formatting

## [0.3.0] - 2025-01-01

### Added
- Add dockerized deployment options with Poppler support
- Add Basic API documentation
- Basic Azure Functions Integration

### Changed
- Use POST HTTP method instead of GET
- Allow disabling PDF to Image conversion
- Code refactor with improved naming and simplified processing modules

### Fixed
- Defensive input filename usage in temp filename storage

## [0.2.0] - 2024-12-31

### Added
- Initial Commit with:
  - Working FastAPI server (Single endpoint)
  - CLI interface (for debugging)
  - Mock mode support

### Note
Initial version limitations:
- Not all parsing rules implemented
- No performance considerations
- No logging
- No Usage/Cost reporting
