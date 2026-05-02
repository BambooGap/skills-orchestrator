# Pipeline 条件分支功能

## 概述

Pipeline 条件分支允许根据门禁（gate）检查结果自动跳转到不同的步骤，实现"成功继续，失败处理"的流程控制。

## 功能说明

### 两种配置方式

#### 1. Gate 级别分支（推荐）

```yaml
steps:
  - id: debug
    skill: systematic-debugging
    next: [fix]
    gate:
      must_produce: root_cause
      on_failure: abort  # 门禁失败时跳转到 abort 步骤

  - id: fix
    skill: tdd
    next: []

  - id: abort
    skill: finish-branch
    next: []
```

#### 2. Step 级别分支

```yaml
steps:
  - id: debug
    skill: systematic-debugging
    next: [fix]
    on_gate_failure: retry  # 门禁失败时跳转到 retry 步骤
    gate:
      must_produce: root_cause

  - id: fix
    skill: tdd
    next: []

  - id: retry
    skill: systematic-debugging
    next: []
```

### 优先级

当同时配置了 `gate.on_failure` 和 `step.on_gate_failure` 时：
- `gate.on_failure` 优先级更高
- 只有在 `gate.on_failure` 未配置时，才会使用 `step.on_gate_failure`

## 使用场景

### 1. 失败终止

```yaml
steps:
  - id: debug
    skill: systematic-debugging
    next: [fix]
    gate:
      must_produce: root_cause
      on_failure: abort  # 找不到原因就终止流程

  - id: abort
    skill: finish-branch
    next: []
    gate:
      must_produce: abort_reason
```

### 2. 失败重试

```yaml
steps:
  - id: debug
    skill: systematic-debugging
    next: [fix]
    on_gate_failure: retry  # 失败后重新调试
    gate:
      must_produce: root_cause

  - id: retry
    skill: systematic-debugging
    next: [fix]  # 重试后继续修复流程
    gate:
      must_produce: root_cause
```

### 3. 条件修复

```yaml
steps:
  - id: security-check
    skill: security-review
    next: [finish]
    gate:
      must_produce: security_findings
      on_failure: fix-security  # 发现安全问题就修复

  - id: fix-security
    skill: tdd
    next: [finish]
    gate:
      must_produce: code_changes
```

## 实际示例

查看 `config/pipelines/bug-fix-with-abort.yaml` 获取完整示例。

## 技术实现

### 新增方法

- `Engine.complete_and_advance(state)`: 推荐使用的推进方法
  - 自动检查 gate
  - 根据结果决定分支
  - 更新步骤状态

### 向后兼容

- 原有的 `Engine.advance(state)` 方法保持不变
- 没有配置分支字段的 pipeline 行为与之前一致
- 所有现有测试全部通过

## 测试

查看 `tests/test_pipeline_branch.py` 了解完整的测试用例：
- gate 失败分支
- gate 成功不走分支
- step 级别分支
- 优先级测试
- 向后兼容性测试