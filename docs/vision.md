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
- Follow USBV workflow (Understand → Specify → Build → Validate)
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

---

## Foundational Influences

Invar's Core/Shell architecture builds on two foundational software design patterns:

### Hexagonal Architecture (Ports and Adapters)
> Alistair Cockburn, 2005 — https://alistair.cockburn.us/hexagonal-architecture

The application's business logic (Core) is isolated from external concerns (Shell) through ports and adapters. This enables testing without I/O and makes the system adaptable to different external systems.

### Functional Core, Imperative Shell
> Gary Bernhardt, 2012 — https://github.com/kbilsted/Functional-core-imperative-shell

Pure, functional code (Core) handles all logic and decisions. Imperative code (Shell) handles I/O and side effects. The Shell is a thin wrapper that calls Core functions and performs I/O.

### Invar's Contribution

Invar extends these patterns for **Agent-Native development**:

| Classic Pattern | Invar Extension |
|-----------------|-----------------|
| Separate Core/Shell | + Design-by-Contract (@pre/@post) |
| Pure functions | + Contract completeness (uniquely determines impl) |
| Testable logic | + Reflective verification (understand before fix) |
| Ports/Adapters | + Hierarchical decomposition (leaves first) |

---

## Research Foundation

Invar's methodology is validated by recent AI code generation research (6 papers).

### The Six Laws

| Law | Principle | Research Source |
|-----|-----------|-----------------|
| **1. Separation** | Pure logic (Core) and I/O (Shell) physically separate | Determinism enables testing |
| **2. Contract Complete** | Define COMPLETE, RECOVERABLE boundaries | Clover (2024): 87% accept, 0% false positive |
| **3. Context Economy** | map → signatures → implementation | Token efficiency |
| **4. Decompose First** | Break into sub-functions before implementing | Parsel (2023): +75% pass rate |
| **5. Verify Reflectively** | Reflect (why?) → Fix → Verify | Reflexion (2023): +11% success |
| **6. Integrate Fully** | Verify all feature paths connect correctly | DX-07 post-mortem: local ≠ global |

### Core Formula

```
Human Success = Agent Effectiveness × Invar Support × Problem Solvability

Where:
  Problem Solvability = Contract Completeness × Decomposition Quality
```

### AlphaCodium (2024)
Test-first approach improved GPT-4 accuracy from 19% to 44%.
> "Generating tests is easier than generating code."

This validates Invar's Contract-First principle.

### Pel (2025)
Contracts/docstrings serve as recovery context for auto-fixing errors.
> "When an error occurs, the Agent analyzes the discrepancy between
> code and expected usage (based on docstring) to propose corrections."

This extends Invar's philosophy: contracts are both verification AND recovery tools.

### Parsel (2022/2023)
Hierarchical decomposition improved pass rates by 75%+ on competition problems.
> "Like human programmers, start with high-level design, then implement
> each part gradually."

This validates Invar's Design step: decompose before implement.

### SWE-bench (2023/2024)
Real-world GitHub issues reveal that underspecified problems are unsolvable.
Best model (Claude 2) solved only 1.96% of 2,294 real issues.
> "Underspecified issue descriptions led to ambiguity on what the problem
> was and how it should be solved."

This validates Invar's core insight: **Contracts eliminate ambiguity.**
- @pre/@post make expectations explicit
- Doctests provide concrete examples
- Clear specs → Solvable problems

### Reflexion (2023)
Verbal reflection on failures improved HumanEval pass@1 from 80% to 91%.
> "Reflexion agents verbally reflect on task feedback signals, then maintain
> their reflective text in episodic memory to induce better decision-making."

This enhances Invar's Verify step: **Don't just fix—understand why it failed first.**

### Clover (2023/2024)
Three-way consistency checking achieves 87% acceptance while maintaining zero false positives.
> "To prevent annotations that are too trivial from being accepted, they test whether
> the annotations contain enough information to reconstruct functionally equivalent code."

This introduces **contract completeness**: A complete contract uniquely determines the implementation.

### Unified Insight

The research converges on a single principle:

**Understand before specify. Structure before code. Reflection before fix.**

1. **UNDERSTAND** - Inspect context, grasp intent, identify constraints
2. **SPECIFY** - Write COMPLETE contracts and decompose into sub-functions
3. **BUILD** - Write code to pass the tests (leaves first)
4. **VALIDATE** - If failure, reflect → return to appropriate phase → fix

Time spent on understanding and structure pays dividends at every stage:
- During specification → Better contracts from context awareness
- During implementation → Clearer targets (complete contracts = one valid solution)
- During verification → Catch bugs early (three-way consistency)
- During recovery → Explicit iteration to SPECIFY or UNDERSTAND
- For solvability → Clear, complete specs make problems tractable
