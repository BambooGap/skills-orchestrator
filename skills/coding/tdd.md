---
id: tdd
name: 测试驱动开发
summary: "Red-Green-Refactor 循环：先写失败测试，再写最小实现，再重构"
tags: [testing, coding, tdd, quality]
load_policy: free
priority: 90
zones: [default]
conflict_with: []
---
# 测试驱动开发 Skill

## 概述

TDD 不是"先写测试"的仪式感，而是**用测试来驱动设计**的思维方式。
适用场景：新功能开发、修复有明确预期行为的 bug、重构前的安全网建设。

---

## Red-Green-Refactor 循环

### 第一步：Red（写一个失败的测试）

```python
def test_parse_email_extracts_domain():
    assert parse_email("user@example.com")["domain"] == "example.com"
```

**原则**：
- 测试要描述**行为**，不描述实现
- 一个测试只测一件事
- 测试名字就是需求文档

**检查**：运行后必须看到红色（FAIL），不红就没用

---

### 第二步：Green（写最小的实现让测试通过）

```python
def parse_email(email: str) -> dict:
    local, domain = email.split("@")
    return {"local": local, "domain": domain}
```

**原则**：
- 只写让当前测试通过的最少代码
- 不要提前实现"以后可能需要的"逻辑
- 丑一点没关系，下一步会 refactor

**检查**：测试变绿即可进入下一步

---

### 第三步：Refactor（在绿灯保护下重构）

```python
@dataclass
class EmailAddress:
    local: str
    domain: str

    @classmethod
    def parse(cls, raw: str) -> "EmailAddress":
        if "@" not in raw:
            raise ValueError(f"Invalid email: {raw}")
        local, domain = raw.split("@", 1)
        return cls(local=local, domain=domain)
```

**原则**：
- 消除重复代码
- 改善命名和结构
- 测试全程保持绿色
- 如果重构让测试变红，说明你改错了

---

## 测试分层策略

| 层级 | 占比 | 特征 |
|------|------|------|
| 单元测试 | 70% | 纯函数、单一依赖、毫秒级 |
| 集成测试 | 20% | 真实 DB/API、测试边界 |
| E2E 测试 | 10% | 用户视角、慢但高置信 |

---

## 常见反模式与修正

| 反模式 | 问题 | 修正 |
|--------|------|------|
| 先写实现再补测试 | 测试变成实现的镜像，没有设计价值 | 严格 Red first |
| 一个测试测多件事 | 失败时不知道哪里坏了 | 每个 assert 拆成独立测试 |
| Mock 太多 | 测试通过但集成时崩 | 只 Mock 外部 I/O |
| 测试私有方法 | 测试耦合实现细节 | 只测公共接口 |
| 忽略边界条件 | 生产环境才发现 | TDD 时明确写边界 case |

---

## 输出模板

```
## TDD 任务记录

### 需求
[一句话描述要实现的行为]

### 测试用例清单
- [ ] 正常情况：xxx
- [ ] 边界条件：xxx（空/零/最大值）
- [ ] 错误情况：xxx

### Cycle 记录
1. RED: [测试名] → [失败原因]
2. GREEN: [最小实现摘要]
3. REFACTOR: [重构要点]
```

---

## 与其他 Skill 的关系

- 与 `systematic-debugging` 配合：TDD 产生的测试是调试的起点
- 与 `refactoring` 配合：Refactor 阶段直接用重构 skill
- 与 `finish-branch` 配合：提 PR 前确认所有 TDD cycle 已完成
