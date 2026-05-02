---
id: code-style
name: 代码风格规范
summary: "命名、函数大小、注释时机：让代码自解释，减少认知负担"
tags: [coding, style, naming, readability]
load_policy: free
priority: 70
zones: [default]
conflict_with: []
---
# 代码风格规范 Skill

## 概述

代码风格的核心目标：**让代码在没有注释的情况下也能被读懂**。
适用场景：代码 review、新成员入职、重构前的标准对齐。

---

## 命名原则

### 变量和函数：描述"是什么"/"做什么"

```python
# 差
d = 86400
f(x)
data2 = process(data)
flag = True

# 好
SECONDS_PER_DAY = 86400
calculate_compound_interest(principal, rate, years)
validated_users = filter_inactive_users(raw_users)
is_email_verified = True
```

**规则**：
- 布尔值用 `is_`/`has_`/`can_` 前缀
- 集合用复数：`users`, `pending_orders`
- 避免缩写（`usr`, `btn`, `mgr`），除非是公认缩写（`url`, `id`, `api`）
- 函数名用动词：`get_`, `fetch_`, `calculate_`, `validate_`, `send_`

---

### 类名：描述"是什么"（名词）

```python
# 差
class DoUserStuff:
class UserManager:  # "Manager" 太模糊

# 好
class UserRepository:    # 数据访问
class UserService:       # 业务逻辑
class EmailAddress:      # 值对象
class OrderProcessor:    # 处理器
```

---

## 函数大小原则

**单一职责**：一个函数只做一件事，一个名字能概括全部行为。

```python
# 差：一个函数做了三件事
def process_order(order):
    # 验证
    if order.amount <= 0:
        raise ValueError("Invalid amount")
    # 计算
    tax = order.amount * 0.1
    total = order.amount + tax
    # 保存
    db.insert("orders", {"total": total, ...})
    return total

# 好：拆分成有意义的层次
def process_order(order: Order) -> ProcessedOrder:
    validated = validate_order(order)
    priced = calculate_pricing(validated)
    return save_order(priced)
```

**经验值**：函数超过 20 行时，想想能否拆分；超过 40 行时，必须拆分。

---

## 注释时机

**写注释的唯一理由**：解释"为什么"，不是"是什么"。

```python
# 不需要注释（代码已经说清楚了）
user_count = len(active_users)

# 需要注释（非显而易见的原因）
# Stripe 要求金额单位为分，不是元
amount_cents = int(amount_yuan * 100)

# 需要注释（绕过某个特定 bug）
# Python 3.9 的 dict 合并 bug，用 {**a, **b} 代替 a | b
merged = {**defaults, **overrides}
```

**不要写的注释**：
- 重复代码功能（`# 循环遍历用户`）
- 过时的历史（`# 2023年改的`，用 git blame）
- TODO 而不行动（要么做，要么建 issue）

---

## 复杂度控制

```python
# 减少嵌套：Early Return
def get_discount(user, product):
    if not user.is_member:
        return 0
    if product.category == "excluded":
        return 0
    if user.membership_years < 1:
        return 0.05
    return 0.10

# 减少条件：表驱动
DISCOUNT_BY_YEARS = {0: 0.05, 1: 0.08, 3: 0.10, 5: 0.15}
def get_tier_discount(years: int) -> float:
    for threshold in sorted(DISCOUNT_BY_YEARS, reverse=True):
        if years >= threshold:
            return DISCOUNT_BY_YEARS[threshold]
    return 0
```

---

## 格式化工具（不要手动维护）

| 语言 | 工具 |
|------|------|
| Python | `black` + `isort` + `ruff` |
| TypeScript | `prettier` + `eslint` |
| Go | `gofmt`（内置） |
| Rust | `rustfmt`（内置） |

**在 CI 里强制跑格式检查，代码评审不讨论格式。**

---

## 与其他 Skill 的关系

- 与 `chinese-code-review` 配合：review 时检查命名和函数大小
- 与 `refactoring` 配合：重构的目标状态就是符合本 skill 的标准
- 与 `karpathy-guidelines` 配合：最小化实现与代码风格共同减少认知负担
