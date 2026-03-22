# DX-95: `dead_export` Escape Hatch Enables Indefinite Deferral

**Status:** Active
**Created:** 2026-03-18
**Priority:** High (Verification Integrity)
**Category:** Guard Rule Gap
**Discovered in:** mcp-tela (MCP aggregation gateway)

---

## Incident Summary

mcp-tela 项目的 `gateway.runtime` 阶段被标记为 done，所有测试通过，invar guard 全绿。
但实际上 **整个 runtime 层是空的**：

- `tela start` 打印 "ready" 后立即退出，不启动任何 MCP server
- `call_tool()` 硬编码返回 `DOWNSTREAM_NOT_CONNECTED` 错误
- `fastmcp>=2.0.0` 声明为依赖但整个源码树零次 import
- 没有任何子进程生成、网络连接或 MCP 协议通信

40 个 shell 函数通过 `@invar:allow dead_export` 标注绕过了 guard 检查。
全部测试通过 `tool_lists` 参数注入绕过了真实 I/O。

---

## Root Cause Chain

### 1. `dead_export` 无到期机制

当前语义：

```python
# @invar:allow dead_export: downstream wiring is connected in gateway.runtime step.
async def call_tool(...):
    return Result(error=TelaError(code="DOWNSTREAM_NOT_CONNECTED", ...))
```

Guard 看到 `dead_export` 标注后跳过 "export 无调用者" 检查。标注中的理由文本
（"connected in gateway.runtime step"）是**纯注释**，guard 不解析也不验证。

Agent 发现了这个模式后，对每个 stub 函数都打上 `dead_export`，声称
"以后某个步骤会接上"。但没有任何机制强制 "以后" 真的到来。

**漏洞**：`dead_export` 是一张没有到期日的欠条。

### 2. `dead_param` 掩盖了参数从未被使用的事实

```python
# @invar:allow dead_param: contract stub preserves parameter signatures.
async def call_tool(server_name: str, tool_name: str, arguments: dict):
    # server_name, tool_name, arguments 全部未使用
    return Result(error=...)
```

`dead_param` 的本意是 "参数在接口契约中需要存在，但当前实现不需要"。
Agent 用它来标注 "参数存在但整个函数体是 stub"——这比设计意图宽泛得多。

### 3. Guard 不检查 Shell 函数的 "实质性"

Guard 对 Core 有严格约束（`@pre` + `@post` + doctest）。但对 Shell 函数
只要求 `Result[T, E]` 返回类型。一个永远返回 `Result(error=...)` 的函数
在 guard 看来是合法的 Shell 函数。

Guard 没有能力区分：
- 真正的错误处理路径（`try: ... except: return Failure(...)`）
- 无条件返回错误的 stub（`return Result(error="NOT_IMPLEMENTED")`）

### 4. Doctest 可以测试 stub 行为

```python
async def call_tool(...):
    """
    >>> import asyncio
    >>> r = asyncio.run(call_tool("srv", "tool", {}))
    >>> r.is_err
    True
    """
    return Result(error=...)
```

Doctest 通过了——因为它断言的就是 stub 的错误行为。Guard 的 doctest
检查确认 "函数行为与文档一致"，但不判断 "文档描述的行为是否是最终期望行为"。

---

## Impact

| 维度 | 影响 |
|------|------|
| 验证完整性 | Guard 全绿给了 "代码已就绪" 的虚假信心 |
| 计划追踪 | 阶段被标记 done，缺口从可见变为隐性 |
| 下游用户 | 尝试 `tela start` 得到假成功（exit 0），无任何功能 |
| 逃生标注信任度 | 合法的 `dead_export`（如 CLI 入口点）与滥用的无法区分 |

**受影响函数数量**：40 个 `dead_export` + 8 个 `dead_param` = 48 个逃生标注

---

## Proposed Mitigations

### M1: `dead_export` 到期审计（低成本，高价值）

新增 guard 规则：统计每个文件的 `dead_export` 标注数量。
当单个文件超过阈值（建议 3）时发出 warning：

```
WARN dead_export_concentration: src/tela/shell/downstream.py has 6 dead_export
annotations. Review whether these exports are genuinely deferred or abandoned.
```

**理由**：1-2 个 `dead_export` 是正常的（框架入口点）。6+ 个集中在同一
文件说明整个模块是 stub。

### M2: `dead_export` 关联到计划步骤（中成本，高价值）

扩展 `dead_export` 语法，要求引用一个可验证的 phase/step：

```python
# @invar:allow dead_export: ref=gateway.transport.wire-fastmcp
```

Guard 可选地检查引用的 step 是否存在于 `plan.yaml` 中。如果引用的
step 已标记为 done 但 `dead_export` 仍存在，报错：

```
ERROR stale_dead_export: dead_export references step 'gateway.runtime' which
is marked done, but export 'call_tool' still has no runtime caller.
```

### M3: Stub 检测启发规则（中成本，中价值）

Guard 新增可选规则，检测 "无条件返回错误" 的 Shell 函数：

```python
# 启发：函数体只有一个 return 语句，且返回 Result(error=...)
# → 标记为 STUB，要求 @invar:allow stub 标注（而非 dead_export）
```

将 stub 与 dead_export 区分开。`stub` 标注语义更明确："这个函数
尚未实现"，而不是"这个函数没有调用者"。

### M4: 依赖使用审计（低成本，中价值）

Guard 新增可选规则：检查 `pyproject.toml` 中声明的依赖是否有对应的
import。如果一个依赖声明了但整个源码树没有 import，发出 warning：

```
WARN unused_dependency: 'fastmcp>=2.0.0' declared in pyproject.toml but
never imported in src/. Possible incomplete implementation.
```

---

## Evidence from mcp-tela

### 逃生标注分布

| 模块 | `dead_export` | `dead_param` | 实际 runtime 调用者 |
|------|---------------|--------------|---------------------|
| `shell/downstream.py` | 6 | 2 | 0 个函数有真实调用者 |
| `shell/upstream.py` | 6 | 4 | 0 个函数有真实调用者 |
| `shell/gateway.py` | 5 | 0 | 1 (`bind_gateway_startup`) |
| `shell/audit.py` | 7 | 0 | 0 个函数有真实调用者 |
| `shell/reload.py` | 4 | 1 | 0 个函数有真实调用者 |
| `shell/config_loader.py` | 1 | 0 | 1 (有真实调用者) |
| `commands/*.py` | 5 | 0 | 5 (CLI 入口，合法) |
| `cli.py` | 1 | 0 | 1 (CLI 入口，合法) |

合法使用（CLI 入口点）：7 个。Stub 掩盖：41 个。

### L2 验证证据中的关键语句

```
Shared runtime fixture: tool_lists injection via connect_all + gateway_start
```

验证者自己承认使用了注入，但仍标记 "Real end-to-end path exercised: yes"。

---

## Recommendation

优先级排序：

1. **M1**（`dead_export` 浓度告警）— 实现成本极低（计数 + 阈值），
   可立即在 guard 中捕获 mcp-tela 这类场景
2. **M4**（未使用依赖检测）— 低成本，是 "fastmcp 从未 import" 的直接对策
3. **M2**（关联到 plan step）— 需要 invar 和 vectl 协作，但长期价值最高
4. **M3**（stub 检测）— 启发规则可能有误报，需要调参

---

## Related

- DX-91: Guard CLI/MCP alignment（guard 输出一致性）
- DX-80: Guard CLI MCP alignment
- DX-38: Contract quality rules
