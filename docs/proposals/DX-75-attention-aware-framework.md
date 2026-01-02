# DX-75: Attention-Aware Framework Architecture

**Status:** Draft
**Created:** 2026-01-02
**Supersedes:** DX-74-tiered-attention-defense.md (merged)
**References:** [DX-74-experiment-report.md](./DX-74-experiment-report.md)

## Executive Summary

DX-74 实验揭示了 LLM Agent 的四个核心注意力现象。本提案将这些发现系统性地应用到 Invar 整个框架，包括所有 Skill、USBV 工作流、以及底层架构。

**设计原则：** 不考虑向后兼容，从零设计最优架构。

---

## Part 1: 核心发现 (来自 DX-74)

### 1.1 四个注意力现象

| 现象 | 触发条件 | 表现 | 影响 |
|------|---------|------|------|
| **Attention Drift** | 50+ items, 5+ files, 3000+ lines | 后期内容分析质量下降 | 遗漏问题 |
| **Checklist Mentality** | 预枚举已知模式 | 只验证清单项，遗漏变种 | 盲点固化 |
| **Context Contamination** | 创建者评估自己作品 | 失去客观性 | 误判质量 |
| **Scale Threshold** | 规模变化 | 小规模 vs 大规模需不同策略 | 策略失配 |

### 1.2 实验验证数据

| 场景 | 规模 | Baseline | Strategy N | 关键发现 |
|------|------|----------|------------|---------|
| V4 | 50 issues, 5 files | 84% | 100% | **漂移验证** |
| V5 | 100 issues, 12 files | 100% | 100% | BUG标记无效化测试 |
| V6 | 100 issues, 12 files | 100% | 100% | 软提示无效化测试 |
| V7 | 25 issues, 5 files | 132% | 100% | **清单思维验证** |

**关键洞察：**
- 大规模 (V4): 枚举引导防止漂移
- 小规模 (V7): 彻底阅读发现更多边缘案例
- 策略必须根据规模动态选择

---

## Part 2: 框架级架构

### 2.1 Scope Analyzer (新组件)

```
┌─────────────────────────────────────────────────────────────┐
│  SCOPE ANALYZER                                             │
│  ───────────────────────────────────────────────────────────│
│  Input: file list or directory                              │
│  Output: ScopeProfile                                       │
│                                                             │
│  Metrics:                                                   │
│  - file_count: int                                          │
│  - total_lines: int                                         │
│  - avg_complexity: float                                    │
│  - issue_density_estimate: float                            │
│                                                             │
│  Classification:                                            │
│  - SMALL:  <5 files AND <3000 lines                         │
│  - MEDIUM: 5-10 files OR 3000-10000 lines                   │
│  - LARGE:  >10 files OR >10000 lines                        │
└─────────────────────────────────────────────────────────────┘
```

**实现位置：** `src/invar/core/scope_analyzer.py`

```python
@dataclass
class ScopeProfile:
    """Scope analysis result for strategy selection."""
    file_count: int
    total_lines: int
    complexity_score: float
    classification: Literal["SMALL", "MEDIUM", "LARGE"]

    @property
    def recommended_strategy(self) -> str:
        if self.classification == "SMALL":
            return "THOROUGH_BASELINE"
        elif self.classification == "MEDIUM":
            return "HYBRID"
        else:
            return "ENUMERATION_GUIDED"
```

### 2.2 Strategy Orchestrator (新组件)

```
┌─────────────────────────────────────────────────────────────┐
│  STRATEGY ORCHESTRATOR                                      │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Scope       │ →  │ Strategy     │ →  │ Execution     │  │
│  │ Analyzer    │    │ Selector     │    │ Engine        │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│                                                             │
│  Strategies:                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ THOROUGH_BASELINE                                   │   │
│  │ - Linear reading, no enumeration                    │   │
│  │ - Best for: <3000 lines, finding edge cases         │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ ENUMERATION_GUIDED                                  │   │
│  │ - Phase 0: invar_sig + grep enumeration             │   │
│  │ - Phase 1: Fresh agent with issue_map               │   │
│  │ - Best for: >3000 lines, preventing drift           │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ HYBRID                                              │   │
│  │ - Run ENUMERATION_GUIDED first                      │   │
│  │ - Run OPEN_ENDED pass second                        │   │
│  │ - Merge and deduplicate                             │   │
│  │ - Best for: Security audits, maximum coverage       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ CHUNKED_PARALLEL                                    │   │
│  │ - Split into <3000 line chunks                      │   │
│  │ - Parallel subagents per chunk                      │   │
│  │ - Merge results                                     │   │
│  │ - Best for: >10000 lines                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Isolation Manager (新组件)

```
┌─────────────────────────────────────────────────────────────┐
│  ISOLATION MANAGER                                          │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Principle: Creator ≠ Evaluator                             │
│                                                             │
│  spawn_isolated_agent(                                      │
│      role: "REVIEWER" | "VALIDATOR" | "CHALLENGER",         │
│      context: MinimalContext,  # No conversation history    │
│      model: "opus" | "sonnet",                              │
│  ) -> AgentReport                                           │
│                                                             │
│  Rules:                                                     │
│  1. Isolated agent receives ONLY:                           │
│     - Files to process                                      │
│     - Contracts (if available)                              │
│     - Specific instructions                                 │
│  2. Isolated agent does NOT receive:                        │
│     - Conversation history                                  │
│     - Previous agent's reasoning                            │
│     - Development context                                   │
│  3. Each round spawns NEW agent (no reuse)                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 Attention Refresh Controller

```
┌─────────────────────────────────────────────────────────────┐
│  ATTENTION REFRESH CONTROLLER                               │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Triggers (automatic):                                      │
│  - After processing 5 files                                 │
│  - After phase transition (U→S→B→V)                         │
│  - Before evaluation/validation                             │
│  - When switching creation→review mode                      │
│                                                             │
│  Refresh Actions:                                           │
│  1. Re-read .invar/context.md                               │
│  2. Re-enumerate remaining scope                            │
│  3. Reset completion tracking                               │
│  4. Optional: Spawn fresh subagent                          │
│                                                             │
│  Integration:                                               │
│  - Hook into all skill entry points                         │
│  - Automatic, transparent to user                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 3: Skill 重设计

### 3.1 /review (完全重设计)

**废弃:** 旧的 same-context review 模式
**新架构:**

```
┌─────────────────────────────────────────────────────────────┐
│  /review                                                    │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Entry:                                                     │
│  1. Scope Analyzer → determine strategy                     │
│  2. Self-review check → force isolation if self-review      │
│                                                             │
│  Execution (based on scope):                                │
│                                                             │
│  SMALL (<3000 lines):                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Isolated Agent (single pass, thorough reading)     │   │
│  │  + Open-ended discovery                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  MEDIUM (3000-10000 lines):                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Phase 0: Enumeration (invar_sig + grep)            │   │
│  │  Phase 1: Isolated Agent with issue_map             │   │
│  │  Phase 2: Open-ended discovery pass                 │   │
│  │  → Merge, deduplicate                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  LARGE (>10000 lines):                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Chunk into ~3000 line segments                     │   │
│  │  Parallel isolated agents per chunk                 │   │
│  │  Cross-chunk boundary analysis                      │   │
│  │  → Merge all findings                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Fix Loop (all strategies):                                 │
│  - Main agent fixes issues                                  │
│  - NEW isolated agent reviews (never reuse)                 │
│  - Repeat until APPROVED or max_rounds                      │
└─────────────────────────────────────────────────────────────┘
```

**Key Changes:**
1. 废弃 same-context review - 永远使用隔离
2. 规模自动检测策略
3. Hybrid 默认包含 open-ended pass
4. 每轮 fix 后 spawn 新 agent

### 3.2 /develop (新增 VALIDATE 隔离)

```
┌─────────────────────────────────────────────────────────────┐
│  /develop (USBV with Isolation)                             │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  UNDERSTAND ─── Main Agent                                  │
│      │          (reads, explores, asks)                     │
│      ▼                                                      │
│  SPECIFY ─────── Main Agent                                 │
│      │          (writes contracts, designs)                 │
│      ▼                                                      │
│  BUILD ───────── Main Agent                                 │
│      │          (implements code)                           │
│      ▼                                                      │
│  VALIDATE ────── ⚠️ ISOLATION REQUIRED                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Validation Sub-workflow:                           │   │
│  │                                                     │   │
│  │  1. Main Agent: Run invar_guard()                   │   │
│  │                                                     │   │
│  │  2. Spawn Isolated VALIDATOR:                       │   │
│  │     - Receives: implementation files, contracts     │   │
│  │     - Does NOT receive: development conversation    │   │
│  │     - Task: Verify implementation matches spec      │   │
│  │     - Returns: PASS/FAIL + issues                   │   │
│  │                                                     │   │
│  │  3. If FAIL:                                        │   │
│  │     - Main agent fixes                              │   │
│  │     - Spawn NEW isolated validator                  │   │
│  │     - Repeat until PASS                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Exit: Guard PASS + Isolated Validator PASS                 │
└─────────────────────────────────────────────────────────────┘
```

**Key Changes:**
1. VALIDATE 阶段强制隔离
2. Builder 不能评估自己的代码
3. 每轮 fix 后 spawn 新 validator

### 3.3 /investigate (分块探索)

```
┌─────────────────────────────────────────────────────────────┐
│  /investigate (Chunked Exploration)                         │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Problem: Long research → later files skimmed               │
│                                                             │
│  Solution: Chunk exploration into focused subtasks          │
│                                                             │
│  Entry:                                                     │
│  1. Scope Analyzer → estimate exploration size              │
│  2. If LARGE: auto-chunk                                    │
│                                                             │
│  SMALL exploration:                                         │
│  - Direct exploration by main agent                         │
│  - Attention refresh after every 5 files                    │
│                                                             │
│  LARGE exploration:                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Generate exploration plan (questions/areas)     │   │
│  │  2. For each area:                                  │   │
│  │     - Spawn focused Explore subagent                │   │
│  │     - Limit to specific question/area               │   │
│  │  3. Synthesize findings                             │   │
│  │  4. AUTO-COMPLETE CHECK:                            │   │
│  │     - Did findings answer original question?        │   │
│  │     - If YES → auto-complete                        │   │
│  │     - If NO → auto-expand scope (up to 2x)          │   │
│  │     - If still NO → report partial + gaps           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 /propose (Devil's Advocate)

```
┌─────────────────────────────────────────────────────────────┐
│  /propose (with Challenger)                                 │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Problem: Author proposes → only considers known options    │
│                                                             │
│  Solution: Add Devil's Advocate pass                        │
│                                                             │
│  Workflow:                                                  │
│  1. Main Agent: Generate options (as today)                 │
│                                                             │
│  2. Spawn Isolated CHALLENGER:                              │
│     - Receives: proposed options                            │
│     - Task: "What options are missing? What flaws exist?"   │
│     - Returns: critiques + alternative options              │
│                                                             │
│  3. Main Agent: Synthesize                                  │
│     - Merge challenger's additions                          │
│     - AUTO-RECOMMEND based on:                              │
│       * Trade-off analysis                                  │
│       * Project context (.invar/context.md)                 │
│       * Complexity vs benefit                               │
│     - Present: "Recommended: X, Alternatives: Y, Z"         │
│                                                             │
│  4. User decides (or accepts recommendation)                │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 /audit (与 /review 统一)

```
┌─────────────────────────────────────────────────────────────┐
│  /audit → 合并到 /review --readonly                         │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  /review --readonly:                                        │
│  - Same strategy selection as /review                       │
│  - Same isolation requirements                              │
│  - But: NO fix loop, only report                            │
│                                                             │
│  废弃独立的 /audit skill                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 4: USBV 工作流重设计

### 4.1 Phase Transitions

```
┌─────────────────────────────────────────────────────────────┐
│  USBV with Attention Awareness                              │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  UNDERSTAND                                                 │
│      │                                                      │
│      │ ← Attention Refresh Point                            │
│      │   (re-read context.md, reset tracking)               │
│      ▼                                                      │
│  SPECIFY                                                    │
│      │                                                      │
│      │ ← Attention Refresh Point                            │
│      │ ← Optional: Isolated Contract Reviewer               │
│      │   (if complex, spawn agent to review contracts)      │
│      ▼                                                      │
│  BUILD                                                      │
│      │                                                      │
│      │ ← Attention Refresh Point                            │
│      │ ← Context Contamination Warning                      │
│      │   (builder now has emotional attachment)             │
│      ▼                                                      │
│  VALIDATE ───── MANDATORY ISOLATION                         │
│      │                                                      │
│      │ ← Spawn Isolated Validator                           │
│      │   (completely fresh context)                         │
│      ▼                                                      │
│  EXIT                                                       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Incremental USBV (Large Tasks)

```
┌─────────────────────────────────────────────────────────────┐
│  Incremental USBV (for large implementations)               │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Large Task Detection:                                      │
│  - >10 functions to implement                               │
│  - >1000 lines estimated                                    │
│  - Multiple files to create/modify                          │
│                                                             │
│  Chunked Workflow:                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  UNDERSTAND (full task)                             │   │
│  │      ↓                                              │   │
│  │  SPECIFY (full design, chunked contracts)           │   │
│  │      ↓                                              │   │
│  │  For each chunk:                                    │   │
│  │      BUILD chunk                                    │   │
│  │      VALIDATE chunk (isolated)                      │   │
│  │      ↓                                              │   │
│  │  Integration VALIDATE (isolated, full scope)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Benefits:                                                  │
│  - Each chunk gets fresh validation                         │
│  - Early detection of issues                                │
│  - Prevents "sunk cost" continuation                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 4.5: Agent 自动化机制 (新增)

### 4.5.1 Skill 自动路由

```
┌─────────────────────────────────────────────────────────────┐
│  AUTO-ROUTER                                                │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Input: User message                                        │
│  Output: Skill invocation (automatic, no user command)      │
│                                                             │
│  Detection Rules:                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  IF message contains:                               │   │
│  │    "implement", "add", "fix", "create", "build"     │   │
│  │  AND requires code changes                          │   │
│  │  → AUTO-INVOKE /develop                             │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  IF message contains:                               │   │
│  │    "review", "check", "audit", "verify"             │   │
│  │  AND references existing code                       │   │
│  │  → AUTO-INVOKE /review                              │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  IF message contains:                               │   │
│  │    "why", "how does", "explain", "understand"       │   │
│  │  → AUTO-INVOKE /investigate                         │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  IF message contains:                               │   │
│  │    "should we", "compare", "which", "design"        │   │
│  │  → AUTO-INVOKE /propose                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Announcement (transparent):                                │
│  "📍 Auto-routing: /develop — detected implementation task" │
└─────────────────────────────────────────────────────────────┘
```

### 4.5.2 成本感知降级

```
┌─────────────────────────────────────────────────────────────┐
│  COST-AWARE DEGRADATION                                     │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Context Budget Estimation:                                 │
│  - Remaining context window                                 │
│  - Estimated tokens per subagent                            │
│  - Number of planned subagent calls                         │
│                                                             │
│  Auto-Degradation Rules:                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Budget Level    │ Strategy Adjustment              │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  HIGH (>50%)     │ Full strategy (HYBRID/PARALLEL)  │   │
│  │  MEDIUM (20-50%) │ ENUMERATION_GUIDED only          │   │
│  │  LOW (10-20%)    │ THOROUGH_BASELINE (no subagent)  │   │
│  │  CRITICAL (<10%) │ Quick check + warn user          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Transparency:                                              │
│  "⚡ Budget: MEDIUM — Using ENUMERATION_GUIDED strategy"    │
└─────────────────────────────────────────────────────────────┘
```

### 4.5.3 失败自动恢复

```
┌─────────────────────────────────────────────────────────────┐
│  AUTO-RECOVERY                                              │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Failure Types and Auto-Actions:                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Failure                │ Auto-Action               │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  Subagent timeout       │ Retry 1x, then degrade    │   │
│  │  Subagent empty result  │ Re-prompt with examples   │   │
│  │  Subagent error         │ Fallback to main agent    │   │
│  │  Inconsistent findings  │ Spawn tiebreaker agent    │   │
│  │  Max rounds reached     │ Report partial + continue │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Recovery Chain:                                            │
│  1. Retry same strategy (1x)                                │
│  2. Degrade to simpler strategy                             │
│  3. Fallback to main agent                                  │
│  4. Report failure + partial results                        │
│                                                             │
│  Never: Silently fail or lose progress                      │
└─────────────────────────────────────────────────────────────┘
```

### 4.5.4 并行执行决策

```
┌─────────────────────────────────────────────────────────────┐
│  PARALLEL EXECUTION CONTROLLER                              │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  Auto-Parallel Conditions:                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Condition                    │ Parallel?           │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  Multiple files, no deps      │ YES - chunk review  │   │
│  │  Sequential fix loop          │ NO - must serialize │   │
│  │  Multiple questions           │ YES - parallel inv. │   │
│  │  Cross-file analysis          │ NO - needs context  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Merge Strategy:                                            │
│  - Deduplicate findings by (file, line, issue_type)         │
│  - Preserve highest severity rating                         │
│  - Combine evidence from multiple sources                   │
└─────────────────────────────────────────────────────────────┘
```

### 4.5.5 复杂度自动阈值

```
┌─────────────────────────────────────────────────────────────┐
│  COMPLEXITY THRESHOLDS (Auto-Trigger)                       │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  When to spawn additional agents:                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Trigger                      │ Auto-Action          │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  >5 contracts in SPECIFY      │ Contract Reviewer    │   │
│  │  >10 functions to implement   │ Chunked BUILD        │   │
│  │  >3 security-sensitive files  │ Security Reviewer    │   │
│  │  >50% escape hatches          │ Escape Hatch Auditor │   │
│  │  Circular dependencies found  │ Architecture Review  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  All thresholds are automatic - no user configuration       │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 5: Prompt Engineering Patterns

### 5.1 Enumeration-First Prompt Pattern

```markdown
## Before Analyzing Any File

1. **Enumerate targets BEFORE reading:**
   ```
   grep "pattern" file → found N instances
   invar_sig file → found M functions
   ```

2. **Create explicit checklist:**
   ```
   □ pattern at line X
   □ pattern at line Y
   □ pattern at line Z
   ```

3. **Process each item explicitly:**
   ```
   ✓ line X: checked, issue found
   ✓ line Y: checked, no issue
   ✓ line Z: checked, issue found
   ```

4. **Verify count before completion:**
   ```
   Checked 3/3 instances of pattern
   ```
```

### 5.2 Fresh Eyes Prompt Pattern

```markdown
## Isolation Prompt Template

You are an independent [ROLE].

CRITICAL RULES:
1. You have NEVER seen this code before
2. You have NO knowledge of how it was developed
3. You are NOT emotionally attached to any solution
4. Your ONLY goal is to [TASK]

INPUT YOU RECEIVE:
- [Files/artifacts to evaluate]

INPUT YOU DO NOT RECEIVE:
- Development conversation
- Previous agent's reasoning
- Author's explanations

OUTPUT:
- [Structured report format]
```

### 5.3 Hybrid Pass Prompt Pattern

```markdown
## Pass 1: Guided Review

Using the issue_map from Phase 0, verify each potential issue:
[issue_map items]

Report: "Verified X/Y items from issue_map"

## Pass 2: Open-Ended Discovery

Forget the issue_map. Read the code as if you've never seen it.
Look for issues NOT in the issue_map:
- Edge cases
- Variant patterns
- Logic errors
- Security issues

Report: "Found N additional issues not in issue_map"

## Merge

Combine findings from both passes, deduplicate.
```

---

## Part 6: 实现路线图

### 6.0 实现策略选择

**核心洞察:** DX-74 的大部分收益可以通过提示词更新获得，无需新增代码模块。

| 方案 | 开发成本 | 预期收益 | ROI |
|------|---------|---------|-----|
| **Phase B (轻量级)** | ~300 行提示词 | +10-15% 检测率 | **高** |
| Phase A (完整) | ~1700 行代码 | +16-20% 检测率 | 中等 |

**推荐路径:** 先实施 Phase B，验证效果后再决定是否需要 Phase A。

---

### 6.1 Phase B: 轻量级实施 (✅ 已完成)

**仅提示词更新，无新增代码模块。**

| 更新 | 文件 | 状态 |
|------|------|------|
| /review 规模感知策略 | `skills/review/SKILL.md` | ✅ v7.0 |
| /develop VALIDATE 隔离 | `skills/develop/SKILL.md` | ✅ v5.1 |
| 规模分类规则 | Agent 自行判断 | ✅ 内嵌 |

**关键变更:**

1. **/review 添加规模分类:**
   - SMALL (<5 files, <1500 lines): THOROUGH 策略 (不预枚举)
   - MEDIUM (5-10 files, 1500-5000 lines): HYBRID 策略 (枚举 + 开放发现)
   - LARGE (>10 files, >5000 lines): CHUNKED 策略 (分块并行)

2. **/develop VALIDATE 阶段隔离:**
   - 非简单实现 (>3 functions OR >200 lines) 需 spawn 隔离 validator
   - 隔离 validator 不接收开发对话上下文

3. **策略选择由 Agent 判断:**
   - 无需 ScopeAnalyzer 代码模块
   - 提示词中嵌入分类规则

---

### 6.2 Phase B 验证计划

#### 6.2.1 验证目标

| 目标 | 验证问题 | 成功标准 |
|------|---------|---------|
| 大规模漂移防护 | MEDIUM/LARGE scope 是否选择 HYBRID/CHUNKED? | V4 检测率 >90% (原 84%) |
| 小规模清单思维避免 | SMALL scope 是否选择 THOROUGH? | V7 发现边缘变种 |
| 规模判断准确性 | Agent 是否正确分类 SMALL/MEDIUM/LARGE? | 90%+ 正确率 |
| 隔离执行 | 是否 spawn 独立 subagent? | 100% 遵守隔离规则 |

#### 6.2.2 验证步骤

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: V4 场景验证 (MEDIUM scope, 漂移防护)               │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  场景: tests/experiments/dx74_attention_drift/scenario_v4/  │
│  规模: 5 files, ~2600 lines, 50 issues                      │
│  预期策略: HYBRID                                           │
│                                                             │
│  执行:                                                      │
│  1. 在新会话中运行 /review 对 V4 场景                        │
│  2. 观察: Agent 是否选择 HYBRID 策略?                        │
│  3. 观察: Phase 0 是否执行枚举?                              │
│  4. 观察: Phase 1+2 是否 spawn 隔离 agent?                   │
│  5. 计算: 检测率 = 发现数 / 50                               │
│                                                             │
│  成功标准: 检测率 >90%, 策略选择正确                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Step 2: V7 场景验证 (SMALL scope, 清单思维避免)            │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  场景: tests/experiments/dx74_attention_drift/scenario_v7/  │
│  规模: 5 files, ~2600 lines, 25 issues                      │
│  预期策略: THOROUGH (边界情况，接近 MEDIUM)                  │
│                                                             │
│  执行:                                                      │
│  1. 在新会话中运行 /review 对 V7 场景                        │
│  2. 观察: Agent 是否选择 THOROUGH 策略?                      │
│  3. 观察: 是否跳过预枚举，直接彻底阅读?                       │
│  4. 观察: 是否发现 ground_truth 之外的变种?                  │
│  5. 计算: 检测率 = 发现数 / 25                               │
│                                                             │
│  成功标准: 检测率 >=100%, 发现至少 1 个变种                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Step 3: 隔离验证                                           │
│  ───────────────────────────────────────────────────────────│
│                                                             │
│  在 Step 1 和 Step 2 中检查:                                 │
│  - 每轮是否 spawn 新的隔离 subagent?                         │
│  - Subagent prompt 是否不包含开发对话?                       │
│  - 多轮 fix loop 是否每轮都是新 agent?                       │
│                                                             │
│  成功标准: 100% 遵守隔离规则                                 │
└─────────────────────────────────────────────────────────────┘
```

#### 6.2.3 验证记录模板

```markdown
## DX-75 Phase B 验证报告

### 测试信息
- 日期: YYYY-MM-DD
- 测试者: [name]
- Review skill 版本: v7.0

### V4 场景结果
- 策略选择: [THOROUGH/HYBRID/CHUNKED]
- 策略正确: [是/否]
- 发现问题数: [N] / 50
- 检测率: [N%]
- 隔离遵守: [是/否]

### V7 场景结果
- 策略选择: [THOROUGH/HYBRID/CHUNKED]
- 策略正确: [是/否]
- 发现问题数: [N] / 25
- 检测率: [N%]
- 变种发现: [列出]
- 隔离遵守: [是/否]

### 结论
- [ ] Phase B 达标，无需 Phase A
- [ ] Phase B 部分达标，需要调整提示词
- [ ] Phase B 不足，需要实施 Phase A
```

#### 6.2.4 失败处理

| 失败情况 | 诊断 | 修复方案 |
|---------|------|---------|
| 策略选择错误 | 分类阈值不当 | 调整 SKILL.md 中阈值 |
| 检测率 <90% | 策略执行不彻底 | 强化策略说明 |
| 未 spawn 隔离 agent | 规则未遵守 | 添加强制检查 |
| 变种未发现 | THOROUGH 不够彻底 | 增强开放发现提示 |

---

### 6.3 Phase A: 完整实施 (延后)

**仅在 Phase B 效果不足时实施。**

| Component | Location | 触发条件 |
|-----------|----------|----------|
| ScopeAnalyzer | `src/invar/core/scope_analyzer.py` | Agent 规模判断不准 |
| StrategySelector | `src/invar/core/strategy_selector.py` | 策略选择需要更复杂逻辑 |
| IsolationManager | `src/invar/shell/isolation.py` | 隔离 spawn 需要封装 |
| AttentionRefreshController | `src/invar/core/attention.py` | 自动刷新需要代码支持 |

### 6.4 Phase A Skill Updates (延后)

| Skill | Changes | 触发条件 |
|-------|---------|----------|
| /investigate | 分块探索 | 大规模探索效果不佳 |
| /propose | Devil's Advocate | 选项遗漏问题 |
| /audit | 合并到 /review --readonly | 简化 skill 数量 |

### 6.5 验证与回归

| Test | Method | Success Criteria |
|------|--------|------------------|
| V4 scenario | Run new /review | >95% detection |
| V7 scenario | Run new /review | >100% detection (find variants) |
| Self-review detection | Automated | 100% isolation for self-review |
| Scale-based selection | Various scopes | Correct strategy selected |

---

## Part 7: 废弃项

### 7.1 废弃的 Skill 模式

| 废弃项 | 原因 | 替代 |
|--------|------|------|
| Same-context self-review | Context contamination | Always isolation |
| /audit as separate skill | Redundant | /review --readonly |
| Manual strategy selection | Error-prone | Auto-detection |
| Single-pass validation | Drift risk | Multi-round with isolation |

### 7.2 废弃的提案

| 提案 | 状态 | 处理 |
|------|------|------|
| DX-74-tiered-attention-defense.md | Superseded | 内容已合并到本提案 |

---

## Part 8: 成功指标

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| V4 baseline detection | 84% | 100% | Run experiment |
| V7 edge case detection | 100% (Strategy N) | 120%+ (find variants) | Run experiment |
| Self-review without isolation | Possible | Impossible (blocked) | Code path analysis |
| Strategy selection accuracy | N/A (manual) | 95% | A/B testing |
| False positive rate | N/A | <5% on control files | Control file testing |

---

## Appendices

### Appendix A: ScopeProfile Classification Algorithm

```python
def classify_scope(files: List[Path]) -> ScopeProfile:
    """Classify scope for strategy selection."""
    total_lines = sum(count_lines(f) for f in files)
    file_count = len(files)

    # Complexity estimation
    complexity = estimate_complexity(files)

    # Classification
    if file_count < 5 and total_lines < 3000:
        classification = "SMALL"
    elif file_count < 10 and total_lines < 10000:
        classification = "MEDIUM"
    else:
        classification = "LARGE"

    return ScopeProfile(
        file_count=file_count,
        total_lines=total_lines,
        complexity_score=complexity,
        classification=classification
    )
```

### Appendix B: Isolation Manager API

```python
class IsolationManager:
    """Manages isolated agent spawning."""

    def spawn_reviewer(
        self,
        files: List[Path],
        issue_map: Optional[Dict] = None,
    ) -> ReviewReport:
        """Spawn isolated code reviewer."""

    def spawn_validator(
        self,
        implementation: List[Path],
        contracts: List[Path],
    ) -> ValidationReport:
        """Spawn isolated implementation validator."""

    def spawn_challenger(
        self,
        proposal: str,
    ) -> ChallengeReport:
        """Spawn isolated devil's advocate."""
```

### Appendix C: Strategy Decision Tree

```
                    ┌─────────────────┐
                    │ Analyze Scope   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         ┌────────┐    ┌──────────┐   ┌─────────┐
         │ SMALL  │    │  MEDIUM  │   │  LARGE  │
         │<3K LOC │    │ 3K-10K   │   │ >10K    │
         └───┬────┘    └────┬─────┘   └────┬────┘
             │              │              │
             ▼              ▼              ▼
        ┌─────────┐   ┌──────────┐   ┌──────────┐
        │THOROUGH │   │  HYBRID  │   │ CHUNKED  │
        │BASELINE │   │(enum+    │   │ PARALLEL │
        │         │   │ open)    │   │          │
        └─────────┘   └──────────┘   └──────────┘
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-01-02 | Initial draft from DX-74 findings |
| 0.2 | 2026-01-02 | Added Part 4.5: Agent automation mechanisms |
| 0.3 | 2026-01-02 | **Phase B 实施完成**: 轻量级提示词方案，重构 Part 6 路线图 |
| 0.4 | 2026-01-02 | 添加详细验证计划 (6.2): V4/V7 验证步骤、记录模板、失败处理 |

---

*Generated from DX-74 experiment results. See [DX-74-experiment-report.md](./DX-74-experiment-report.md) for full experimental data.*
