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
│  │  4. Ask user if more exploration needed             │   │
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
│     - Present unified options to user                       │
│                                                             │
│  4. User decides                                            │
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

### 6.1 Phase 1: Core Components (Week 1-2)

| Component | Location | Priority |
|-----------|----------|----------|
| ScopeAnalyzer | `src/invar/core/scope_analyzer.py` | P0 |
| StrategySelector | `src/invar/core/strategy_selector.py` | P0 |
| IsolationManager | `src/invar/shell/isolation.py` | P0 |
| AttentionRefreshController | `src/invar/core/attention.py` | P1 |

### 6.2 Phase 2: Skill Updates (Week 2-3)

| Skill | Changes | Priority |
|-------|---------|----------|
| /review | Complete rewrite with new architecture | P0 |
| /develop | Add isolated VALIDATE phase | P0 |
| /investigate | Add chunked exploration | P1 |
| /propose | Add Devil's Advocate pass | P2 |
| /audit | Merge into /review --readonly | P1 |

### 6.3 Phase 3: Protocol Updates (Week 3-4)

| Update | Location | Priority |
|--------|----------|----------|
| USBV attention refresh | `INVAR.md` | P0 |
| Skill routing rules | `CLAUDE.md` | P0 |
| Isolation requirements | Skill SKILL.md files | P0 |

### 6.4 Phase 4: Testing & Validation (Week 4-5)

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

---

*Generated from DX-74 experiment results. See [DX-74-experiment-report.md](./DX-74-experiment-report.md) for full experimental data.*
