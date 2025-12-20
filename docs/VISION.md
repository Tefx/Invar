# Invar Vision: Revised Principles

## Core Purpose

> **Invar enables humans to effectively direct AI agents in producing high-quality code.**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    Human                                                    │
│      │                                                      │
│      │ directs (goals, review, decisions)                   │
│      ▼                                                      │
│    Agent ─────────────────────────────────────────────┐     │
│      │                                                │     │
│      │ follows              uses                      │     │
│      ▼                      ▼                         │     │
│    Protocol              Tools                        │     │
│    (INVAR.md)            (invar guard, etc.)          │     │
│      │                      │                         │     │
│      └──────────────────────┘                         │     │
│                  │                                    │     │
│                  ▼                                    │     │
│            High-Quality Code ◄────────────────────────┘     │
│                  │                                          │
│                  │ delivers                                 │
│                  ▼                                          │
│               Human                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## The Three Roles

### 1. Human: The Commander

**Role:** Directs the Agent, reviews output, makes final decisions.

**What humans do:**
- Define what needs to be built
- Review Agent's work
- Approve or reject changes
- Make architectural decisions when asked

**What humans DON'T need to do:**
- Memorize Invar Protocol details
- Run `invar guard` manually (Agent does this)
- Understand every rule (Agent handles compliance)

**Human's relationship with Invar:** Indirect. Humans benefit from Invar through better Agent output.

### 2. Agent: The Executor

**Role:** Follows Protocol, uses Tools, produces code that meets human's goals.

**What agents do:**
- Read and internalize INVAR.md
- Follow ICIDIV workflow
- Write contracts, separate Core/Shell
- Run `invar guard` to verify compliance
- Fix violations before presenting to human

**Agent's relationship with Invar:** Direct and primary. Agent is Invar's first-class user.

### 3. Invar: The Executor's Toolkit

**Role:** Provides structure and verification for Agent's work.

**Components:**
- **Protocol (INVAR.md):** Rules and patterns for Agent to follow
- **Tools (invar CLI):** Verification and assistance for Agent

**Invar's design principle:** Agent-Native.
- Optimized for Agent consumption (not human reading)
- Automatic over opt-in (Agent won't use unknown features)
- Machine-parseable output (--agent mode)
- Embedded hints (Agent sees them automatically)

---

## Revised Principle: Agent-Native Design

### Old Framing (Imprecise)

> "Human-AI Collaboration: Design for both humans and agents."

This implied Invar serves both equally. It doesn't.

### New Framing (Precise)

> **"Agent-Native Execution, Human-Directed Purpose"**
>
> - **Purpose:** Help humans achieve goals through Agents
> - **Execution:** Protocol and Tools are Agent-Native (Agent is primary user)
> - **Success metric:** Human can effectively direct Agent to produce quality code

### What This Means in Practice

| Design Decision | Agent-Native Approach |
|-----------------|----------------------|
| Protocol length | Short (save Agent tokens) |
| Error messages | Include fix code (Agent needs exact instructions) |
| Output format | JSON available (Agent parses easily) |
| Feature discovery | Auto-embed in output (Agent won't read docs) |
| Defaults | Strict ON (more checking helps Agent) |
| Hints | Always shown (Agent sees them automatically) |

### What This Does NOT Mean

- ❌ Humans can't use Invar directly (they can, it's just not the primary use case)
- ❌ Human experience doesn't matter (human reviews Agent output)
- ❌ Documentation is only for Agents (humans may want to understand the system)

---

## Success Criteria

### For Humans

| Criterion | Measure |
|-----------|---------|
| Effective direction | Human can describe task, Agent delivers |
| Trust in output | Human confident in Agent's code quality |
| Reduced review burden | Fewer bugs to catch in review |
| Clear escalation | Agent asks human when genuinely uncertain |

### For Agents

| Criterion | Measure |
|-----------|---------|
| Clear guidance | Protocol provides unambiguous rules |
| Actionable feedback | Guard output includes exact fixes |
| Efficient verification | Fast feedback loop (--changed mode) |
| Fail-safe defaults | Can't accidentally skip important checks |

### For the System

| Criterion | Measure |
|-----------|---------|
| Code quality | Fewer bugs, better structure |
| Maintainability | Clear Core/Shell separation |
| Verifiability | Contracts document assumptions |
| Consistency | Same patterns across codebase |

---

## The Invar Equation (Revised)

```
Human Success = Agent Effectiveness × Invar Support

Where:
  Agent Effectiveness = Protocol Clarity × Tool Utility
  Invar Support = Agent-Native Design × Verification Coverage
```

**Translation:**
- Humans succeed when Agents are effective
- Agents are effective when Invar provides clear protocols and useful tools
- Invar provides this through Agent-Native design and comprehensive verification

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Ultimate Goal** | Humans effectively direct Agents |
| **Primary User** | Agent (for Protocol and Tools) |
| **Design Philosophy** | Agent-Native |
| **Human's Role** | Commander, not operator |
| **Success Metric** | Human achieves goals through Agent |

> *"Invar is Agent infrastructure that serves Human goals."*
