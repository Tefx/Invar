# Changelog

All notable changes to Invar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **init: Language-specific config.toml (LX-05)** - Generate correct config for TypeScript
  - TypeScript projects now get TypeScript-specific `forbidden_imports`: `fs`, `path`, `http`, etc.
  - TypeScript projects get `require_doctests = false` (uses JSDoc instead)
  - TypeScript-specific `exclude_paths`: `node_modules`, `.next`, `coverage`
  - Python projects unaffected (still get Python-specific config)

## [1.15.6] - 2026-01-03

### Fixed
- **invar map: File Handle Management (DX-82)** - Fixed "Too many open files" error
  - Convert `discover_python_files()` generator to list to release directory handles immediately
  - Explicitly delete file list after processing to free memory
  - Prevents exhausting system file descriptor limit on large projects
  - **Solves system error** on macOS and other systems with low default limits:
    - Root cause: `rglob()` generator keeps directory handles open during iteration
    - Symptom: "OSError: [Errno 1] Too many open files in system" 
    - macOS default limit: 256 file descriptors
  - Recommendation: Users can also increase system limits with `ulimit -n 4096`

## [1.15.5] - 2026-01-03

### Fixed
- **Pi Custom Tools: Exit Code Handling** - Fixed false positive failures
  - Changed exit code check from `!== 0` to `&& !== 0` (truthy check)
  - Prevents treating undefined/null/0 as failure
  - **Solves critical issue** where successful commands were marked as failed:
    - Root cause: Pi's exec() may return undefined/null/0 for successful commands
    - Symptom: Tools returned correct JSON data but status showed as "Failed"
    - Example: `Failed to extract TOC: {correct JSON data}`
  - All 8 tools now correctly identify success vs failure
  - Fixed in: invar_sig, invar_map, invar_doc_toc, invar_doc_read, invar_doc_find, invar_doc_replace, invar_doc_insert, invar_doc_delete
  - Note: invar_guard intentionally doesn't check exit code (warnings are valid output)

## [1.15.4] - 2026-01-03

### Fixed
- **Pi Custom Tools: Error Message Capture** - Improved error diagnostics
  - Enhanced error message capture to include both stderr and stdout
  - Prevents empty error messages like "Failed to extract TOC: "
  - Fallback to "Unknown error" if both streams are empty
  - **Solves diagnostic issue** where error details were missing:
    - Root cause: Some errors may output to stdout instead of stderr
    - Pi's exec() stderr might be empty even when command fails
  - All 9 tools now provide clear error messages for debugging
  - Fixed in: invar_sig, invar_map, invar_doc_toc, invar_doc_read, invar_doc_find, invar_doc_replace, invar_doc_insert, invar_doc_delete

## [1.15.3] - 2026-01-03

### Fixed
- **Pi Custom Tools: Parameter Handling** - Fixed parameter validation and default values
  - Added validation for all required parameters (file, target, section, etc.)
  - Added explicit default value handling using `??` operator for optional parameters
  - Prevents tools from failing when Pi doesn't pass parameter values
  - **Solves critical issue** where tools failed with missing parameters:
    - Root cause: TypeBox default values not automatically populated in params object
    - Pi may call tools without passing values, even for required parameters
  - All 9 tools now validate inputs and handle defaults correctly
  - Clear error messages guide LLM to provide required parameters


## [1.15.2] - 2026-01-03

### Fixed
- **Pi Custom Tools: ESLint Compatibility** - Removed CommonJS require() calls
  - Moved `fs` and `path` imports to top-level ES module imports
  - Removed internal `require("fs")` and `require("path")` calls in doc tools
  - Fixed in `doc_replace` and `doc_insert` execute methods
  - **Resolves critical bug** where custom tools failed to load:
    - `invar_map()`: "Failed to generate map"
    - `invar_sig()`: "Failed to get signatures"
    - `invar_guard()`: Tool calls hanging without response
  - Root cause: ESLint prohibited CommonJS require() in ES modules
  - Pi custom tools now load and execute correctly

## [1.15.1] - 2026-01-03

### Added
- **Pi Custom Tools: Document Tools** - Added 6 doc tools for structured markdown editing
  - `invar_doc_toc`: Extract document structure (Table of Contents)
  - `invar_doc_read`: Read specific section from a document
  - `invar_doc_find`: Find sections matching a pattern
  - `invar_doc_replace`: Replace section content
  - `invar_doc_insert`: Insert content relative to a section
  - `invar_doc_delete`: Delete a section
  - All tools follow the same security patterns as core tools (path validation, temp file handling)
  - Brings Pi custom tools to parity with MCP server capabilities (9 tools total)

### Fixed
- **Pi Custom Tools: uvx Fallback Support** - Automatic fallback to `uvx invar-tools`
  - Added `resolveInvarCommand()` helper to replace `checkInvarInstalled()`
  - Try `invar` command first (if installed in PATH)
  - Fallback to `uvx invar-tools` if `invar` not found
  - No installation required - uvx downloads and runs invar-tools on-demand
  - Matches the 3-tier calling method documented in CLAUDE.md
  - All 9 tools updated to use the command resolver

### Added
- **Pi Custom Tools: Document Tools** - Added 6 doc tools for structured markdown editing
  - `invar_doc_toc`: Extract document structure (Table of Contents)
  - `invar_doc_read`: Read specific section from a document
  - `invar_doc_find`: Find sections matching a pattern
  - `invar_doc_replace`: Replace section content
  - `invar_doc_insert`: Insert content relative to a section
  - `invar_doc_delete`: Delete a section
  - All tools follow the same security patterns as core tools (path validation, temp file handling)
  - Brings Pi custom tools to parity with MCP server capabilities

### Changed
- **Pi Custom Tools: uvx Fallback Support** - Automatic fallback to `uvx invar-tools`
  - Try `invar` command first (if installed in PATH)
  - Fallback to `uvx invar-tools` if `invar` not found
  - No installation required - uvx downloads and runs invar-tools on-demand
  - Matches the 3-tier calling method documented in CLAUDE.md

### Added
- **Pi Custom Tools: Document Tools** - Added 6 doc tools for structured markdown editing
  - `invar_doc_toc`: Extract document structure (Table of Contents)
  - `invar_doc_read`: Read specific section from a document
  - `invar_doc_find`: Find sections matching a pattern
  - `invar_doc_replace`: Replace section content
  - `invar_doc_insert`: Insert content relative to a section
  - `invar_doc_delete`: Delete a section
  - All tools follow the same security patterns as core tools (path validation, temp file handling)
  - Brings Pi custom tools to parity with MCP server capabilities

## [1.15.0] - 2026-01-03

### Added
- **DX-81: Multi-Agent Init Support** - Complete implementation
  - Remove mutual exclusivity between `--claude` and `--pi` flags
  - Support combined flags: `invar init --claude --pi`
  - Install both `.claude/hooks/` and `.pi/hooks/` simultaneously
  - **Interactive mode enhancement**:
    - Changed from single-select to checkbox multi-select
    - Allow selecting multiple agents with Space key
    - Claude Code pre-checked as default
  - **Backward compatibility maintained**:
    - `invar init --claude` works as before (Claude only)
    - `invar init --pi` works as before (Pi only)
    - Sequential init (`--claude` then `--pi`) still works
  - **Use cases enabled**:
    - Team collaboration (different members use different agents)
    - Agent switching (both configured, use either)
    - Open source projects (contributors have agent choice)
- **DX-79: Message Count Auto-Trigger for /invar-reflect** - Cross-platform feedback automation
  - Automatic feedback reminder at configurable message threshold (default: 30)
  - **Claude Code implementation**: UserPromptSubmit hook with jq config parsing
  - **Pi implementation**: TypeScript hook with fs config reading
  - **Shared configuration**: Both read `.claude/settings.local.json` feedback section
  - **User control**: Disable via `feedback.enabled=false` or adjust `min_messages` threshold
  - Replaces unimplemented PostTaskCompletion hook with simpler, universally-supported approach
- **Pi Custom Tools for Invar** - Native tool integration without CLI dependency
  - `invar_guard`: Smart verification wrapper (static + doctests + symbolic)
  - `invar_sig`: Show function signatures and contracts
  - `invar_map`: Symbol map with reference counts
  - Auto-installed via `invar init --pi` in `.pi/tools/invar/index.ts`
  - Pi auto-discovers tools, no configuration needed
  - Solves problem of Pi agents not actively using invar tools (falling back to pytest/grep)

### Changed
- Agent selection prompt now uses checkbox instead of radio buttons
- Header shows "Claude Code + Pi" when both flags used
- File selection logic builds from all selected agents' categories

### Fixed
- **Security hardening in Pi templates** (3-round adversarial review)
  - Path injection defense with comprehensive shell metacharacter blocking
  - TOCTOU race condition eliminated in config reading
  - Runtime type validation for external inputs
  - ES module consistency (no CommonJS mixing)

### Documentation
- Updated README.md with multi-agent examples
- Added Multi-Agent Support section to CLAUDE.md
- Updated context.md to reflect DX-81 completion

### Added
- **DX-81: Multi-Agent Init Support** - Complete implementation
  - Remove mutual exclusivity between `--claude` and `--pi` flags
  - Support combined flags: `invar init --claude --pi`
  - Install both `.claude/hooks/` and `.pi/hooks/` simultaneously
  - **Interactive mode enhancement**:
    - Changed from single-select to checkbox multi-select
    - Allow selecting multiple agents with Space key
    - Claude Code pre-checked as default
  - **Backward compatibility maintained**:
    - `invar init --claude` works as before (Claude only)
    - `invar init --pi` works as before (Pi only)
    - Sequential init (`--claude` then `--pi`) still works
  - **Use cases enabled**:
    - Team collaboration (different members use different agents)
    - Agent switching (both configured, use either)
    - Open source projects (contributors have agent choice)
- **DX-79: Message Count Auto-Trigger for /invar-reflect** - Cross-platform feedback automation
  - Automatic feedback reminder at configurable message threshold (default: 30)
  - **Claude Code implementation**: UserPromptSubmit hook with jq config parsing
  - **Pi implementation**: TypeScript hook with fs config reading
  - **Shared configuration**: Both read `.claude/settings.local.json` feedback section
  - **User control**: Disable via `feedback.enabled=false` or adjust `min_messages` threshold
  - Replaces unimplemented PostTaskCompletion hook with simpler, universally-supported approach
- **Pi Custom Tools for Invar** - Native tool integration without CLI dependency
  - `invar_guard`: Smart verification wrapper (static + doctests + symbolic)
  - `invar_sig`: Show function signatures and contracts
  - `invar_map`: Symbol map with reference counts
  - Auto-installed via `invar init --pi` in `.pi/tools/invar/index.ts`
  - Pi auto-discovers tools, no configuration needed
  - Solves problem of Pi agents not actively using invar tools (falling back to pytest/grep)

### Changed
- Agent selection prompt now uses checkbox instead of radio buttons
- Header shows "Claude Code + Pi" when both flags used
- File selection logic builds from all selected agents' categories

### Documentation
- Updated README.md with multi-agent examples
- Added Multi-Agent Support section to CLAUDE.md
- Updated context.md to reflect DX-81 completion

## [1.14.0] - 2026-01-03

### Added
- **DX-79: Invar Usage Feedback Collection** - Complete implementation of automatic feedback generation system
  - `/invar-reflect` skill: Generate structured feedback on Invar tool usage
    - Analyzes tool usage patterns and pain points
    - Tracks learning curves and confusion points
    - Produces detailed markdown reports in `.invar/feedback/`
  - **CLI tools** for feedback management:
    - `invar feedback list` - Display all feedback files with timestamps
    - `invar feedback cleanup` - Remove old feedback files (default: >90 days)
    - `invar feedback anonymize` - Strip sensitive data for safe sharing
  - **Core anonymization logic** (`src/invar/core/feedback.py`):
    - Removes 8 types of sensitive data (emails, IPs, paths, tokens, etc.)
    - Contract-verified with `@pre`/`@post` and doctests
    - CrossHair symbolic verification passed
  - **Init integration**:
    - Automatic feedback configuration in `.claude/settings.local.json`
    - Interactive consent prompt (opt-out design, default: enabled)
    - Visible notifications in quick modes (`--claude`, `--pi`)
  - **Template integration**: New projects get `/invar-reflect` skill out-of-box
    - Added to `manifest.toml` with 3 files (SKILL.md, template.md, CONFIG.md)
    - Installed automatically via `invar init --claude`

### Fixed
- **Round 2 review fixes**:
  - Moved anonymization logic from Shell to Core (proper separation)
  - Removed redundant type contracts (guard warning resolved)
  - Fixed Pi notification path mismatch
  - Expanded anonymization patterns (comprehensive coverage)

### Security
- Privacy-first design: All feedback stored locally, never sent automatically
- Comprehensive anonymization for safe sharing with maintainers
- User controls what (if anything) to share

## [1.13.0] - 2026-01-03

### Fixed
- **guard CLI默认行为对齐MCP**: CLI和MCP默认都检查修改文件
  - 修复设计遗留问题：CLI应该和MCP行为一致（agent-first原则）
  - 之前：`invar guard` 检查全部文件（慢）
  - 现在：`invar guard` 检查修改文件（快，和MCP一致）

### Added
- **新增`--all`标志**: 显式请求全检查
  - `invar guard --all` - 检查整个项目（CI、release场景）
  - 向后兼容：`invar guard --changed` 仍然有效
- **Tool Selection文档章节**: 解决Pi等不支持MCP的agent调用问题
  - 三种等价调用方式对照表（MCP / CLI / uvx）
  - 参数映射说明
  - 快速示例

### Migration
- **Agent用户（主要）**: 自动获得更快体验，无需改动
- **CI脚本（极少）**: 如需全检查，改为 `invar guard --all`
- **Pre-commit hooks**: 不受影响（已经用--changed）

## [1.12.0] - 2026-01-03

### Added
- **DX-78: TypeScript Compiler API Integration**
  - Full TypeScript semantic analysis via Compiler API
  - `invar refs` command for finding symbol references across Python and TypeScript
  - Security fixes for TypeScript code analysis
  - Comprehensive MCP handlers for TypeScript tools

### Fixed
- Skill frontmatter missing in skill definitions

## [1.11.0] - 2025-12

### Added
- **DX-77: MCP Document Tools Enhancements**
  - Phase A: Batch section reading with `invar_doc_read_many`
  - Unicode-aware fuzzy matching for section search
  - Explicit tool substitution hints

### Changed
- Documentation improvements for MCP server configuration

## [1.10.0] - 2025-12

### Added
- **DX-75: Lightweight Review Strategy**
  - Scope-based review strategies (THOROUGH, HYBRID, CHUNKED)
  - Isolation requirements for non-trivial implementations

### Changed
- Review skill now spawns isolated subagents based on scope

## [1.9.0] - 2025-12

### Added
- **DX-63: Contracts-First Enforcement**
  - `--contracts-only` flag for contract coverage checking
  - Function-level gates in BUILD phase
  - Incremental development patterns

### Changed
- USBV workflow now enforces contracts before implementation

## [1.8.0] - 2025-12

### Added
- **DX-54: Context Management**
  - Context refresh requirements at workflow entry points
  - Task Router in `.invar/context.md`

### Changed
- Workflow skills now read context on entry

## [1.7.0] - 2025-12

### Added
- **DX-51: Workflow Phase Visibility**
  - Visual phase headers for USBV transitions
  - Three-layer visibility (Skill, Phase, Tasks)

### Changed
- Phase transitions now display clear visual separators

## [1.6.0] - 2025-12

### Added
- **DX-42: Workflow Auto-Routing**
  - Automatic skill selection based on trigger words
  - User redirect capability with natural language
  - Simple task optimization

### Changed
- Skills now announce routing decisions before execution

## [1.5.0] - 2025-12

### Added
- **DX-41: Automatic Review Orchestration**
  - Guard triggers `review_suggested` for security-sensitive changes
  - Auto-entry to /review skill

### Changed
- Review is now automatically invoked after development when appropriate

## [1.4.0] - 2025-12

### Added
- **DX-37: Coverage Integration**
  - `--coverage` flag for branch coverage collection
  - Integration with pytest-cov

### Changed
- Guard can now collect and report branch coverage

## [1.3.0] - 2025-12

### Added
- **DX-30: Visible Workflow**
  - TodoList checkpoints for complex tasks (UNDERSTAND, SPECIFY, VALIDATE)
  - Contracts shown before code in SPECIFY phase

### Changed
- BUILD phase is now internal work (not shown in TodoList)

## [1.2.0] - 2025-12

### Added
- **DX-26: Guard Simplification**
  - Agent mode auto-detection (TTY vs non-TTY)
  - JSON output for non-TTY environments

### Changed
- Guard now automatically outputs JSON when piped

## [1.1.0] - 2025-12

### Added
- **DX-21: Package and Init**
  - `invar init` command for project initialization
  - Template-based CLAUDE.md and INVAR.md generation

### Changed
- Initial project setup now streamlined with `invar init`

## [1.0.0] - 2025-12

### Added
- Initial release of Invar
- Core/Shell architecture
- Contract-based verification (@pre/@post)
- USBV workflow (Understand → Specify → Build → Validate)
- Smart Guard (static + doctests + CrossHair + Hypothesis)
- MCP server for Claude Code integration
- CLI tools (guard, sig, map, rules)
- Multi-agent support (Claude Code, Aider, Pi)

---

[Unreleased]: https://github.com/yourusername/invar/compare/v1.15.5...HEAD
[1.15.5]: https://github.com/yourusername/invar/compare/v1.15.4...v1.15.5
[1.15.4]: https://github.com/yourusername/invar/compare/v1.15.3...v1.15.4
[1.15.3]: https://github.com/yourusername/invar/compare/v1.15.2...v1.15.3
[1.15.2]: https://github.com/yourusername/invar/compare/v1.15.1...v1.15.2
[1.15.1]: https://github.com/yourusername/invar/compare/v1.15.0...v1.15.1
[1.15.0]: https://github.com/yourusername/invar/compare/v1.14.0...v1.15.0
[1.14.0]: https://github.com/yourusername/invar/compare/v1.13.0...v1.14.0
[1.13.0]: https://github.com/yourusername/invar/compare/v1.12.0...v1.13.0
[1.12.0]: https://github.com/yourusername/invar/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/yourusername/invar/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/yourusername/invar/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/yourusername/invar/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/yourusername/invar/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/yourusername/invar/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/yourusername/invar/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/yourusername/invar/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/yourusername/invar/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/yourusername/invar/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/yourusername/invar/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/yourusername/invar/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yourusername/invar/releases/tag/v1.0.0
