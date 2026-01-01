<!--invar:skill-->
# /security — Security Audit

> Extension Skill | Tier: T0 | Isolation: Default

## Purpose

Identify security vulnerabilities using OWASP Top 10 as baseline. This skill performs systematic security audits with evidence-based reporting.

## Triggers

Use this skill when user says: "security", "audit", "vulnerabilities", "OWASP"

## Relationship to Core Skills

- `/review` includes security as one checklist item
- `/security` is deep-dive security-focused audit

---

## Core Principles

| Principle | Description |
|-----------|-------------|
| **Assume vulnerable** | Every input is malicious until proven safe |
| **Defense in depth** | Check all layers, not just obvious entry points |
| **Evidence-based** | Report with file:line and exploitation scenario |
| **Context isolated** | Fresh perspective prevents "I know this is safe" bias |

---

## Depth Levels

| Level | Scope | Use Case |
|-------|-------|----------|
| `--quick` | A03 (Injection) only | Fast CI gate |
| `--standard` | A01-A05 (most common) | Regular development |
| `--deep` (default) | Full OWASP A01-A10 + isolated agent | Release audit |

**Default is `--deep`** — thorough security review is critical.

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
│ • Code scope (files/directories to audit)                │
│ • Dependency manifest (package.json, requirements.txt)   │
│ • Config files (if any)                                  │
│                                                          │
│ Spawn Task agent with:                                   │
│ • Security Auditor persona (see below)                   │
│ • NO conversation history                                │
│ • Only the collected inputs                              │
│                                                          │
│ → Isolated agent executes steps 1-4 below                │
│ → Returns structured security report                     │
└─────────────────────────────────────────────────────────┘

If --quick or --standard:
└─ Continue in same context with attacker mindset
```

### Step 1: Entry + External Tools

- Detect Invar (Enhanced/Standalone mode)
- Identify scope (full project or specific files)
- Run external security tools (if available)

**External Tool Detection:**
```
package.json exists?     → npm audit --json
requirements.txt exists? → pip-audit --format=json
go.mod exists?           → govulncheck -json ./...
.git exists?             → trufflehog git file://. --json (secrets)
```

| Tool | OWASP Category | Command |
|------|----------------|---------|
| `npm audit` | A06 | `npm audit --json` |
| `pip-audit` | A06 | `pip-audit --format=json` |
| `govulncheck` | A06 | `govulncheck -json ./...` |
| `trufflehog` | A02 | `trufflehog git file://. --json` |
| `semgrep` | A01-A10 | `semgrep --config=auto --json` |

If tool not available → note in report, continue with manual analysis.

### Step 2: Reconnaissance — Understand Attack Surface

Identify:
- **Entry points:** APIs, forms, file uploads
- **Data flows:** user input → storage → output
- **Auth points:** authentication/authorization checkpoints
- **Dependencies:** external libraries and services

**Enhanced Mode:** Use `invar_map` to find entry points
**Standalone:** Grep for route definitions, handlers

### Step 3: OWASP Check — Systematic Vulnerability Scan

Check against OWASP Top 10 (2021):

#### A01: Broken Access Control
- [ ] Authorization checked on all endpoints?
- [ ] IDOR vulnerabilities?
- [ ] Missing function-level access control?

#### A02: Cryptographic Failures
- [ ] Sensitive data encrypted at rest?
- [ ] Weak algorithms (MD5, SHA1)?
- [ ] Hardcoded secrets?

#### A03: Injection
- [ ] SQL injection (raw queries)?
- [ ] Command injection (shell exec)?
- [ ] XSS (unescaped output)?

#### A04: Insecure Design
- [ ] Missing rate limiting?
- [ ] No account lockout?
- [ ] Predictable tokens?

#### A05: Security Misconfiguration
- [ ] Debug mode in production?
- [ ] Default credentials?
- [ ] Verbose error messages?

#### A06: Vulnerable Components
- [ ] Known CVEs in dependencies?
- [ ] Outdated packages?

#### A07: Authentication Failures
- [ ] Weak password policy?
- [ ] Missing MFA?
- [ ] Session fixation?

#### A08: Data Integrity Failures
- [ ] Unsigned data trusted?
- [ ] Deserialization of untrusted data?

#### A09: Logging Failures
- [ ] Security events logged?
- [ ] Sensitive data in logs?

#### A10: SSRF
- [ ] User-controlled URLs fetched?
- [ ] Internal network accessible?

**Use language-specific patterns from `patterns/` directory.**

### Step 4: Evidence — Document Findings

For each finding, document:
- **Location:** file:line
- **Severity:** Critical/High/Medium/Low
- **Evidence:** Code snippet
- **Exploitation scenario:** How to exploit
- **Remediation:** How to fix

### Step 5: Report — Security Audit Report

```markdown
## Security Audit Report

**Scope:** src/api/, src/auth/
**Date:** [date]
**Mode:** Enhanced / Standalone
**Depth:** --deep

### External Tool Results
- npm audit: 2 vulnerabilities (1 high, 1 moderate)
- trufflehog: 0 secrets found

### Summary
| Severity | Count |
|----------|-------|
| Critical | 1     |
| High     | 2     |
| Medium   | 3     |
| Low      | 1     |

### Critical Findings

**[CRITICAL] SQL Injection in user search**
- Location: api/users.py:45
- Evidence: `query = f"SELECT * FROM users WHERE name='{n}'"`
- Exploit: Input `' OR 1=1 --` returns all users
- Risk: Full database compromise
- Fix: Use parameterized queries

### New Findings (not baselined)
| ID | Severity | Category | Location | Description |
|----|----------|----------|----------|-------------|
| SEC-001 | Critical | A03 | api/users.py:45 | SQL injection |

### Baselined (suppressed)
| ID | Status | Reason |
|----|--------|--------|
| SEC-000 | false_positive | ORM handles escaping |

### Recommendations
1. [URGENT] Fix SQL injection
2. Add rate limiting to login endpoint
3. Implement account lockout

### Statistics
- New findings: 7
- Baselined: 2
- Total tracked: 9
```

---

## Severity Classification

**Decision Tree:**
```
Can attacker execute arbitrary code?
    │
YES ─┴─ NO
│      │
▼      ▼
CRITICAL   Can read/write sensitive data?
               │
          YES ─┴─ NO
           │      │
           ▼      ▼
         HIGH     Can access limited data / disrupt service?
                      │
                 YES ─┴─ NO
                  │      │
                  ▼      ▼
               MEDIUM   LOW
```

| Severity | Impact | Examples |
|----------|--------|----------|
| **Critical** | Complete system compromise | RCE, SQL injection (write), command injection |
| **High** | Significant data breach | SQL injection (read), stored XSS, session hijacking |
| **Medium** | Limited exposure | Reflected XSS, user enumeration, missing rate limiting |
| **Low** | Minimal direct impact | Missing security headers, debug info |

---

## False Positive Handling

Baseline file: `.invar/security-baseline.yaml`

```yaml
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
```

| Status | Meaning | Behavior |
|--------|---------|----------|
| `false_positive` | Not a real vulnerability | Suppress permanently (unless code changes) |
| `accepted_risk` | Real but accepted | Suppress, can set expiry date |
| `wont_fix` | Won't be fixed | Suppress, still counted in stats |
| `in_progress` | Being fixed | Show but don't block |

**To mark a finding:**
```
"Mark SEC-001 as false-positive: ORM handles escaping"
```

---

## Language-Specific Patterns

Patterns are loaded from `patterns/` directory based on project type.

**Pattern file structure:**
```yaml
# patterns/python.yaml
extends: _common
patterns:
  sql_injection:
    category: A03
    severity: Critical
    description: "SQL injection via string formatting"
    regex:
      - 'f"[^"]*SELECT[^"]*\{[^}]+\}'
      - '\.format\([^)]*\)[^"]*SELECT'
```

**Loading logic:**
1. Detect language(s) from manifest files
2. Load `_common.yaml` always
3. Load language-specific YAML(s)
4. Merge patterns (language-specific overrides common)

---

## Security Auditor Persona

Used in `--deep` mode (isolated agent):

```
You are an independent Security Auditor.

CRITICAL RULES:
1. Assume all code is vulnerable until proven secure
2. Think like an attacker — how would I exploit this?
3. Check all layers, not just obvious entry points
4. Provide exploitation scenarios, not just "vulnerable to X"
5. Prioritize by impact, not likelihood

OWASP TOP 10 CHECKLIST:
You MUST check every item in A01-A10.

INPUT YOU WILL RECEIVE:
- Code files to audit
- Dependency manifests
- Configuration files

INPUT YOU WILL NOT RECEIVE:
- Developer assurances ("this is only internal")
- Prior security review results
- Context about "trusted" inputs

OUTPUT: Structured Security Report (see Step 5)
```

---

## CLI Override

Override isolation level per-invocation:

```
/security              → Uses --deep (default, spawns isolated agent)
/security --quick      → Same context, A03 only
/security --standard   → Same context, A01-A05
/security --deep       → Spawns isolated agent (explicit)
```

**No external configuration required.** Defaults are in this SKILL.md.

---

## Installation

```bash
# Via CLI
invar skill add security

# Manual copy
cp -r /path/to/extensions/security .claude/skills/
```

---

*Extension Skill v1.0 — LX-07*
<!--/invar:skill--><!--invar:extensions-->
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Custom security patterns for your tech stack
     - Project-specific baseline rules
     - Additional OWASP categories relevant to your domain
     ======================================================================== -->
<!--/invar:extensions-->
