---
name: invar-onboard
description: Evaluate and plan migration of existing (legacy) projects to the Invar framework. Provides structured assessment, discussion, and planning workflow.
_invar:
  version: "1.0"
  managed: skill
---
<!--invar:skill-->
# /invar-onboard — Legacy Project Onboarding

> Extension Skill | Tier: T1 | Isolation: Default

## Purpose

Evaluate and plan migration of existing (legacy) projects to the Invar framework. Provides structured assessment, discussion, and planning workflow.

## Triggers

Use this skill when user says: "onboard", "migrate to invar", "can this project use invar", "invar assessment"

## Relationship to Core Skills

| Skill | Purpose | Timing |
|-------|---------|--------|
| `/invar-onboard` | One-time migration assessment | Before Invar adoption |
| `/develop` | Day-to-day implementation | After Invar adoption |
| `/review` | Code quality verification | After Invar adoption |

```
Non-Invar Project → /invar-onboard → Invar Project → /develop, /review
                    (one-time)                      (continuous)
```

---

## Core Principles

| Principle | Description |
|-----------|-------------|
| **Claude as parser** | Use LLM understanding, no language-specific code |
| **Deep analysis only** | Refactoring is major decision, no quick scan |
| **Human checkpoint** | Pause after assessment for user confirmation |
| **Cross-project capable** | Can assess projects outside current directory |

---

## Input

```
/invar-onboard [path]

path: Target project path (optional, defaults to current directory)
```

---

## Workflow

### Phase 1: ASSESS (Automatic)

Deep analysis of target project. **No user interaction required.**

```
Step 1: Discovery
├── Glob scan for source files
├── Detect package.json / pyproject.toml / go.mod
├── Identify primary language and framework
└── Calculate code metrics (LOC, files)

Step 2: Architecture Analysis
├── Identify layering pattern (MVC, Clean, etc.)
├── Map module dependencies
├── Detect existing test framework
└── Identify entry points

Step 3: Pattern Detection
├── Error handling (throw / Result / error return)
├── Validation (Zod / Pydantic / manual)
├── Dependency injection
└── Logging/monitoring patterns

Step 4: Gap Analysis
├── Core/Shell separation status
├── Contract coverage estimation
├── Test coverage assessment
└── Documentation coverage

Step 5: Risk Assessment
├── Complexity hotspots
├── Dependency risks
├── Refactoring blockers
└── Regression risk areas

Step 6: Estimation
├── LOC per layer
├── Complexity factors
├── Risk buffer (×1.3-1.5)
└── Total effort estimate
```

**Output:** `docs/invar-onboard-assessment.md`

**Display after Phase 1:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ASSESSMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Metric | Value |
|--------|-------|
| Language | {language} |
| Code Size | {loc} lines / {files} files |
| Invar Compatibility | {compatibility}% |
| Estimated Effort | {days} days |
| Risk Level | {risk} |

Key Decision Points:
1. {decision_1}
2. {decision_2}

Proceed to planning phase? [Y/n]
```

---

### Phase 2: DISCUSS (With User)

Present findings and gather user input. **Requires explicit user confirmation.**

```
1. Summary Display
   - Invar compatibility score (0-100%)
   - Estimated effort (days)
   - Risk level (Low/Medium/High)

2. Key Decision Points
   - Error handling strategy (Result vs throw)
   - Core extraction priority
   - Test coverage requirements

3. Risk Discussion
   - Identified blockers
   - Mitigation options
   - Scope adjustment suggestions

4. Confirmation
   - "Proceed to planning phase? [Y/n]"
   - Option to abort or adjust scope
```

**Gate:** User must explicitly confirm to proceed to Phase 3.

If user says "no" or "stop" → End skill with assessment only.
If user says "yes" or "proceed" → Continue to Phase 3.

---

### Phase 3: PLAN (Automatic)

Generate detailed migration roadmap. **Only after user confirmation.**

```
Step 1: Load Assessment
├── Read assessment report
├── Extract metrics and gaps
└── Apply user preferences from discussion

Step 2: Dependency Analysis
├── Map file dependencies
├── Determine refactoring order
└── Identify parallelization opportunities

Step 3: Phase Decomposition
├── Group by layer (Repository → Service → Actions)
├── Estimate per-file effort
└── Define Gate criteria for each phase

Step 4: Session Planning
├── Break into agent sessions (2-3 files each)
├── Allocate context checkpoints
└── Define verification points

Step 5: Risk Mitigation
├── Define rollback points
├── Identify verification gates
└── Plan E2E test checkpoints

Step 6: Generate Roadmap
└── Write docs/invar-onboard-roadmap.md
```

**Output:** `docs/invar-onboard-roadmap.md`

**Display after Phase 3:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ROADMAP GENERATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase breakdown:
1. Foundation ({days_1} days) - Error types, Result infrastructure
2. Core Extraction ({days_2} days) - Pure function isolation
3. Shell Refactor ({days_3} days) - I/O layer conversion
4. Contracts ({days_4} days) - @pre/@post / Zod schemas
5. Validation ({days_5} days) - Guard integration

Total: {total_days} days

Next step: Execute Phase 1 using /develop
```

---

## Language Adapters

Load patterns based on detected language. Pattern files are located at `.invar/templates/onboard/patterns/` after `invar init`:

| Language | Pattern File | Library |
|----------|--------------|---------|
| Python | `.invar/templates/onboard/patterns/python.md` | `returns` |
| TypeScript | `.invar/templates/onboard/patterns/typescript.md` | `neverthrow` |

**Note:** If running from Invar project itself, patterns are at `src/invar/templates/onboard/patterns/`.

**Pattern file contains:**
1. Error handling transformation examples
2. Contract syntax (Python: @pre/@post, TypeScript: Zod)
3. Core/Shell directory structure
4. Framework integration (FastAPI, Next.js)
5. Must-keep-throw scenarios

---

## Assessment Report Structure

```markdown
# Invar Onboarding Assessment

> Project: {project_name}
> Assessed: {timestamp}
> Invar Version: {invar_version}

## 1. Summary

| Metric | Value |
|--------|-------|
| Primary Language | {language} |
| Framework | {framework} |
| Code Size | {loc} lines / {files} files |
| Test Coverage | {test_type}: {test_count} tests |
| **Invar Compatibility** | **{compatibility}%** |
| **Estimated Effort** | **{total_days} days** |
| **Risk Level** | **{risk_level}** |

## 2. Architecture Analysis

### 2.1 Layer Structure
{architecture_diagram}

### 2.2 Dependency Map
{dependency_map}

## 3. Pattern Analysis

| Dimension | Current | Invar Target | Gap |
|-----------|---------|--------------|-----|
| Error Handling | {current_error} | Result[T, E] / Result<T, E> | {gap_error} |
| Validation | {current_validation} | @pre/@post / Zod | {gap_validation} |
| Core/Shell | {current_separation} | Explicit separation | {gap_separation} |
| Testing | {current_test} | Doctest + Property | {gap_test} |

## 4. Risk Assessment

### 4.1 High Risk Areas
{high_risk_areas}

### 4.2 Blockers
{blockers}

### 4.3 Dependency Risks
{dependency_risks}

## 5. Effort Breakdown

| Phase | Scope | Estimate |
|-------|-------|----------|
| Foundation | Error types, Result infrastructure | {phase1_days} days |
| Core Extraction | Pure function isolation | {phase2_days} days |
| Shell Refactor | I/O layer Result conversion | {phase3_days} days |
| Contracts | @pre/@post / Zod schemas | {phase4_days} days |
| Validation | Guard integration, test coverage | {phase5_days} days |
| **Total** | | **{total_days} days** |

## 6. Recommendations

### 6.1 Suggested Approach
{recommendation}

### 6.2 Prerequisites
- [ ] E2E test coverage > 80% for critical paths
- [ ] Result library installed (neverthrow / returns)
- [ ] Error type hierarchy defined

---

*Generated by /invar-onboard*
```

---

## Roadmap Structure

```markdown
# Invar Onboarding Roadmap

> Project: {project_name}
> Generated: {timestamp}
> Based on: docs/invar-onboard-assessment.md

## Overview

| Metric | Value |
|--------|-------|
| Total Phases | 5 |
| Total Days | {total_days} |
| Agent Sessions | {session_count} |

## Phase 1: Foundation ({days} days)

### Objective
Establish error types and Result infrastructure.

### Tasks
| Day | Files | Scope |
|-----|-------|-------|
| 1 | errors/types.ts | Define error type hierarchy |
| 1 | lib/result.ts | Result helper utilities |

### Gate Checklist
- [ ] Error types defined
- [ ] Result helpers working
- [ ] E2E tests still pass

---

## Phase 2: Core Extraction ({days} days)

### Objective
Extract pure functions to Core layer.

### Sessions
| Session | Files | Estimated |
|---------|-------|-----------|
| 2.1 | validation/*.ts | 0.5 day |
| 2.2 | calculation/*.ts | 0.5 day |

### Gate Checklist
- [ ] Core functions have no I/O
- [ ] All Core functions have contracts
- [ ] E2E tests still pass

---

[Continue for remaining phases...]

---

## Rollback Strategy

| Phase | Rollback Point | Recovery Action |
|-------|----------------|-----------------|
| 1 | Pre-Foundation | Revert error types |
| 2 | Pre-Core | Revert Core extraction |
| 3 | Pre-Shell | Revert Shell changes |

---

*Generated by /invar-onboard*
```

---

## Detection Patterns

### Error Handling Detection

| Pattern | Regex |
|---------|-------|
| throw (JS/TS) | `throw new \w+Error` |
| raise (Python) | `raise \w+Error` |
| Result (Rust-style) | `Result<`, `Ok\(`, `Err\(` |
| neverthrow (TS) | `ok\(`, `err\(`, `ResultAsync` |
| returns (Python) | `Success\(`, `Failure\(`, `Result\[` |

### Validation Detection

| Pattern | Detection |
|---------|-----------|
| Zod | `z.object`, `z.string`, `.safeParse` |
| Pydantic | `BaseModel`, `Field`, `validator` |
| Joi | `Joi.object`, `Joi.string` |
| Manual | `if (!x) throw`, `if x is None: raise` |

### Architecture Detection

| Pattern | Detection |
|---------|-----------|
| MVC | `controllers/`, `models/`, `views/` |
| Clean | `domain/`, `application/`, `infrastructure/` |
| Layered | Repository, Service, Controller naming |

---

## Effort Estimation Formula

```
Base effort = LOC / 100 (days)

Adjustments:
× 1.2 if no existing tests
× 1.3 if complex dependencies
× 1.5 if high-risk areas identified
× 0.8 if Result library already used

Total = Base × Adjustments
```

---

## Installation

```bash
# Copy skill to project
cp -r src/invar/templates/skills/extensions/invar-onboard .claude/skills/

# Ensure pattern files are synced (via invar init/update)
invar update
```

**Note:** Pattern files at `.invar/templates/onboard/patterns/` are synced automatically by `invar init` or `invar update`.

---

*Extension Skill v1.0 — LX-09*
<!--/invar:skill--><!--invar:extensions-->
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Custom assessment criteria for your tech stack
     - Organization-specific migration guidelines
     - Additional language adapters
     ======================================================================== -->
<!--/invar:extensions-->
