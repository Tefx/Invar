# Changelog

All notable changes to Invar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/yourusername/invar/compare/v1.13.0...HEAD
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
