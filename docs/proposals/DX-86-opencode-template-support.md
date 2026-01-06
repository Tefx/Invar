# DX-86: OpenCode + oh_my_opencode Template Support

**Status:** 📝 Draft
**Priority:** Medium
**Type:** Enhancement
**Related:** LX-18 (OpenCode Compatibility)
**Created:** 2026-01-06

---

## 执行摘要

**需求：** OpenCode + oh_my_opencode 用户需要特定的CLAUDE.md内容（Invar × UltraWork兼容宪章），但普通Claude Code用户不需要。

**方案：** 条件化template系统 - 仅在检测到OpenCode/oh_my_opencode时注入特定内容。

**原则：** 不污染默认template，保持向后兼容。

---

## 1. 背景

### 1.1 OpenCode + oh_my_opencode架构

**oh_my_opencode是什么：**
- OpenCode的执行编排层扩展
- 提供并行执行、任务委派、止损机制
- 内部名称：UltraWork

**兼容需求：**
```
Invar（上层协议：USBV、Check-In/Final）
    ↓
UltraWork（执行编排：并行/委派/止损）
    ↓
OpenCode（Agent实现）
```

### 1.2 特定需求

OpenCode + oh_my_opencode用户需要的特殊约定：

1. **Baseline模式** - guard不绿时的工作规则
2. **工具顺序** - invar_map优先，guard只在根目录运行
3. **最小可见输出** - 只输出关键信息，不做状态播报
4. **分层优先级** - Invar硬性流程优先，UltraWork提供编排

**关键点：** Claude Code用户**不需要**这些规则。

---

## 2. 问题分析

### 2.1 当前template系统

```python
# src/invar/templates/protocol/universal/
├── CLAUDE.md          # 单一版本
├── INVAR.md          # 单一版本
└── completion.md     # 单一版本
```

**问题：**
- 所有agent共享相同template
- 添加OpenCode特定内容会污染Claude Code用户的CLAUDE.md
- 无法条件化注入内容

### 2.2 需要条件化的内容

**Invar × UltraWork兼容宪章：**
```markdown
## Invar × UltraWork Compatibility Protocol

A. 分层与优先级
1. Invar是上层协议；UltraWork是执行编排层
2. 冲突时以Invar硬性流程为准

B. 最小必要可见输出
3. 仅输出：Routing行、Phase Header、TodoWrite、Final行

C. 工具与探索顺序
4. 结构探索默认先invar_map
5. invar_guard只在仓库根目录运行：path="."

D. Baseline模式
6. guard FAIL时记录baseline，允许继续
7. 采用本地校验：lsp_diagnostics + type-check + lint
8. 收尾要求不扩大失败面

E. Final输出格式
9. Baseline FAIL: ✓ Final: guard BASELINE_FAIL (known debt) | local checks PASS
10. Baseline PASS: ✓ Final: guard PASS | ...
```

**大小：** ~30行，约600字符

---

## 3. 设计方案

### 3.1 Template区域系统（推荐）⭐

**核心思想：** 在CLAUDE.md中使用条件区域标记。

**Template结构：**
```markdown
<!--invar:critical-->
...
<!--/invar:critical-->

<!--invar:managed version="5.0"-->
...
<!--/invar:managed-->

<!--invar:opencode-->  ← 新增
## Invar × UltraWork Compatibility Protocol
...
<!--/invar:opencode-->

<!--invar:user-->
...
<!--/invar:user-->
```

**同步逻辑：**
```python
# src/invar/shell/commands/template_sync.py

def should_include_opencode_section(path: Path) -> bool:
    """检测是否需要OpenCode专用内容。"""
    # 检测1: opencode.json存在
    if (path / "opencode.json").exists():
        return True

    # 检测2: oh_my_opencode package.json依赖
    package_json = path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "oh-my-opencode" in deps or "@oh-my-opencode/core" in deps:
                return True
        except:
            pass

    # 检测3: .opencode目录存在
    if (path / ".opencode").exists():
        return True

    return False

def sync_templates(path: Path, config: SyncConfig) -> Result:
    """Sync templates with conditional sections."""
    include_opencode = should_include_opencode_section(path)

    for region in ["critical", "managed", "user"]:
        # ... 正常同步 ...

    # 条件同步OpenCode区域
    if include_opencode:
        sync_region(path, "opencode", template_content)
    else:
        remove_region(path, "opencode")  # 移除（如果存在）
```

**优点：**
- ✅ 不污染默认template
- ✅ 自动检测，无需手动flag
- ✅ 向后兼容（现有用户不受影响）
- ✅ 可扩展（未来可添加其他条件区域）

**缺点：**
- ⚠️ 需要修改template_sync.py逻辑
- ⚠️ 增加复杂度

---

### 3.2 替代方案：独立Template文件

**结构：**
```
src/invar/templates/protocol/
├── universal/           # 通用template
│   ├── CLAUDE.md
│   └── INVAR.md
└── opencode/           # OpenCode专用
    └── CLAUDE.md       # 包含宪章的完整版本
```

**同步逻辑：**
```python
def get_template_variant(path: Path) -> str:
    """Determine which template variant to use."""
    if should_include_opencode_section(path):
        return "opencode"
    return "universal"

def sync_templates(path: Path, config: SyncConfig):
    variant = get_template_variant(path)
    template_root = TEMPLATES / variant
    # ... 使用对应variant的template ...
```

**优点：**
- ✅ 更清晰的分离
- ✅ 易于维护（不同用户群的template独立）

**缺点：**
- ❌ Template重复（opencode版需要复制universal全部内容）
- ❌ 维护成本高（改动需要同步两个版本）
- ❌ 违反DRY原则

---

### 3.3 替代方案：invar init Flag

**用法：**
```bash
# Claude Code用户（默认）
invar init --claude

# OpenCode用户
invar init --opencode

# OpenCode + oh_my_opencode用户
invar init --opencode --ultrawork
```

**实现：**
```python
def init_cmd(
    path: Path,
    claude: bool = False,
    opencode: bool = False,
    ultrawork: bool = False,
):
    config = SyncConfig(
        include_opencode=opencode,
        include_ultrawork=ultrawork,
    )
    sync_templates(path, config)
```

**优点：**
- ✅ 用户显式控制
- ✅ 实现简单

**缺点：**
- ❌ 用户需要手动指定
- ❌ 自动检测更优（用户无感）
- ❌ 已有项目需要重新init

---

## 4. 推荐方案：条件区域系统

### 4.1 实现步骤

**Phase 1: Template更新（1天）**

1. **添加OpenCode区域到template：**
```markdown
<!--invar:opencode-->
---

## Invar × UltraWork Compatibility Protocol

**Context:** This section applies when using OpenCode with oh_my_opencode (UltraWork).

### A. Layering and Priority
1. **Invar** = Upper protocol (USBV, Check-In/Final, guard semantics)
2. **UltraWork** = Execution orchestration (parallel/delegation/circuit-breaker)
3. **Conflict resolution:** Invar hard requirements take precedence

### B. Minimal Necessary Output
- **Output ONLY:** Routing lines, USBV Phase Headers, TodoWrite, Final line
- **Do NOT:** Status broadcasts, intermediate state reports

### C. Tool and Exploration Order
4. **Structure exploration:** Default to `invar_map` first (for entry points/symbols/module map)
5. **Guard invocation:** ONLY at repository root: `path="."` (avoid subdirectory marker/language detection issues)

### D. Baseline Mode (when guard fails)
6. **Entering implementation:** Run `invar_guard(changed=true)` first
   - If FAIL and is known debt → Record as **baseline failing**, allow continuation
7. **During implementation:** Use local checks for current changes
   - `lsp_diagnostics` + `pnpm type-check` + `pnpm lint`
   - Add `tests/e2e` as needed per task
8. **Completion:** Run `invar_guard(changed=true)` again
   - **Requirement:** Do NOT expand failure surface (at minimum: files changed in this task do NOT introduce new guard errors)

### E. Final Output Format
9. **If baseline still FAIL:**
   ```
   ✓ Final: guard BASELINE_FAIL (known debt) | local checks PASS
   ```
10. **If baseline cleared to PASS:**
   ```
   ✓ Final: guard PASS | ...
   ```

---
<!--/invar:opencode-->
```

2. **更新template_sync.py：**
```python
# src/invar/shell/commands/template_sync.py

CONDITIONAL_REGIONS = {
    "opencode": should_include_opencode_section,
    # 未来可扩展：
    # "pi": should_include_pi_section,
}

def sync_conditional_regions(path: Path, template_content: str) -> str:
    """Apply conditional region logic."""
    result = template_content

    for region, detector_func in CONDITIONAL_REGIONS.items():
        should_include = detector_func(path)

        pattern = rf"<!--invar:{region}-->(.*?)<!--/invar:{region}-->"
        if should_include:
            # Keep the region (remove markers only)
            result = re.sub(
                pattern,
                r"\1",
                result,
                flags=re.DOTALL
            )
        else:
            # Remove entire region
            result = re.sub(
                pattern,
                "",
                result,
                flags=re.DOTALL
            )

    return result
```

**Phase 2: 检测逻辑（2天）**

```python
def should_include_opencode_section(path: Path) -> bool:
    """Detect if OpenCode-specific content is needed.

    Detection signals (OR logic):
    1. opencode.json exists
    2. oh-my-opencode in package.json dependencies
    3. .opencode/ directory exists
    """
    # Signal 1: OpenCode config
    if (path / "opencode.json").exists():
        return True

    # Signal 2: oh-my-opencode package
    package_json = path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            all_deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {})
            }

            opencode_packages = {
                "oh-my-opencode",
                "@oh-my-opencode/core",
                "ultrawork",
            }

            if any(pkg in all_deps for pkg in opencode_packages):
                return True
        except (json.JSONDecodeError, OSError):
            pass

    # Signal 3: OpenCode directory
    if (path / ".opencode").exists():
        return True

    return False
```

**Phase 3: 测试（1天）**

```python
# tests/test_opencode_template.py

def test_opencode_detection():
    """Test OpenCode environment detection."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)

        # Case 1: No OpenCode
        assert not should_include_opencode_section(path)

        # Case 2: opencode.json exists
        (path / "opencode.json").write_text("{}")
        assert should_include_opencode_section(path)

def test_template_sync_with_opencode():
    """Test template sync includes OpenCode section."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)
        (path / "opencode.json").write_text("{}")

        sync_templates(path, SyncConfig())

        claude_md = (path / "CLAUDE.md").read_text()
        assert "Invar × UltraWork Compatibility Protocol" in claude_md
        assert "Baseline Mode" in claude_md

def test_template_sync_without_opencode():
    """Test template sync excludes OpenCode section."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)

        sync_templates(path, SyncConfig())

        claude_md = (path / "CLAUDE.md").read_text()
        assert "UltraWork" not in claude_md
        assert "Baseline Mode" not in claude_md
```

---

## 5. 兼容宪章完整内容

**注入到CLAUDE.md的完整文本：**

```markdown
<!--invar:opencode-->
---

## Invar × UltraWork Compatibility Protocol

**Context:** This section applies when using OpenCode with oh_my_opencode (UltraWork orchestration layer).

**Version:** v2.0 (Baseline)
**Last Updated:** 2026-01-06

### Philosophy

- **Invar** provides the upper protocol (USBV workflow, Check-In/Final ceremony, guard semantics)
- **UltraWork** provides execution orchestration (parallel task execution, delegation, circuit-breaker mechanisms)
- On conflict: Invar's hard requirements take precedence; UltraWork provides efficiency optimizations

---

### A. Layering and Priority

1. **Invar** = Upper protocol layer
   - USBV workflow (Understand → Specify → Build → Validate)
   - Check-In/Final ceremony
   - Guard semantics and contract verification

2. **UltraWork** = Execution orchestration layer
   - Parallel task execution
   - Task delegation
   - Circuit-breaker/stop-loss mechanisms

3. **Conflict resolution:** Invar's hard workflow requirements take precedence
   - Example: VALIDATE phase MUST run guard before Final
   - UltraWork can optimize execution order but cannot skip Invar checkpoints

---

### B. Minimal Necessary Output

4. **Output ONLY the following:**
   - **Routing announcements:** `📍 Routing: /skill — reason`
   - **USBV Phase Headers:** `━━━ SPECIFY (2/4) ━━━`
   - **TodoWrite updates:** Task list changes
   - **Final line:** `✓ Final: guard PASS | ...`

5. **Do NOT output:**
   - Verbose status broadcasts
   - Intermediate state reports
   - "I'm now doing X..." announcements
   - Internal orchestration details

**Rationale:** Reduce noise, maintain focus on deliverables

---

### C. Tool and Exploration Order (Updated after invar_map fix)

6. **Structure exploration priority:**
   ```
   1st: invar_map (symbol/entry point/module map)
   2nd: explore/grep (for detailed search when needed)
   ```

   **Rationale:** After DX-85 fixes, invar_map correctly supports TypeScript and provides language-agnostic output

7. **Guard invocation rule:**
   ```bash
   # ✅ ALWAYS run guard at repository root
   invar_guard(path=".")

   # ❌ NEVER run guard in subdirectories
   invar_guard(path="./src/components")  # May cause language detection issues
   ```

   **Rationale:** Avoid subdirectory marker file issues and language detection edge cases

---

### D. Baseline Mode (when guard does not pass)

**Problem:** Repository may have pre-existing guard failures (technical debt)

**Solution:** Baseline mode allows forward progress while preventing regression

8. **Entering implementation task:**
   ```python
   # Step 1: Establish baseline
   result = invar_guard(changed=True)

   if result.status == "failed":
       # Record known failures
       baseline = {
           "files": result.files_with_errors,
           "error_count": result.error_count,
       }
       # ✅ Allow continuation (known debt)
   ```

9. **During implementation:**
   Use **local checks** for files changed in current task:
   ```bash
   # Required checks
   - lsp_diagnostics  # IDE/LSP error checking
   - pnpm type-check  # TypeScript type checking (if TS project)
   - pnpm lint        # ESLint/Ruff linting

   # Optional (task-dependent)
   - pnpm test        # Unit tests
   - tests/e2e        # E2E tests (if UI changes)
   ```

   **Requirement:** Files changed in THIS task MUST pass local checks

10. **Completion (before Final):**
    ```python
    # Step 2: Verify no regression
    result = invar_guard(changed=True)

    # ✅ Acceptable outcomes:
    # - PASS (ideal: debt cleared!)
    # - FAIL with SAME baseline (no new errors introduced)

    # ❌ Unacceptable:
    # - FAIL with NEW errors in changed files
    # - Expanded failure surface
    ```

---

### E. Final Output Format

11. **If baseline still FAIL:**
    ```
    ✓ Final: guard BASELINE_FAIL (known debt) | local checks PASS | 0 new errors
    ```

    **Interpretation:**
    - Pre-existing guard failures remain (known debt)
    - All local checks passed
    - No new guard errors introduced in this task

12. **If baseline cleared to PASS:**
    ```
    ✓ Final: guard PASS | 0 errors, 2 warnings
    ```

    **Interpretation:**
    - All guard checks passed (debt cleared!)
    - Standard Final format applies

---

### F. Workflow Integration

**Check-In + Baseline:**
```
✓ Check-In: Invar | main | dirty
   Baseline: guard FAIL (12 pre-existing errors in 3 files)
```

**USBV Phases (unchanged):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Specification work...]
```

**Final + Baseline:**
```
✓ Final: guard BASELINE_FAIL (known debt) | local checks PASS | 0 new errors
```

---

### G. Example Session

```markdown
# Check-In
✓ Check-In: Invar | feature/auth | clean
   Baseline: guard FAIL (8 errors in src/legacy/)

# Routing
📍 Routing: /develop — Implement OAuth login

# USBV Phases
━━━ UNDERSTAND (1/4) ━━━
[invar_map to understand structure]

━━━ SPECIFY (2/4) ━━━
[Design contracts and types]

━━━ BUILD (3/4) ━━━
[Implementation with local checks]

━━━ VALIDATE (4/4) ━━━
- Local checks: ✅ PASS
- Guard (changed): ✅ No new errors (baseline maintained)

# Final
✓ Final: guard BASELINE_FAIL (known debt) | local checks PASS | 0 new errors
```

---

### H. When to Use Baseline Mode

| Situation | Use Baseline? | Rationale |
|-----------|---------------|-----------|
| New greenfield project | ❌ No | Expect guard PASS |
| Legacy codebase with debt | ✅ Yes | Allow incremental improvement |
| Current task touches legacy | ✅ Yes | Prevent spreading debt |
| Team actively fixing debt | ⚠️ Optional | Balance progress vs cleanup |

---

### I. Migrating Out of Baseline Mode

**Goal:** Gradually clear technical debt

**Strategy:**
1. **Freeze debt:** No new guard errors (enforced by Baseline)
2. **Incremental cleanup:** Fix 1-2 errors per task when touching related files
3. **Track progress:** Monitor baseline error count trend
4. **Celebrate milestones:** When baseline clears to PASS

**Example:**
```
Week 1: Baseline 20 errors
Week 2: Baseline 18 errors (fixed 2 while implementing feature A)
Week 3: Baseline 15 errors (fixed 3 while refactoring module B)
...
Week N: ✅ guard PASS (debt cleared!)
```

---

<!--/invar:opencode-->
```

---

## 6. 向后兼容性

### 6.1 现有用户

**Claude Code用户：**
- ✅ 无影响（不会看到UltraWork宪章）
- ✅ CLAUDE.md保持原样
- ✅ 运行`invar init`或`invar update`时自动排除OpenCode区域

**已有OpenCode用户（如果有）：**
- ✅ 运行`invar init`或`invar update`时自动注入宪章
- ✅ 基于检测逻辑，无需手动操作

### 6.2 测试计划

**测试场景：**
1. Claude Code环境（无opencode.json）→ 无宪章
2. OpenCode环境（有opencode.json）→ 有宪章
3. oh_my_opencode环境（package.json依赖）→ 有宪章
4. 混合环境（Claude + OpenCode配置共存）→ 有宪章

---

## 7. 实施计划

### Phase 1: Template准备（1天）
- [ ] 在`src/invar/templates/protocol/universal/CLAUDE.md`添加`<!--invar:opencode-->`区域
- [ ] 编写完整兼容宪章内容
- [ ] Validate markdown语法

### Phase 2: 检测逻辑（2天）
- [ ] 实现`should_include_opencode_section()`
- [ ] 更新`sync_templates()`支持条件区域
- [ ] 添加`sync_conditional_regions()`函数

### Phase 3: 测试（1天）
- [ ] 单元测试：检测逻辑
- [ ] 集成测试：template同步
- [ ] E2E测试：`invar init`在不同环境

### Phase 4: 文档（1天）
- [ ] 更新`docs/opencode-setup.md`说明自动检测
- [ ] 添加troubleshooting指南
- [ ] 更新CHANGELOG

### Phase 5: 发布（v1.18.0）
- [ ] Bump version
- [ ] Git tag
- [ ] PyPI发布

**总时间：** 5天

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 检测逻辑误判 | 中 | 中 | 提供手动override flag |
| Template区域冲突 | 低 | 高 | 严格测试区域边界 |
| 现有用户意外变化 | 低 | 高 | 默认不检测OpenCode（保守） |
| 维护成本增加 | 中 | 低 | 清晰文档 + 单元测试 |

**缓解：手动override flag**
```bash
# 强制包含OpenCode宪章
invar init --force-opencode

# 强制排除OpenCode宪章
invar init --no-opencode
```

---

## 9. 替代考虑

### 9.1 不做条件化（放弃）

**方案：** 所有用户都看到UltraWork宪章

**缺点：**
- ❌ 污染Claude Code用户体验
- ❌ 引入不相关概念（Baseline、UltraWork）
- ❌ CLAUDE.md变得更长、更复杂

**决策：** 拒绝

### 9.2 完全独立项目（过度）

**方案：** 创建`invar-opencode`独立包

**缺点：**
- ❌ 维护成本高（重复代码）
- ❌ 用户困惑（选哪个包？）
- ❌ 碎片化生态

**决策：** 过度设计

---

## 10. 未来扩展

### 10.1 其他Agent支持

相同机制可支持其他agent的特定需求：

```markdown
<!--invar:pi-->
## Pi Coding Agent Specific Rules
...
<!--/invar:pi-->

<!--invar:cursor-->
## Cursor IDE Integration
...
<!--/invar:cursor-->
```

### 10.2 更细粒度控制

```python
# .invar/config.toml
[template]
include_sections = ["opencode", "pi"]
exclude_sections = ["legacy"]
```

---

## 11. 成功标准

**Phase 1完成标准：**
- ✅ Claude Code用户CLAUDE.md无UltraWork内容
- ✅ OpenCode用户CLAUDE.md包含完整宪章
- ✅ 自动检测成功率 > 95%
- ✅ 无破坏性变更

**长期成功标准：**
- ✅ OpenCode用户反馈Baseline模式有效
- ✅ 无Claude Code用户抱怨template变复杂
- ✅ 其他agent（Pi, Cursor）可复用此机制

---

## 12. 决策

### 推荐方案
✅ **条件区域系统** (`<!--invar:opencode-->`)

**理由：**
1. 不污染默认template
2. 自动检测，用户无感
3. 可扩展（支持未来其他agent）
4. 向后兼容
5. 维护成本可控

### 实施时机
**建议：** v1.18.0（下一个minor版本）

**依赖：**
- DX-85修复已完成 ✅
- LX-18 OpenCode兼容性已评估 ✅

---

## 13. 参考

**相关提案：**
- LX-18: OpenCode Compatibility Evaluation
- DX-85: TypeScript Support UX Fix
- DX-56: Template Sync Engine (managed regions)

**外部资源：**
- OpenCode文档: https://opencode.ai/docs/
- oh_my_opencode (UltraWork): [内部编排层]

---

**提案版本：** v1.0
**作者：** Based on OpenCode agent feedback
**状态：** 📝 Draft - 待用户批准
**下一步：** 用户确认方案后开始Phase 1实施
