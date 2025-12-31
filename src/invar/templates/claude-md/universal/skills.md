## Commands (User-Invokable)

| Command | Purpose |
|---------|---------|
| `/audit` | Read-only code review (reports issues, no fixes) |
| `/guard` | Run Invar verification (reports results) |

## Skills (Agent-Invoked)

| Skill | Triggers | Purpose |
|-------|----------|---------|
| `/investigate` | "why", "explain", vague tasks | Research mode, no code changes |
| `/propose` | "should we", "compare" | Decision facilitation |
| `/develop` | "add", "fix", "implement" | USBV implementation workflow |
| `/review` | After /develop, `review_suggested` | Adversarial review with fix loop |

**Note:** Skills are invoked by agent based on context. Use `/audit` for user-initiated review.

Guard triggers `review_suggested` for: security-sensitive files, escape hatches >= 3, contract coverage < 50%.

---

## Workflow Routing (MANDATORY)

When user message contains these triggers, you MUST use the **Skill tool** to invoke the skill:

| Trigger Words | Skill Tool Call | Notes |
|---------------|-----------------|-------|
| "review", "review and fix" | `Skill(skill="review")` | Adversarial review with fix loop |
| "implement", "add", "fix", "update" | `Skill(skill="develop")` | Unless in review context |
| "why", "explain", "investigate" | `Skill(skill="investigate")` | Research mode, no code changes |
| "compare", "should we", "design" | `Skill(skill="propose")` | Decision facilitation |

**CRITICAL: You must call the Skill tool, not just follow the workflow mentally.**

The Skill tool reads `.claude/skills/<skill>/SKILL.md` which contains:
- Detailed phase instructions (USBV breakdown)
- Error handling rules
- Timeout policies
- Incremental development patterns (DX-63)

**Violation check (before writing ANY code):**
- "Did I call `Skill(skill="...")`?"
- "Am I following the SKILL.md instructions?"

---

## Routing Control (DX-42)

Agent announces routing decision before entering any workflow:

```
📍 Routing: /[skill] — [trigger or reason]
   Task: [summary]
```

**User can redirect with natural language:**
- "wait" / "stop" — pause and ask for direction
- "just do it" — proceed with /develop
- "let's discuss" — switch to /propose
- "explain first" — switch to /investigate

**Simple task optimization:** For simple tasks (single file, clear target, <50 lines), agent may offer:

```
📊 Simple task. Auto-orchestrate? [Y/N]
```

- Y → Full cycle without intermediate confirmations
- N → Normal step-by-step workflow

**Auto-review (DX-41):** When Guard outputs `review_suggested`, agent automatically
enters /review. Say "skip" to bypass.
