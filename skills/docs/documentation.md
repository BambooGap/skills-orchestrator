---
id: documentation
name: 写文档
summary: "README 规范、代码注释时机、API 文档格式、迁移文档模板"
tags: [docs, readme, api]
load_policy: free
priority: 60
zones: [default]
conflict_with: []
---
# 写文档 Skill

## 概述

本 skill 定义什么时候必须写文档、写什么、怎么写。核心原则：**文档解释"为什么"，代码解释"是什么"**。

---

## 文档类型与触发条件

| 类型 | 何时必须写 | 放在哪里 |
|------|-----------|---------|
| README | 新项目；现有 README 信息过时 | 项目根目录 |
| API 文档 | 公共接口；被其他服务调用的接口 | 代码注释 + 单独文档 |
| 架构说明 | 非显而易见的设计决策 | docs/ 目录或代码注释 |
| 操作手册 | 需要人工执行的流程 | docs/ 或 wiki |
| 变更说明 | breaking change；迁移指南 | CHANGELOG + PR 描述 |

---

## README 规范

### 必须包含的章节

```markdown
# 项目名

一句话描述：这个工具/库是做什么的。

## 快速开始

从零到能跑起来的最短路径，不超过 5 个步骤：

\`\`\`bash
pip install xxx
xxx init
xxx build
\`\`\`

## 配置

关键配置项说明（不是所有配置，只是关键的）。

## 常见问题

3-5 个最常见的报错/问题和解决方法。
```

### README 的常见问题

| 问题 | 症状 | 修法 |
|------|------|------|
| 太长 | 读者找不到他们要的 | 分章节，加导航 |
| 过时 | 代码已改，文档没跟上 | 在 CI 里加文档检查 |
| 太技术 | 新用户看不懂 | 从"我能用它做什么"开始写 |
| 缺示例 | 只有概念，没有实际代码 | 每个功能至少一个完整示例 |

---

## 代码注释规范

### 写注释的时机

**必须写**：
```python
# 绕过了 Python 的 GIL 限制，因为这个操作是 CPU-bound 而非 IO-bound
# 参考：https://docs.python.org/3/library/multiprocessing.html
with multiprocessing.Pool() as pool:
    results = pool.map(process, items)
```

```python
# 注意：这里故意不用 async/await，因为下游 SDK 不支持协程
# 换成 async 会导致 SDK 内部状态竞争，见 issue #234
result = sdk.sync_call(params)
```

**不需要写**：
```python
# 遍历所有用户  ← 多余，代码自己说
for user in users:
    process(user)
```

### 注释质量检查

好注释回答以下其中一个问题：
- 为什么要这样做？（不是其他方式）
- 这段代码有什么不明显的副作用？
- 这里依赖了什么前提条件？
- 这是临时方案，后续怎么处理？

---

## API 文档规范

### Python docstring

```python
def calculate_discount(amount: float, user_level: str) -> float:
    """
    计算用户折扣后金额。

    Args:
        amount: 原始金额，必须 > 0
        user_level: 用户等级，可选值 "gold" / "silver" / "normal"

    Returns:
        折扣后金额。gold 用户 8 折，silver 9 折，normal 原价。

    Raises:
        ValueError: amount <= 0 或 user_level 不合法

    Example:
        >>> calculate_discount(100.0, "gold")
        80.0
    """
```

### HTTP API 文档（最小格式）

```markdown
## POST /api/orders

创建新订单。

**Request Body**
\`\`\`json
{
  "user_id": "string (required)",
  "amount": "number (required, > 0)",
  "items": "array (required, min 1)"
}
\`\`\`

**Response**
- 200: 成功，返回 `{"order_id": "xxx"}`
- 400: 参数错误，返回 `{"error": "描述"}`
- 401: 未认证

**注意**：同一用户 1 分钟内只能创建 5 个订单（rate limit）。
```

---

## 迁移文档规范

任何涉及以下内容的变更，**必须**附带迁移文档：

- 配置文件格式变更
- 数据库 schema 变更
- 删除了公共 API
- 修改了公共 API 的参数/返回值

### 迁移文档模板

```markdown
## v1.x → v2.0 迁移指南

### 变更内容

[列出 breaking change]

### 迁移步骤

**Step 1**: [具体操作，带命令]

**Step 2**: [具体操作]

### 验证

迁移完成后执行：
\`\`\`bash
[验证命令]
\`\`\`

预期输出：[具体描述]

### 回滚

如果遇到问题，回滚步骤：
[具体步骤]
```

---

## 与其他 Skill 的关系

- `finish-branch`：提 PR 前文档检查清单的一部分
- `chinese-code-review`：代码注释规范的补充
- `writing-plans`：计划中应包含文档更新任务
