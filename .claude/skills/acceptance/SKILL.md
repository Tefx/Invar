---
name: acceptance
description: Verify implementation satisfies requirements with adversarial rigor. PRD alignment review, checking that all requirements are implemented and edge cases are handled.
_invar:
  version: "1.0"
  managed: skill
---
<!--invar:skill-->
# /acceptance — Requirements Acceptance Review

> Extension Skill | Tier: T0 | Isolation: Default

## Purpose

Verify implementation satisfies requirements with adversarial rigor. This skill performs PRD alignment review, checking that all requirements are implemented and edge cases are handled.

## Triggers

Use this skill when user says: "acceptance", "check requirements", "PRD alignment", "acceptance review", "verify requirements"

## Relationship to Core Skills

- `/review` = Code quality (bugs, contracts, security)
- `/acceptance` = Feature completeness (requirements coverage)

---

## Core Principles

| Principle | Description |
|-----------|-------------|
| **Skeptical by default** | Assume feature is NOT implemented until proven otherwise |
| **Evidence required** | "Implemented" requires file:line proof, not intuition |
| **Deep challenge** | Every requirement gets adversarial scenarios, no shortcuts |
| **Graceful degradation** | Works without Invar contracts (falls back to code analysis) |
| **Polluter pays** | External verification must restore state, or use dry-run |

---

## Depth Levels

| Level | Scope | Use Case |
|-------|-------|----------|
| `--quick` | P0 (Must-have) only, skip NFR/UI | Fast feedback, CI gates |
| `--standard` | P0 + P1, sample challenges | Normal development |
| `--deep` (default) | ALL requirements, full challenge, external verify | Release readiness |

**Default is `--deep`** — thorough verification is the norm.

---

## Workflow

### Step 0: Isolation Check

```
Parse depth: --quick / --standard / --deep (default)

If --deep (default):
┌─────────────────────────────────────────────────────────┐
│ SPAWN ISOLATED AGENT                                     │
│                                                          │
│ Collect inputs:                                          │
│ • PRD path (smart search or user-provided)               │
│ • Design paths (if found)                                │
│ • Code scope (files/directories to review)               │
│                                                          │
│ Spawn Task agent with:                                   │
│ • QA Acceptance Reviewer persona (see below)             │
│ • NO conversation history                                │
│ • Only the collected inputs                              │
│                                                          │
│ → Isolated agent executes steps 1-5 below                │
│ → Returns structured report                              │
└─────────────────────────────────────────────────────────┘

If --quick or --standard:
└─ Continue in same context with persona switch
```

### Step 1: Entry

- Detect Invar (Enhanced/Standalone mode)
- Locate PRD: smart search or user-provided path
- Locate Design: design/, mockups/, figma/ (if exists)

**Invar Detection:**
- File-based: `INVAR.md` exists OR `.invar/` directory exists
- Context-based: `invar_guard` tool available in session
- Enhanced Mode → Use invar_guard, invar_sig, invar_map
- Standalone Mode → Use Read, Grep, Glob, Bash only

### Step 2: Parse — Extract Requirements

Read PRD and extract:
- **FR (Functional):** What system must DO
- **NFR (Non-Functional):** Performance, security, UX
- **EC (Edge Case):** Explicitly mentioned scenarios
- **UI (UI/UX):** Visual/interaction requirements (if any)

**Output format:**
```markdown
| ID    | Type | Requirement              | Priority |
|-------|------|--------------------------|----------|
| FR-1  | FR   | User can login with email| Must     |
| NFR-1 | NFR  | Response time < 200ms    | Should   |
| UI-1  | UI   | Login button is blue #007| Could    |
```

### Step 3: Map — Link to Implementation (Skeptical)

**DEFAULT STATUS: ❌ Missing** (upgrade only with evidence)

**Evidence Sources (priority order):**
1. Invar contracts (@pre/@post matching requirement)
2. Type signatures + docstrings
3. Test cases covering the requirement
4. Code implementation (read and verify)

**Enhanced Mode:**
- `invar_sig` to find functions + contracts
- Cross-reference contracts with requirements

**Standalone Mode (no contracts):**
- Grep for requirement keywords
- Read docstrings, type hints, comments
- Trace code flow to verify implementation

**Output format:**
```markdown
| ID   | Requirement  | Evidence           | Status      |
|------|--------------|--------------------| ------------|
| FR-1 | User login   | auth.py:45 @post   | ✅ Complete |
| FR-2 | Password reset| -                 | ❌ Missing  |
| FR-3 | Email verify | email.py:30 (partial)| ⚠️ Partial|
```

### Step 4: Challenge — Deep Adversarial Scenarios

For **EVERY** requirement (no shortcuts):

**Functional (FR):**
- "What if input is empty/null/malformed?"
- "What if user lacks permission?"
- "What if dependent service fails?"
- "What if called twice/concurrently?"

**Non-Functional (NFR):**
- "Is there evidence this is measured?"
- "What's the worst-case scenario?"
- "How does it degrade under load?"

**Edge Cases (EC):**
- "Is boundary explicitly handled?"
- "What's the error message?"
- "Is it tested?"

**UI/UX (UI):**
- "Does implementation match design spec?"
- "Are design tokens correct (colors, spacing)?"
- "Is interaction behavior as specified?"

**Output format:**
```markdown
| Scenario              | Expected     | Actual  | Gap? |
|-----------------------|--------------|---------|------|
| Wrong password 5x     | Lock account | No lock | ❌   |
| Empty email           | Error msg    | Crash   | ❌   |
| Concurrent login      | Queue/reject | Race bug| ❌   |
```

### Step 5: Verify — External Tool Validation

**POLLUTER PAYS PRINCIPLE:**
```
Before running external verification:
1. Can state be restored? (snapshot, rollback, reset)
   → YES: Run freely, restore after
   → NO:  Must use dry-run / read-only mode

Examples:
• DB: Use transaction + rollback, or test DB
• Files: Backup → run → restore
• API: Use sandbox/test endpoint
• Destructive: MUST dry-run (--dry-run, --whatif)
```

**Web Projects:**
- Playwright/Puppeteer for E2E flows
- curl/httpie for API endpoints
- Lighthouse for performance NFRs

**CLI Projects:**
- Actually invoke commands with test inputs
- Verify exit codes and output format

**Library Projects:**
- Run existing test suite
- Execute doctest examples

**NFR Benchmarks:**
```bash
# Response Time
time curl -s http://localhost:8000/api/endpoint
hyperfine 'curl -s http://localhost:8000/api/endpoint'

# Load Testing
wrk -t4 -c100 -d30s http://localhost:8000/api/endpoint

# Memory
/usr/bin/time -v python script.py
```

**UI/UX Deep Verification (4 levels):**
1. **Level 1: Design Tokens** — Colors, Typography, Spacing
2. **Level 2: Layout** — Flexbox/Grid alignment, Responsive breakpoints
3. **Level 3: Interaction** — Hover/focus states, Animation, Keyboard nav
4. **Level 4: Visual Regression** — Screenshot comparison (if baseline exists)

### Step 6: Report — Coverage Matrix + Integration

```markdown
## Validation Report

**PRD:** docs/requirements.md
**Design:** design/mockups/ (if found)
**Mode:** Enhanced (Invar detected) / Standalone

### Coverage Summary
| Status      | Count | Percent |
|-------------|-------|---------|
| ✅ Complete | 7     | 58%     |
| ⚠️ Partial  | 3     | 25%     |
| ❌ Missing  | 2     | 17%     |

### Critical Gaps
1. FR-2: Password reset — Not implemented
2. NFR-1: Response time — Not measured

### Adversarial Findings
| Finding                    | Severity | Location      |
|----------------------------|----------|---------------|
| Account lockout missing    | High     | auth.py       |
| Input validation incomplete| Medium   | forms.py:23   |

### UI/UX Discrepancies (if applicable)
| Element      | Design    | Actual    | Action       |
|--------------|-----------|-----------|--------------|
| Login button | #0070f3   | #007bff   | Update color |

### NFR Verification Results
| Requirement       | Target   | Measured | Status    |
|-------------------|----------|----------|-----------|
| Response time     | < 200ms  | 145ms    | ✅ Pass   |
| Memory usage      | < 100MB  | 89MB     | ✅ Pass   |

### Suggested /develop Tasks

**High Priority (Must-have gaps):**
1. FR-2: Password reset
   - Scope: auth/ module
   - Estimate: ~80 LOC, 2 new functions

2. Account lockout (adversarial finding)
   - Scope: auth/session.py
   - Estimate: ~30 LOC

### Next Actions
1. [ ] Implement FR-2 (use /develop)
2. [ ] Add account lockout (use /develop)
3. [ ] Run load test for NFR verification
```

---

## PRD Smart Search

When user says "PRD" without path:

```
Search order:
1. docs/prd.md, docs/PRD.md, docs/requirements.md
2. *.prd.md, *requirements*.md, *spec*.md
3. README.md (Requirements section)
4. .invar/prd.md

If multiple → ask user to select
If none → ask user for path
```

---

## Design File Detection

```
Search order:
1. design/, mockups/, figma/
2. *.fig, *.sketch (metadata only)
3. docs/design/, docs/ui/
4. .invar/design/

If found → enable UI/UX verification
If not → skip UI checks, note in report
```

---

## Contract Fallback Strategy

When Invar contracts are not available:

| Fallback Level | Evidence Source | Confidence |
|----------------|-----------------|------------|
| 1. Type hints | `def login(email: str) -> User` | Medium |
| 2. Docstrings | `"""Returns user if valid credentials."""` | Medium |
| 3. Test cases | `test_login_success()` exists | High |
| 4. Code trace | Read implementation, verify logic | Low |

**Important:** Without contracts, increase skepticism. Code that "looks implemented" may have subtle bugs.

---

## QA Acceptance Reviewer Persona

Used in `--deep` mode (isolated agent):

```
You are an independent QA Acceptance Reviewer.

CRITICAL RULES:
1. You have NEVER seen this code before
2. You do NOT know what the developer intended
3. Assume NOTHING works until you verify evidence
4. Your job is to FIND GAPS, not confirm success
5. Be adversarial — challenge every claim

INPUT YOU WILL RECEIVE:
- PRD/Requirements document
- Code files to review
- Design specs (optional)

INPUT YOU WILL NOT RECEIVE:
- Development conversation history
- Developer's explanations
- Prior context about design decisions

OUTPUT: Structured Validation Report (see Step 6)
```

---

## CLI Override

Override isolation level per-invocation:

```
/acceptance              → Uses --deep (default, spawns isolated agent)
/acceptance --quick      → Same context, persona hint only
/acceptance --standard   → Same context, persona switch
/acceptance --deep       → Spawns isolated agent (explicit)
```

**No external configuration required.** Defaults are in this SKILL.md.

---

## Installation

```bash
# Via CLI
invar skill add acceptance

# Manual copy
cp -r /path/to/extensions/acceptance .claude/skills/
```

---

*Extension Skill v1.0 — LX-07*
<!--/invar:skill--><!--invar:extensions-->
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Custom acceptance criteria templates
     - Project-specific requirement categories
     - Domain-specific validation rules
     ======================================================================== -->
<!--/invar:extensions-->
