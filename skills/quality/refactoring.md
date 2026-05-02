---
id: refactoring
name: 安全重构
summary: "安全重构步骤：小步快走、先写测试、提取函数、消除重复代码"
tags: [refactor, quality]
load_policy: free
priority: 100
zones: [default]
conflict_with: []
---
# 安全重构 Skill

## 概述

本 skill 定义安全重构的步骤和原则。重构的核心规则：**行为不变，只改结构**。没有测试的重构不是重构，是赌博。

---

## 重构前的必要条件

在动任何代码前，确认：

- [ ] 要重构的代码有测试覆盖（如果没有，先写测试）
- [ ] 测试全部通过（`pytest` / `npm test` 结果全绿）
- [ ] 在独立分支上进行（不在 main 上直接重构）
- [ ] 有回滚方案（最坏情况：`git checkout .` 还原）

---

## 重构策略选择

### 策略 A：小步快走（推荐）

每次只做一种类型的改动，改完立即跑测试：

```
改名 → 测试 → commit
提取函数 → 测试 → commit  
移动文件 → 测试 → commit
```

**适用**：大部分重构场景。  
**优势**：出问题时能精确定位到哪步引入了 bug。

### 策略 B：完整重写

对整个模块重新实现，最后做行为对比。

**适用**：原代码质量极差、无法小步改动时。  
**必须**：
1. 保留原代码不删
2. 新旧代码并行运行，对比输出
3. 确认行为一致后再删旧代码

---

## 常见重构手法

### 提取函数

**触发条件**：函数超过 40 行；代码块有独立含义；注释解释了一段代码在做什么。

```python
# 重构前
def process_order(order):
    # 校验
    if order.amount <= 0:
        raise ValueError("金额必须大于0")
    if order.user_id is None:
        raise ValueError("用户不能为空")
    
    # 计算折扣
    if order.user.level == "gold":
        discount = 0.2
    elif order.user.level == "silver":
        discount = 0.1
    else:
        discount = 0
    final_amount = order.amount * (1 - discount)
    
    # 保存
    db.save(order)

# 重构后
def process_order(order):
    _validate_order(order)
    final_amount = _calculate_final_amount(order)
    db.save(order)

def _validate_order(order):
    if order.amount <= 0:
        raise ValueError("金额必须大于0")
    if order.user_id is None:
        raise ValueError("用户不能为空")

def _calculate_final_amount(order) -> float:
    discount_map = {"gold": 0.2, "silver": 0.1}
    discount = discount_map.get(order.user.level, 0)
    return order.amount * (1 - discount)
```

### 消除重复

**触发条件**：三处以上相似代码（Rule of Three）。

步骤：
1. 先不要急着抽象，把三处全部写出来
2. 找到真正相同的部分（参数是什么、变化的是什么）
3. 提取函数，用参数表达变化的部分
4. 确认所有调用点行为不变

### 改善变量命名

**触发条件**：看到不明含义的变量名（`temp`、`data`、`flag`、`x`）。

```python
# 重构前
temp = user.get_orders()
for x in temp:
    if x.status == 1:
        flag = True

# 重构后
pending_orders = user.get_orders()
has_pending_order = False
for order in pending_orders:
    if order.status == OrderStatus.PENDING:
        has_pending_order = True
```

### 分解条件

**触发条件**：复杂的 if/elif 链；嵌套超过 3 层。

用**卫语句**（guard clause）替代嵌套：

```python
# 重构前（嵌套地狱）
def process(user, order):
    if user:
        if order:
            if order.amount > 0:
                if user.is_active:
                    return _do_process(user, order)
    return None

# 重构后（卫语句）
def process(user, order):
    if not user:
        return None
    if not order:
        return None
    if order.amount <= 0:
        return None
    if not user.is_active:
        return None
    return _do_process(user, order)
```

---

## 重构检查清单

每次重构完成后：

- [ ] 运行全部测试，全部通过
- [ ] 比较 `git diff`，确认只有结构改动，没有逻辑改动
- [ ] 没有新增功能（新功能在重构完成后单独加）
- [ ] commit message 标注 `refactor:`

---

## 不应该同时做的事

重构时**不要**：
- 同时修 bug（会污染重构的 diff）
- 同时加新功能
- 同时改接口（这是 breaking change，不是重构）

如果发现了 bug，记下来，等重构 commit 后再单独修。

---

## 与其他 Skill 的关系

- 用 `writing-plans` 先规划重构步骤，再执行
- 重构前用 `systematic-debugging` 确认现有行为
- 重构完成后用 `chinese-code-review` 审查
- 用 `finish-branch` 的清单提 PR
