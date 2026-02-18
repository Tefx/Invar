# LX-07: Extension Skills Architecture

**Status:** Phase 1-2 Complete (T0 Skills Implemented, CLI Implemented)
**Priority:** Medium
**Category:** Language/Agent eXtensions
**Created:** 2026-01-01
**Updated:** 2026-01-01
**Depends on:** LX-05 (skill templates)
**Deferred skills:** See [LX-08](LX-08-extension-skills-future.md)

## Executive Summary

Implement 5 core extension skills that complement the USBV workflow. Extensions are language-agnostic, work standalone (without Invar), and gain enhanced capabilities when Invar is available.

**Core Extensions (This Proposal):**

| Tier | Skill | Purpose | Status |
|------|-------|---------|--------|
| T0 | `/acceptance` | Requirements acceptance review (PRD alignment) | **Ready** |
| T0 | `/security` | Security audit (OWASP Top 10) | **Ready** |
| T1 | `/refactor` | Refactoring strategy and execution | Pending Discussion |
| T1 | `/debug` | Root cause analysis | Pending Discussion |
| T1 | `/test-strategy` | Test strategy design | Pending Discussion |

> **Note:** T1 skills have draft designs but require discussion before implementation.

---

## Design Principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | **Core independence** | Invar core (4 skills) works without extensions |
| 2 | **Graceful degradation** | Prefer Invar tools when available, fallback otherwise |
| 3 | **Language agnostic** | Work across Python, TypeScript, Go, etc. |
| 4 | **Copy-installable** | SKILL.md is self-contained, can be manually copied |

---

## Architecture

### Directory Structure

```
src/invar/templates/skills/
├── core/                        # Core skills (invar init)
│   ├── develop/SKILL.md.jinja
│   ├── investigate/SKILL.md.jinja
│   ├── propose/SKILL.md.jinja
│   └── review/SKILL.md.jinja
│
└── extensions/                  # Extension skills (optional)
    ├── _registry.yaml
    ├── acceptance/SKILL.md
    ├── security/SKILL.md
    ├── refactor/SKILL.md
    ├── debug/SKILL.md
    └── test-strategy/SKILL.md
```

### Invar Detection

Extensions detect Invar via file/context (not CLI command):

```
1. File-based: INVAR.md exists OR .invar/ directory exists
2. Context-based: invar_guard tool available in session

→ Enhanced Mode: Use invar_guard, invar_sig, invar_map
→ Standalone Mode: Use Read, Grep, Glob, Bash only
```

### Context Isolation Architecture

Adversarial skills (`/acceptance`, `/security`, `/review`) benefit from **context isolation** to prevent cognitive bias when the same agent wrote and reviews code.

#### Problem: Self-Review Bias

```
Developer writes code → Same agent reviews
                              ↓
                    "I know this works because..."
                              ↓
                    Skips verification of "obvious" things
                              ↓
                    Misses bugs that fresh eyes would catch
```

#### Solution: Isolated Agent Spawn

```
┌─────────────────────────────────────────────────────────────┐
│ CONTEXT ISOLATION STRATEGY                                   │
│                                                              │
│ --quick:    Same context (fast, less objective)             │
│             Use when: CI gates, rapid feedback              │
│                                                              │
│ --standard: Same context + explicit persona switch          │
│             Use when: Development iteration                 │
│                                                              │
│ --deep:     ISOLATED AGENT (slower, most objective)         │
│             Use when: Release readiness, critical review    │
│             DEFAULT for adversarial skills                  │
└─────────────────────────────────────────────────────────────┘
```

#### Isolation Mechanism

When `--deep` mode (default for `/acceptance`, `/security`):

```
┌─────────────────────────────────────────────────────────────┐
│ 1. COLLECT minimal inputs                                    │
│    ├── PRD/requirements path (or inline content)            │
│    ├── Design paths (if any)                                │
│    ├── Code scope (file paths to review)                    │
│    └── Depth level                                          │
│                                                              │
│ 2. SPAWN isolated Task agent                                 │
│    ├── Fresh context (no conversation history)              │
│    ├── Adversarial persona prompt                           │
│    └── Only the collected inputs                            │
│                                                              │
│ 3. EXECUTE review in isolation                               │
│    └── Agent has no knowledge of development intent         │
│                                                              │
│ 4. RETURN structured report                                  │
│    └── Findings, gaps, recommendations                      │
└─────────────────────────────────────────────────────────────┘
```

#### Which Skills Use Isolation?

| Skill | Isolation? | Reason |
|-------|------------|--------|
| `/acceptance` | **YES** (default) | Must objectively assess requirement coverage |
| `/security` | **YES** (default) | Must assume code is vulnerable |
| `/review` | OPTIONAL (`--deep`) | Adversarial but frequently called; see [DX-70](DX-70-review-isolation.md) |
| `/refactor` | NO | Benefits from knowing design intent |
| `/debug` | NO | Benefits from recent change context |
| `/test-strategy` | NO | Benefits from understanding codebase |

#### Smart Suggestion (Self-Review Detection)

> **Note:** For `/review`, this evolved into **Mandatory Self-Review Detection** (DX-72) based on empirical evidence that optional prompting was insufficient. See [DX-72](completed/DX-72-mandatory-self-review-detection.md).

For skills with optional isolation (e.g., `/review`), detect when agent is reviewing its own code:

```
┌─────────────────────────────────────────────────────────────┐
│ SELF-REVIEW DETECTION                                        │
│                                                              │
│ Before review, check:                                        │
│ • Did agent write/edit any of the files being reviewed?     │
│ • In this session (conversation)?                           │
│                                                              │
│ If YES (self-review detected):                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⚠️ Self-review detected                                  │ │
│ │                                                          │ │
│ │ You are about to review code you wrote in this session. │ │
│ │ For maximum objectivity, consider using --deep mode.    │ │
│ │                                                          │ │
│ │ [Use --deep] [Continue normal review]                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ If NO (external code):                                      │
│ └─ Proceed with default (no prompt)                         │
└─────────────────────────────────────────────────────────────┘
```

**Detection heuristic:**
- Track files modified by agent during session
- Compare against files in review scope
- Overlap > 0 → self-review detected

**Why prompt instead of auto-deep:**
- Respects user choice
- User may have valid reason to skip (e.g., trivial change)
- Educates user about isolation benefit

#### Persona Prompts

See [Appendix: Persona Templates](#appendix-persona-templates) for full prompts.

---

## Skill Designs

### 1. `/acceptance` — Requirements Acceptance Review

**Purpose:** Verify implementation satisfies requirements with adversarial rigor.

**Triggers:** "acceptance", "check requirements", "PRD alignment", "acceptance review", "verify requirements"

**Relationship to Core Skills:**
- `/review` = Code quality (bugs, contracts, security)
- `/acceptance` = Feature completeness (requirements coverage)

#### Core Principles

| Principle | Description |
|-----------|-------------|
| **Skeptical by default** | Assume feature is NOT implemented until proven otherwise |
| **Evidence required** | "Implemented" requires file:line proof, not intuition |
| **Deep challenge** | Every requirement gets adversarial scenarios, no shortcuts |
| **Graceful degradation** | Works without Invar contracts (falls back to code analysis) |
| **Polluter pays** | External verification must restore state, or use dry-run |

#### Depth Levels

| Level | Scope | Use Case |
|-------|-------|----------|
| `--quick` | P0 (Must-have) only, skip NFR/UI | Fast feedback, CI gates |
| `--standard` | P0 + P1, sample challenges | Normal development |
| `--deep` (default) | ALL requirements, full challenge, external verify | Release readiness |

**Default is `--deep`** — thorough verification is the norm, not the exception.

#### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 0. ISOLATION CHECK                                           │
│                                                              │
│ Parse depth: --quick / --standard / --deep (default)        │
│                                                              │
│ If --deep (default):                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SPAWN ISOLATED AGENT                                     │ │
│ │                                                          │ │
│ │ Collect inputs:                                          │ │
│ │ • PRD path (smart search or user-provided)               │ │
│ │ • Design paths (if found)                                │ │
│ │ • Code scope (files/directories to review)               │ │
│ │                                                          │ │
│ │ Spawn Task agent with:                                   │ │
│ │ • QA Acceptance Reviewer persona (see Appendix)          │ │
│ │ • NO conversation history                                │ │
│ │ • Only the collected inputs                              │ │
│ │                                                          │ │
│ │ → Isolated agent executes steps 1-5 below                │ │
│ │ → Returns structured report                              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ If --quick or --standard:                                   │
│ └─ Continue in same context with persona switch            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. ENTRY (isolated or same-context)                         │
│ • Detect Invar (Enhanced/Standalone)                        │
│ • Locate PRD: smart search or user-provided path            │
│ • Locate Design: design/, mockups/, figma/ (if exists)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. PARSE — Extract Requirements                             │
│                                                              │
│ Read PRD and extract:                                       │
│ • FR (Functional): What system must DO                      │
│ • NFR (Non-Functional): Performance, security, UX           │
│ • EC (Edge Case): Explicitly mentioned scenarios            │
│ • UI (UI/UX): Visual/interaction requirements (if any)      │
│                                                              │
│ Output:                                                      │
│ | ID    | Type | Requirement              | Priority |       │
│ |-------|------|--------------------------|----------|       │
│ | FR-1  | FR   | User can login with email| Must     |       │
│ | NFR-1 | NFR  | Response time < 200ms    | Should   |       │
│ | UI-1  | UI   | Login button is blue #007| Could    |       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MAP — Link to Implementation (Skeptical)                 │
│                                                              │
│ DEFAULT STATUS: ❌ Missing (upgrade only with evidence)      │
│                                                              │
│ Evidence Sources (priority order):                          │
│ 1. Invar contracts (@pre/@post matching requirement)        │
│ 2. Type signatures + docstrings                             │
│ 3. Test cases covering the requirement                      │
│ 4. Code implementation (read and verify)                    │
│                                                              │
│ Enhanced Mode:                                               │
│ • invar_sig to find functions + contracts                   │
│ • Cross-reference contracts with requirements               │
│                                                              │
│ Standalone Mode (no contracts):                             │
│ • Grep for requirement keywords                             │
│ • Read docstrings, type hints, comments                     │
│ • Trace code flow to verify implementation                  │
│                                                              │
│ Output:                                                      │
│ | ID   | Requirement  | Evidence           | Status      |  │
│ |------|--------------|--------------------| ------------|  │
│ | FR-1 | User login   | auth.py:45 @post   | ✅ Complete |  │
│ | FR-2 | Password reset| -                 | ❌ Missing  |  │
│ | FR-3 | Email verify | email.py:30 (partial)| ⚠️ Partial|  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CHALLENGE — Deep Adversarial Scenarios (ALL requirements)│
│                                                              │
│ For EVERY requirement (no shortcuts):                       │
│                                                              │
│ Functional (FR):                                            │
│ • "What if input is empty/null/malformed?"                  │
│ • "What if user lacks permission?"                          │
│ • "What if dependent service fails?"                        │
│ • "What if called twice/concurrently?"                      │
│                                                              │
│ Non-Functional (NFR):                                       │
│ • "Is there evidence this is measured?"                     │
│ • "What's the worst-case scenario?"                         │
│ • "How does it degrade under load?"                         │
│                                                              │
│ Edge Cases (EC):                                            │
│ • "Is boundary explicitly handled?"                         │
│ • "What's the error message?"                               │
│ • "Is it tested?"                                           │
│                                                              │
│ UI/UX (UI):                                                 │
│ • "Does implementation match design spec?"                  │
│ • "Are design tokens correct (colors, spacing)?"            │
│ • "Is interaction behavior as specified?"                   │
│                                                              │
│ Output (per requirement):                                   │
│ | Scenario              | Expected     | Actual  | Gap? |   │
│ |-----------------------|--------------|---------|------|   │
│ | Wrong password 5x     | Lock account | No lock | ❌   |   │
│ | Empty email           | Error msg    | Crash   | ❌   |   │
│ | Concurrent login      | Queue/reject | Race bug| ❌   |   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VERIFY — External Tool Validation                        │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ POLLUTER PAYS PRINCIPLE                                  │ │
│ │                                                          │ │
│ │ Before running:                                          │ │
│ │ 1. Can state be restored? (snapshot, rollback, reset)    │ │
│ │    → YES: Run freely, restore after                      │ │
│ │    → NO:  Must use dry-run / read-only mode              │ │
│ │                                                          │ │
│ │ Examples:                                                │ │
│ │ • DB: Use transaction + rollback, or test DB             │ │
│ │ • Files: Backup → run → restore                          │ │
│ │ • API: Use sandbox/test endpoint                         │ │
│ │ • Destructive: MUST dry-run (--dry-run, --whatif)        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Web Projects:                                               │
│ • Playwright/Puppeteer for E2E flows                        │
│ • curl/httpie for API endpoints                             │
│ • Lighthouse for performance NFRs                           │
│                                                              │
│ CLI Projects:                                               │
│ • Actually invoke commands with test inputs                 │
│ • Verify exit codes and output format                       │
│                                                              │
│ Library Projects:                                           │
│ • Run existing test suite                                   │
│ • Execute doctest examples                                  │
│                                                              │
│ NFR Benchmarks:                                             │
│ | NFR Type      | Suggested Tool                         |  │
│ |---------------|----------------------------------------|  │
│ | Response time | `time curl`, `ab`, `wrk`, `hyperfine`  |  │
│ | Memory        | `heaptrack`, `/usr/bin/time -v`        |  │
│ | Throughput    | `wrk -t4 -c100 -d30s`                   |  │
│ | Bundle size   | `du -sh dist/`, bundlesize tools       |  │
│                                                              │
│ UI/UX Deep Verification:                                    │
│                                                              │
│ Level 1: Design Tokens                                      │
│ • Colors: Extract from CSS/Tailwind, compare to spec        │
│ • Typography: font-family, size, weight, line-height        │
│ • Spacing: padding, margin, gap values                      │
│                                                              │
│ Level 2: Layout                                             │
│ • Component positioning (flexbox/grid alignment)            │
│ • Responsive breakpoints (mobile/tablet/desktop)            │
│ • Z-index stacking order                                    │
│                                                              │
│ Level 3: Interaction                                        │
│ • Hover/focus/active states                                 │
│ • Animation timing and easing                               │
│ • Keyboard navigation (tab order, shortcuts)                │
│ • Screen reader compatibility (aria labels)                 │
│                                                              │
│ Level 4: Visual Regression (requires baseline)              │
│ • Playwright screenshot comparison                          │
│ • Percy/Chromatic integration                               │
│ • Pixel-diff with threshold                                 │
│                                                              │
│ Output:                                                      │
│ | ID    | Requirement      | Measured      | Status     |   │
│ |-------|------------------|---------------|------------|   │
│ | NFR-1 | Response < 200ms | 145ms         | ✅ Pass    |   │
│ | NFR-2 | Memory < 100MB   | 89MB          | ✅ Pass    |   │
│ | UI-1  | Button #0070f3   | #007bff       | ⚠️ Close   |   │
│ | UI-2  | 16px spacing     | 12px          | ❌ Fail    |   │
│ | UI-3  | Hover animation  | 300ms ease    | ✅ Pass    |   │
│ | UI-4  | Tab navigation   | Missing focus | ❌ Fail    |   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. REPORT — Coverage Matrix + Integration                   │
│                                                              │
│ ## Validation Report                                         │
│                                                              │
│ **PRD:** docs/requirements.md                               │
│ **Design:** design/mockups/ (if found)                      │
│ **Mode:** Enhanced (Invar detected) / Standalone            │
│                                                              │
│ ### Coverage Summary                                         │
│ | Status      | Count | Percent |                           │
│ |-------------|-------|---------|                           │
│ | ✅ Complete | 7     | 58%     |                           │
│ | ⚠️ Partial  | 3     | 25%     |                           │
│ | ❌ Missing  | 2     | 17%     |                           │
│                                                              │
│ ### Critical Gaps                                            │
│ 1. FR-2: Password reset — Not implemented                   │
│ 2. NFR-1: Response time — Not measured                      │
│                                                              │
│ ### Adversarial Findings                                     │
│ | Finding                    | Severity | Location      |   │
│ |----------------------------|----------|---------------|   │
│ | Account lockout missing    | High     | auth.py       |   │
│ | Input validation incomplete| Medium   | forms.py:23   |   │
│ | Race condition in login    | High     | session.py:45 |   │
│                                                              │
│ ### UI/UX Discrepancies (if applicable)                     │
│ | Element      | Design    | Actual    | Action       |    │
│ |--------------|-----------|-----------|--------------|    │
│ | Login button | #0070f3   | #007bff   | Update color |    │
│ | Spacing      | 16px      | 12px      | Fix padding  |    │
│                                                              │
│ ### NFR Verification Results                                 │
│ | Requirement       | Target   | Measured | Status    |    │
│ |-------------------|----------|----------|-----------|    │
│ | Response time     | < 200ms  | 145ms    | ✅ Pass   |    │
│ | Memory usage      | < 100MB  | 89MB     | ✅ Pass   |    │
│ | Concurrent users  | 100      | Untested | ⚠️ TODO   |    │
│                                                              │
│ ### Suggested /develop Tasks                                 │
│                                                              │
│ These gaps are suitable for `/develop` workflow:            │
│                                                              │
│ **High Priority (Must-have gaps):**                         │
│ 1. FR-2: Password reset                                     │
│    - Scope: auth/ module                                    │
│    - Estimate: ~80 LOC, 2 new functions                     │
│    - Dependencies: email service integration                │
│                                                              │
│ 2. Account lockout (adversarial finding)                    │
│    - Scope: auth/session.py                                 │
│    - Estimate: ~30 LOC, 1 new function                      │
│    - Add: failed_attempts counter, lockout check            │
│                                                              │
│ **Medium Priority:**                                        │
│ 3. Input validation hardening                               │
│    - Scope: forms.py, validators.py                         │
│    - Add: email format, password strength                   │
│                                                              │
│ **Verification Tasks:**                                      │
│ 4. NFR: Load test concurrent users                          │
│    - Command: `wrk -t4 -c100 -d30s http://localhost/login`  │
│                                                              │
│ ### Next Actions                                             │
│ 1. [ ] Implement FR-2 (use /develop)                        │
│ 2. [ ] Add account lockout (use /develop)                   │
│ 3. [ ] Run load test for NFR verification                   │
│ 4. [ ] Fix UI color discrepancy                             │
└─────────────────────────────────────────────────────────────┘
```

#### PRD Smart Search

```
Search order:
1. docs/prd.md, docs/PRD.md, docs/requirements.md
2. *.prd.md, *requirements*.md, *spec*.md
3. README.md (Requirements section)
4. .invar/prd.md

If multiple → ask user to select
If none → ask user for path
```

#### Design File Detection

```
Search order:
1. design/, mockups/, figma/
2. *.fig, *.sketch (metadata only)
3. docs/design/, docs/ui/
4. .invar/design/

If found → enable UI/UX verification
If not → skip UI checks, note in report
```

#### Contract Fallback Strategy

When Invar contracts are not available:

| Fallback Level | Evidence Source | Confidence |
|----------------|-----------------|------------|
| 1. Type hints | `def login(email: str) -> User` | Medium |
| 2. Docstrings | `"""Returns user if valid credentials."""` | Medium |
| 3. Test cases | `test_login_success()` exists | High |
| 4. Code trace | Read implementation, verify logic | Low |

**Important:** Without contracts, increase skepticism. Code that "looks implemented" may have subtle bugs that contracts would catch.

#### External Verification Commands

```bash
# Performance (Response Time)
time curl -s http://localhost:8000/api/endpoint
hyperfine 'curl -s http://localhost:8000/api/endpoint'
ab -n 100 -c 10 http://localhost:8000/api/endpoint

# Load Testing
wrk -t4 -c100 -d30s http://localhost:8000/api/endpoint
k6 run loadtest.js

# Memory
/usr/bin/time -v python script.py
heaptrack python script.py

# CLI Verification
./cli --help | grep "expected-command"
echo "test input" | ./cli process

# E2E (Web)
npx playwright test
npx cypress run

# Bundle Size
du -sh dist/
npx bundlesize
```

---

### 2. `/security` — Security Audit

**Purpose:** Identify security vulnerabilities using OWASP Top 10 as baseline.

**Triggers:** "security", "audit", "vulnerabilities", "OWASP"

**Relationship to Core Skills:**
- `/review` includes security as one checklist item
- `/security` is deep-dive security-focused audit

#### Core Principles

| Principle | Description |
|-----------|-------------|
| **Assume vulnerable** | Every input is malicious until proven safe |
| **Defense in depth** | Check all layers, not just obvious entry points |
| **Evidence-based** | Report with file:line and exploitation scenario |
| **Context isolated** | Fresh perspective prevents "I know this is safe" bias |

#### Depth Levels

| Level | Scope | Use Case |
|-------|-------|----------|
| `--quick` | A03 (Injection) only | Fast CI gate |
| `--standard` | A01-A05 (most common) | Regular development |
| `--deep` (default) | Full OWASP A01-A10 + isolated agent | Release audit |

#### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 0. ISOLATION CHECK                                           │
│                                                              │
│ Parse depth: --quick / --standard / --deep (default)        │
│                                                              │
│ If --deep (default):                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SPAWN ISOLATED AGENT                                     │ │
│ │                                                          │ │
│ │ Collect inputs:                                          │ │
│ │ • Code scope (files/directories to audit)                │ │
│ │ • Dependency manifest (package.json, requirements.txt)   │ │
│ │ • Config files (if any)                                  │ │
│ │                                                          │ │
│ │ Spawn Task agent with:                                   │ │
│ │ • Security Auditor persona (see Appendix)                │ │
│ │ • NO conversation history                                │ │
│ │ • Only the collected inputs                              │ │
│ │                                                          │ │
│ │ → Isolated agent executes steps 1-4 below                │ │
│ │ → Returns structured security report                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ If --quick or --standard:                                   │
│ └─ Continue in same context with attacker mindset          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. ENTRY (isolated or same-context)                         │
│ • Detect Invar (Enhanced/Standalone)                        │
│ • Identify scope (full project or specific files)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. RECONNAISSANCE — Understand Attack Surface              │
│                                                              │
│ Identify:                                                    │
│ • Entry points (APIs, forms, file uploads)                  │
│ • Data flows (user input → storage → output)                │
│ • Authentication/authorization points                       │
│ • External dependencies                                      │
│                                                              │
│ Enhanced Mode: invar_map to find entry points               │
│ Standalone: Grep for route definitions, handlers            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. OWASP CHECK — Systematic Vulnerability Scan             │
│                                                              │
│ A01: Broken Access Control                                   │
│ □ Authorization checked on all endpoints?                   │
│ □ IDOR vulnerabilities?                                     │
│ □ Missing function-level access control?                    │
│                                                              │
│ A02: Cryptographic Failures                                  │
│ □ Sensitive data encrypted at rest?                         │
│ □ Weak algorithms (MD5, SHA1)?                              │
│ □ Hardcoded secrets?                                        │
│                                                              │
│ A03: Injection                                               │
│ □ SQL injection (raw queries)?                              │
│ □ Command injection (shell exec)?                           │
│ □ XSS (unescaped output)?                                   │
│                                                              │
│ A04: Insecure Design                                         │
│ □ Missing rate limiting?                                    │
│ □ No account lockout?                                       │
│ □ Predictable tokens?                                       │
│                                                              │
│ A05: Security Misconfiguration                               │
│ □ Debug mode in production?                                 │
│ □ Default credentials?                                      │
│ □ Verbose error messages?                                   │
│                                                              │
│ A06: Vulnerable Components                                   │
│ □ Known CVEs in dependencies?                               │
│ □ Outdated packages?                                        │
│                                                              │
│ A07: Authentication Failures                                 │
│ □ Weak password policy?                                     │
│ □ Missing MFA?                                              │
│ □ Session fixation?                                         │
│                                                              │
│ A08: Data Integrity Failures                                 │
│ □ Unsigned data trusted?                                    │
│ □ Deserialization of untrusted data?                        │
│                                                              │
│ A09: Logging Failures                                        │
│ □ Security events logged?                                   │
│ □ Sensitive data in logs?                                   │
│                                                              │
│ A10: SSRF                                                    │
│ □ User-controlled URLs fetched?                             │
│ □ Internal network accessible?                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. EVIDENCE — Document Findings                             │
│                                                              │
│ For each finding:                                            │
│ • Location (file:line)                                      │
│ • Severity (Critical/High/Medium/Low)                       │
│ • Evidence (code snippet)                                   │
│ • Exploitation scenario                                     │
│ • Remediation suggestion                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. REPORT — Security Audit Report                           │
│                                                              │
│ ## Security Audit Report                                     │
│                                                              │
│ **Scope:** src/api/, src/auth/                              │
│ **Date:** 2026-01-01                                        │
│ **Mode:** Enhanced                                           │
│                                                              │
│ ### Summary                                                  │
│ | Severity | Count |                                        │
│ |----------|-------|                                        │
│ | Critical | 1     |                                        │
│ | High     | 2     |                                        │
│ | Medium   | 3     |                                        │
│ | Low      | 1     |                                        │
│                                                              │
│ ### Critical Findings                                        │
│                                                              │
│ **[CRITICAL] SQL Injection in user search**                 │
│ - Location: api/users.py:45                                 │
│ - Evidence: `query = f"SELECT * FROM users WHERE name='{n}'"│
│ - Risk: Full database compromise                            │
│ - Fix: Use parameterized queries                            │
│                                                              │
│ ### Recommendations                                          │
│ 1. [URGENT] Fix SQL injection                               │
│ 2. Add rate limiting to login endpoint                      │
│ 3. Implement account lockout                                │
└─────────────────────────────────────────────────────────────┘
```

#### External Tool Integration

Auto-detect and run external security tools when available:

```
┌─────────────────────────────────────────────────────────────┐
│ TOOL DETECTION & EXECUTION                                   │
│                                                              │
│ 1. Detect project type from manifest files                  │
│ 2. Check if tool is available (which/command -v)            │
│ 3. Run tool and parse JSON output                           │
│ 4. Merge findings into OWASP categories                     │
│                                                              │
│ If tool not available → note in report, continue manually   │
└─────────────────────────────────────────────────────────────┘
```

| Project Type | Tool | OWASP | Command |
|--------------|------|-------|---------|
| Node.js | `npm audit` | A06 | `npm audit --json` |
| Python | `pip-audit` | A06 | `pip-audit --format=json` |
| Go | `govulncheck` | A06 | `govulncheck -json ./...` |
| Any | `trufflehog` | A02 | `trufflehog git file://. --json` |
| Any | `semgrep` | A01-A10 | `semgrep --config=auto --json` |

#### Language-Specific Pattern Architecture

Patterns are separated by language for accuracy:

```
security/patterns/
├── _common.yaml      # Cross-language (secrets, weak random)
├── python.yaml       # Python-specific (pickle, eval, SQL)
├── typescript.yaml   # TS/JS-specific (XSS, prototype pollution)
├── go.yaml           # Go-specific (race conditions, unsafe)
└── java.yaml         # Java-specific (deserialization, JNDI)
```

**Pattern YAML structure:**
```yaml
# python.yaml
extends: _common
patterns:
  sql_injection:
    category: A03
    severity: Critical
    description: "SQL injection via string formatting"
    regex:
      - 'f"[^"]*SELECT[^"]*\{[^}]+\}'
      - '\.format\([^)]*\)[^"]*SELECT'
    false_positive_hints:
      - "Check if ORM parameterization is used"
```

**Loading logic:**
1. Detect language(s) from manifest files
2. Load `_common.yaml` always
3. Load language-specific YAML(s)
4. Merge patterns (language-specific overrides common)

#### Severity Classification

```
┌─────────────────────────────────────────────────────────────┐
│ SEVERITY DECISION TREE                                       │
│                                                              │
│     Can attacker execute arbitrary code?                    │
│         │                                                    │
│    YES ─┴─ NO                                               │
│     │      │                                                 │
│     ▼      ▼                                                 │
│ CRITICAL   Can read/write sensitive data?                   │
│                │                                             │
│           YES ─┴─ NO                                        │
│            │      │                                          │
│            ▼      ▼                                          │
│          HIGH     Can access limited data / disrupt service?│
│                       │                                      │
│                  YES ─┴─ NO                                 │
│                   │      │                                   │
│                   ▼      ▼                                   │
│                MEDIUM   LOW                                  │
└─────────────────────────────────────────────────────────────┘
```

| Severity | Impact | Examples |
|----------|--------|----------|
| **Critical** | Complete system compromise | RCE, SQL injection (write), command injection, hardcoded admin creds |
| **High** | Significant data breach | SQL injection (read), stored XSS, session hijacking, IDOR (multi-user) |
| **Medium** | Limited exposure | Reflected XSS, user enumeration, missing rate limiting, MD5/SHA1 |
| **Low** | Minimal direct impact | Missing security headers, debug info, outdated deps (no known exploit) |

#### False Positive Handling

Persist baseline to avoid re-flagging confirmed false positives:

```yaml
# .invar/security-baseline.yaml
version: 1
findings:
  SEC-2024-001:
    pattern: sql_injection
    file: src/db/queries.py
    line: 45
    content_hash: "a1b2c3d4"  # Re-evaluate if code changes
    status: false_positive
    reason: "ORM handles parameterization"
    marked_by: "dev@example.com"
    marked_at: "2026-01-01T10:30:00Z"
    
  SEC-2024-002:
    pattern: hardcoded_secrets
    file: src/config/test.py
    status: accepted_risk
    reason: "Test-only credentials"
    expires: "2026-06-01"  # Re-evaluate after expiry
```

| Status | Meaning | Behavior |
|--------|---------|----------|
| `false_positive` | Not a real vulnerability | Suppress permanently (unless code changes) |
| `accepted_risk` | Real but accepted | Suppress, can set expiry date |
| `wont_fix` | Won't be fixed | Suppress, still counted in stats |
| `in_progress` | Being fixed | Show but don't block |

**Report integration:**
```markdown
### New Findings (3)
| ID | Severity | Location | Description |
|----|----------|----------|-------------|
| SEC-2024-010 | Critical | api/users.py:45 | SQL injection |

### Baselined (2)
| ID | Status | Reason |
|----|--------|--------|
| SEC-2024-001 | false_positive | ORM handles escaping |
```

---

---

## T1 Skills (Pending Discussion)

> **Status:** The following T1 skills have draft designs. Review and discussion required before implementation.

---

### 3. `/refactor` — Refactoring Strategy

> ⚠️ **Pending Discussion** — Review design before implementation

**Purpose:** Guide safe, systematic refactoring of complex code.

**Triggers:** "refactor", "clean up", "simplify", "restructure"

**Relationship to Core Skills:**
- `/develop` = build new features
- `/refactor` = improve existing code without changing behavior

#### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ ENTRY                                                        │
│ • Identify refactoring target (file, module, function)      │
│ • Detect Invar (Enhanced/Standalone)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. ANALYZE — Identify Code Smells                           │
│                                                              │
│ Check for:                                                   │
│ □ Long functions (>50 lines)                                │
│ □ Deep nesting (>3 levels)                                  │
│ □ Duplicated code                                           │
│ □ God class (too many responsibilities)                     │
│ □ Feature envy (method uses other class's data)             │
│ □ Primitive obsession (should be value object)              │
│ □ Long parameter list (>4 params)                           │
│ □ Dead code (unused functions/variables)                    │
│                                                              │
│ Enhanced Mode: invar_guard for size violations              │
│ Standalone: Manual analysis                                  │
│                                                              │
│ Output: Smell table with severity                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. STRATEGIZE — Plan Refactoring Approach                   │
│                                                              │
│ For each smell, suggest strategy:                           │
│                                                              │
│ | Smell            | Strategy                    | Risk |   │
│ |------------------|-----------------------------| -----|   │
│ | Long function    | Extract Method              | Low  |   │
│ | Deep nesting     | Replace with Guard Clauses  | Low  |   │
│ | Duplication      | Extract Common Function     | Med  |   │
│ | God class        | Split by Responsibility     | High |   │
│                                                              │
│ Prioritize by: Risk (low first) → Impact (high first)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SAFE STEPS — Incremental Refactoring                     │
│                                                              │
│ For each refactoring:                                       │
│                                                              │
│ Step 1: Ensure tests exist (or add characterization tests)  │
│ Step 2: Make ONE small change                               │
│ Step 3: Run tests (invar_guard or test command)             │
│ Step 4: Commit if green                                     │
│ Step 5: Repeat                                              │
│                                                              │
│ STOP CONDITIONS:                                             │
│ • Test failure → revert, analyze                            │
│ • Behavior change detected → revert, reconsider             │
│ • Time limit reached → commit progress, pause               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VERIFY — Confirm Behavior Preserved                      │
│                                                              │
│ Enhanced Mode:                                               │
│ • invar_guard (includes property tests)                     │
│ • Contract verification unchanged                            │
│                                                              │
│ Standalone Mode:                                             │
│ • Run existing test suite                                   │
│ • Manual smoke test                                         │
│                                                              │
│ Output: Before/After comparison                              │
│ • Lines of code: 450 → 320                                  │
│ • Max function length: 120 → 45                             │
│ • Nesting depth: 5 → 3                                      │
│ • Tests: All passing                                        │
└─────────────────────────────────────────────────────────────┘
```

---

### 4. `/debug` — Root Cause Analysis

> ⚠️ **Pending Discussion** — Review design before implementation

**Purpose:** Systematically find root cause of bugs and errors.

**Triggers:** "debug", "why does", "root cause", "error", "bug"

**Relationship to Core Skills:**
- `/investigate` = understand how code works
- `/debug` = understand why code fails

#### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ ENTRY                                                        │
│ • Gather error information (message, stack trace, logs)     │
│ • Detect Invar (Enhanced/Standalone)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. OBSERVE — Collect Evidence                               │
│                                                              │
│ Gather:                                                      │
│ • Error message (exact text)                                │
│ • Stack trace (full trace)                                  │
│ • Reproduction steps (if known)                             │
│ • Environment (version, config)                             │
│ • Recent changes (git log)                                  │
│                                                              │
│ Questions to ask:                                            │
│ • When did this start happening?                            │
│ • Does it happen consistently or intermittently?            │
│ • What was changed recently?                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. HYPOTHESIZE — Generate Possible Causes                   │
│                                                              │
│ Based on evidence, generate hypotheses:                     │
│                                                              │
│ | # | Hypothesis                        | Likelihood |      │
│ |---|-----------------------------------|------------|      │
│ | 1 | Null pointer from uninitialized var| High      |      │
│ | 2 | Race condition in async code       | Medium    |      │
│ | 3 | External API returning unexpected  | Medium    |      │
│ | 4 | Config mismatch between envs       | Low       |      │
│                                                              │
│ Prioritize by: Likelihood × Ease of verification            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TEST — Verify Hypotheses                                 │
│                                                              │
│ For each hypothesis (highest priority first):               │
│                                                              │
│ [H1] Null pointer from uninitialized var                    │
│   • Check: Read code at stack trace location                │
│   • Evidence: Found `user.name` without null check          │
│   • Result: ✅ CONFIRMED                                    │
│                                                              │
│ If confirmed → proceed to FIX                               │
│ If not confirmed → test next hypothesis                     │
│ If all exhausted → gather more evidence                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. FIX — Implement Solution                                 │
│                                                              │
│ Root Cause: Null pointer in user.name access                │
│ Location: api/handlers.py:78                                │
│                                                              │
│ Fix Options:                                                 │
│ A. Add null check before access (quick fix)                 │
│ B. Ensure user always initialized (proper fix)              │
│ C. Add Optional type + handling (defensive fix)             │
│                                                              │
│ Recommendation: Option B (addresses root cause)             │
│                                                              │
│ After fix:                                                   │
│ • Verify error no longer occurs                             │
│ • Add test to prevent regression                            │
│ • Document in commit message                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. PREVENT — Add Safeguards                                 │
│                                                              │
│ • Add regression test for this bug                          │
│ • Consider: Should contract catch this?                     │
│ • Consider: Are there similar patterns elsewhere?           │
│                                                              │
│ Enhanced Mode:                                               │
│ • Suggest @pre/@post contract to prevent recurrence         │
│ • Run invar_guard to verify fix                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 5. `/test-strategy` — Test Strategy Design

> ⚠️ **Pending Discussion** — Review design before implementation

**Purpose:** Design comprehensive test strategy for a feature or module.

**Triggers:** "test strategy", "how to test", "what to test", "testing plan"

**Relationship to Core Skills:**
- `/develop` writes tests as part of USBV
- `/test-strategy` designs testing approach before writing tests

#### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ ENTRY                                                        │
│ • Identify testing target (feature, module, API)            │
│ • Detect Invar (Enhanced/Standalone)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. UNDERSTAND — Analyze Testable Behaviors                  │
│                                                              │
│ For target, identify:                                        │
│ • Inputs (parameters, state, external)                      │
│ • Outputs (return values, side effects, events)             │
│ • Invariants (always true conditions)                       │
│ • State transitions (if stateful)                           │
│                                                              │
│ Enhanced Mode: invar_sig shows contracts (test hints)       │
│ Standalone: Read code to understand behavior                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CATEGORIZE — Test Types Needed                           │
│                                                              │
│ □ Unit Tests                                                │
│   • Pure functions → property-based tests                   │
│   • Complex logic → example-based tests                     │
│                                                              │
│ □ Integration Tests                                         │
│   • Database interactions                                   │
│   • External API calls                                      │
│   • Cross-module flows                                      │
│                                                              │
│ □ Contract Tests                                            │
│   • @pre violations should raise                            │
│   • @post guarantees hold                                   │
│                                                              │
│ □ Edge Case Tests                                           │
│   • Boundary values                                         │
│   • Empty inputs                                            │
│   • Error conditions                                        │
│                                                              │
│ □ Property Tests                                            │
│   • Invariants that hold for all inputs                     │
│   • Round-trip properties                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PRIORITIZE — Test Priority Matrix                        │
│                                                              │
│ | Test Case          | Risk | Frequency | Priority |        │
│ |--------------------|------|-----------|----------|        │
│ | Login success      | High | High      | P0       |        │
│ | Login wrong pass   | High | Medium    | P0       |        │
│ | Password reset     | High | Low       | P1       |        │
│ | Profile update     | Low  | Medium    | P2       |        │
│                                                              │
│ Priority = Risk × (Frequency + 1)                           │
│ P0 = Must have, P1 = Should have, P2 = Nice to have         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. DESIGN — Test Case Specifications                        │
│                                                              │
│ ## Test Plan: User Authentication                           │
│                                                              │
│ ### P0: Critical Path                                        │
│                                                              │
│ **TC-1: Login with valid credentials**                      │
│ - Given: User exists with email/password                    │
│ - When: POST /login with correct credentials                │
│ - Then: 200 OK, JWT token returned                          │
│ - Property: Token is valid JWT with user_id claim           │
│                                                              │
│ **TC-2: Login with wrong password**                         │
│ - Given: User exists                                        │
│ - When: POST /login with wrong password                     │
│ - Then: 401 Unauthorized                                    │
│ - Edge: 5 failed attempts → account locked                  │
│                                                              │
│ ### P1: Important                                            │
│                                                              │
│ **TC-3: Password reset flow**                               │
│ - Given: User exists                                        │
│ - When: Request reset, use token                            │
│ - Then: Password changed, old token invalidated             │
│                                                              │
│ ### Property Tests                                           │
│                                                              │
│ **PROP-1: Token validation is symmetric**                   │
│ - ∀ user: decode(encode(user)) == user                      │
│                                                              │
│ **PROP-2: Failed login count increases monotonically**      │
│ - ∀ failures: count_after >= count_before                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. COVERAGE — Gap Analysis                                  │
│                                                              │
│ Check against requirements:                                  │
│ • All PRD requirements have tests? (link to /acceptance)      │
│ • All contracts have tests?                                 │
│ • Edge cases covered?                                       │
│                                                              │
│ Enhanced Mode: Cross-reference with invar_guard coverage    │
│                                                              │
│ Output: Coverage gaps list                                  │
│ • Missing: Account lockout test                             │
│ • Missing: Token expiry test                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### CLI Commands (DX-71)

```bash
invar skill list              # List available/installed extensions
invar skill add acceptance    # Install OR update (idempotent, preserves extensions region)
invar skill remove acceptance # Remove (prompts if no custom extensions)
invar skill remove acceptance --force  # Remove without prompt (even with custom extensions)
```

**Note:** `invar skill update` is deprecated — use `invar skill add` instead (same behavior, idempotent).

### Manual Copy

```bash
cp -r /path/to/extensions/acceptance .claude/skills/
```

---

## Implementation Plan

### Phase 1: Architecture (3 days) ✅ COMPLETE

| Task | Deliverable | Status |
|------|-------------|--------|
| Create `extensions/` directory | Directory structure | ✅ |
| Implement `_registry.yaml` | Extension metadata | ✅ |
| Add `invar skill` CLI | list, add, remove, update | ✅ |

### Phase 2: T0 Extensions (6 days)

| Task | Days | Deliverable |
|------|------|-------------|
| `/acceptance` skill | 3 | SKILL.md + README |
| `/security` skill | 3 | SKILL.md + README |

### Phase 3: T1 Extensions (6 days) — ⚠️ Requires Discussion

> **Blocker:** Review T1 skill designs before starting implementation.

| Task | Days | Deliverable | Status |
|------|------|-------------|--------|
| Review `/refactor` design | — | Design approval | Pending |
| Review `/debug` design | — | Design approval | Pending |
| Review `/test-strategy` design | — | Design approval | Pending |
| `/refactor` skill | 2 | SKILL.md + README | Blocked |
| `/debug` skill | 2 | SKILL.md + README | Blocked |
| `/test-strategy` skill | 2 | SKILL.md + README | Blocked |

### Phase 4: Testing & Polish (2 days)

| Task | Deliverable |
|------|-------------|
| Integration testing | Test in isolated projects |
| Documentation | Update INVAR.md references |

**Total: 17 days**

---

## Success Criteria

### Phase 1 ✅
- [x] `invar skill list` shows 6 extensions (including invar-onboard)
- [x] `invar skill add acceptance` works
- [x] Manual copy installation works

### Phase 2
- [ ] `/acceptance` produces coverage matrix
- [ ] `/acceptance` spawns isolated agent in --deep mode
- [ ] `/security` covers OWASP Top 10
- [ ] `/security` spawns isolated agent in --deep mode
- [ ] Both work in standalone mode (no Invar)

### Phase 3
- [ ] `/refactor` identifies smells and suggests safe steps
- [ ] `/debug` follows hypothesis-test cycle
- [ ] `/test-strategy` produces prioritized test plan

---

## Open Questions

### Q1: Remediation Plan Verification (Pending Discussion)

**Problem:** After `/acceptance` generates a validation report, how should the agent generate and verify a remediation plan?

**Current State:**
- `/acceptance` Step 6 outputs "Suggested /develop Tasks"
- No verification that plan actually covers all gaps
- Same agent generates report and plan → confirmation bias risk

**Proposed Enhancement:**

```
/acceptance --deep
├── Phase 1: Validation (ISOLATED)
│   → QA Reviewer persona
│   → Generate validation report
│   → Return to main context
│
├── Phase 2: Planning (SAME CONTEXT)
│   → Read report, generate remediation plan
│   → Build Gap Coverage Matrix (mechanical verification)
│   → Flag any gaps without tasks
│
├── Phase 3: Plan Review (ISOLATED, DIFFERENT AGENT)
│   → NEW agent with "Plan Critic" persona
│   → Input: Report + Plan
│   → Task: "Find flaws in this plan. Assume it has problems."
│   → Output: Approved / Needs Revision / Rejected
│
└── Phase 4: User Confirmation
    → Present verified plan
    → User confirms or modifies
```

**Two Types of Verification:**

| Type | Nature | Agent Self-Check? |
|------|--------|-------------------|
| Coverage | Mechanical: Gap → Task mapping | ✅ OK |
| Quality | Subjective: Is plan correct? | ❌ Needs isolation |

**Plan Critic Persona (Draft):**

```markdown
# Plan Critic

You are reviewing a remediation plan against a validation report.

## CRITICAL RULES

1. ASSUME the plan has flaws — your job is to find them
2. For each task, ask: "Will this ACTUALLY fix the gap?"
3. Check for:
   - Missing steps
   - Wrong assumptions
   - Dependencies not considered
   - Edge cases not handled
4. Be adversarial, not confirming

## OUTPUT

- List of issues found (or "None")
- Verdict: APPROVED / NEEDS REVISION / REJECTED
```

**Alternative Approaches:**

| Approach | Description | Trade-off |
|----------|-------------|-----------|
| A: Embedded phases | Add Phase 3-4 to /acceptance | Single skill, complex |
| B: Separate /plan + /review-plan | New skills | Modular, more context switching |
| C: User-only verification | Show matrix, user decides | Simple, requires user expertise |

**Decision:** Pending discussion. Currently `/acceptance` outputs basic suggestions without verification.

---

## References

- LX-05: Language-Agnostic Protocol (skill templates)
- LX-08: Extension Skills — Future Candidates (deferred skills)
- OWASP Top 10: https://owasp.org/www-project-top-ten/

---

## Appendix: Persona Templates

### QA Acceptance Reviewer Persona

Used by `/acceptance` in `--deep` mode:

```markdown
# QA Acceptance Reviewer

You are an independent QA Acceptance Reviewer performing a requirements validation.

## CRITICAL RULES

1. **You have NEVER seen this code before**
   - Do not assume anything works
   - Do not trust developer explanations
   - Verify everything from first principles

2. **You do NOT know what the developer intended**
   - Only requirements matter, not intent
   - If it's not in the PRD, it's not a requirement
   - If it's not in the code, it's not implemented

3. **Assume NOTHING works until you verify evidence**
   - Default status is ❌ Missing
   - Upgrade to ⚠️ Partial only with partial evidence
   - Upgrade to ✅ Complete only with file:line proof

4. **Your job is to FIND GAPS, not confirm success**
   - You are not here to make developers happy
   - You are here to protect users from incomplete features
   - Every unchallenged assumption is a potential bug

5. **Be adversarial — challenge every claim**
   - "What if the input is malformed?"
   - "What if the service fails?"
   - "What if called twice concurrently?"

## INPUT YOU WILL RECEIVE

- PRD/Requirements document
- Code files to review
- Design specs (optional)

## INPUT YOU WILL NOT RECEIVE

- Development conversation history
- Developer's explanations of "what I meant"
- Prior context about design decisions

## OUTPUT FORMAT

Produce a structured Validation Report with:
1. Requirements coverage matrix
2. Evidence for each requirement
3. Adversarial findings
4. Suggested /develop tasks
```

### Security Auditor Persona

Used by `/security` in `--deep` mode:

```markdown
# Security Auditor

You are an independent Security Auditor performing a vulnerability assessment.

## CRITICAL RULES

1. **Assume all code is vulnerable until proven secure**
   - Every input is malicious
   - Every external call is compromised
   - Every secret is leaked

2. **Think like an attacker**
   - How would I exploit this?
   - What's the easiest path to compromise?
   - What would a script kiddie try first?

3. **Check all layers, not just obvious entry points**
   - Frontend validation can be bypassed
   - API middleware can be skipped
   - Database constraints can be circumvented

4. **Provide exploitation scenarios**
   - Don't just say "vulnerable to XSS"
   - Show: "Input `<script>alert(1)</script>` in field X renders unescaped at Y"

5. **Prioritize by impact, not likelihood**
   - SQL injection with low likelihood = CRITICAL
   - Information disclosure with high likelihood = MEDIUM

## OWASP TOP 10 CHECKLIST

You MUST check every item in A01-A10:
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable Components
- A07: Authentication Failures
- A08: Data Integrity Failures
- A09: Logging Failures
- A10: SSRF

## INPUT YOU WILL RECEIVE

- Code files to audit
- Dependency manifests
- Configuration files

## INPUT YOU WILL NOT RECEIVE

- Developer assurances ("this is only internal")
- Prior security review results
- Context about "trusted" inputs

## OUTPUT FORMAT

Produce a structured Security Report with:
1. Attack surface summary
2. Findings by OWASP category
3. Severity ratings (Critical/High/Medium/Low)
4. Evidence (file:line + exploitation scenario)
5. Remediation recommendations
```

### Code Reviewer Persona (Optional for /review)

Used by `/review` when isolation is requested:

```markdown
# Adversarial Code Reviewer

You are an independent Code Reviewer with a REJECTION-FIRST mindset.

## CRITICAL RULES

1. **Code is GUILTY until proven INNOCENT**
   - Assume every function has bugs
   - Assume every edge case is unhandled
   - Assume every contract is incomplete

2. **You did NOT write this code**
   - No emotional attachment
   - No "I know what I meant"
   - Pure objective analysis

3. **Find reasons to REJECT, not accept**
   - Missing error handling = REJECT
   - Incomplete contracts = REJECT
   - Unclear logic = REJECT

4. **Be specific and actionable**
   - Don't say "could be better"
   - Say "file.py:45 - missing null check for user.email"

## INPUT YOU WILL RECEIVE

- Code files to review
- Contracts (if available)
- Test files (if available)

## OUTPUT FORMAT

Produce a structured Review Report with:
1. Verdict: APPROVED / NEEDS WORK / REJECTED
2. Critical issues (must fix)
3. Major issues (should fix)
4. Minor issues (nice to fix)
5. Positive observations (what's done well)
```

---

*Proposal v2.2 — 5 Core Extension Skills with Context Isolation*
