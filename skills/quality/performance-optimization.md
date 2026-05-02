---
id: performance-optimization
name: 性能优化方法论
summary: "先测量再优化：profiling 定位瓶颈，避免过早优化，量化改进效果"
tags: [quality, performance, profiling, optimization]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
---
# 性能优化方法论 Skill

## 概述

**永远不要在没有测量之前优化。** 直觉找到的瓶颈通常不是真正的瓶颈。
适用场景：响应时间变慢、内存占用过高、数据库查询超时。

---

## 优化流程

```
测量 → 定位瓶颈 → 提出假设 → 实施改动 → 再次测量 → 比较效果
         ↑___________________________|（如果效果不足，继续循环）
```

**每一步都必须有数据，不允许"感觉应该会快"。**

---

## 第一步：建立基线

```python
# Python：用 timeit 建立基线
import timeit
baseline = timeit.timeit(lambda: your_function(test_data), number=1000)
print(f"基线：{baseline/1000*1000:.2f}ms per call")

# 或用 pytest-benchmark
def test_performance(benchmark):
    result = benchmark(your_function, test_data)
    assert result is not None
```

**记录**：P50/P95/P99 响应时间，不只是平均值。

---

## 第二步：Profiling 定位瓶颈

### CPU 瓶颈

```bash
# Python cProfile
python -m cProfile -o output.prof your_script.py
python -m pstats output.prof
# 或可视化
pip install snakeviz && snakeviz output.prof
```

### 内存瓶颈

```python
# memory_profiler
from memory_profiler import profile

@profile
def your_function():
    ...
```

### 数据库查询

```sql
-- PostgreSQL: 找慢查询
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 分析具体查询
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;
```

---

## 常见瓶颈与解法

### N+1 查询问题

```python
# 差：1 次查询所有用户 + N 次查询每个用户的订单
users = User.objects.all()
for user in users:
    orders = user.orders.all()   # N 次额外查询！

# 好：2 次查询（JOIN 或预加载）
users = User.objects.prefetch_related("orders").all()
```

### 不必要的重复计算

```python
# 差：每次调用都重新计算
def get_user_stats(user_id):
    return expensive_aggregation(user_id)

# 好：缓存结果
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_stats(user_id):
    return expensive_aggregation(user_id)
```

### 序列化/反序列化热路径

```python
# 差：每个请求都 JSON 解析一个大的配置文件
def handle_request(req):
    config = json.loads(Path("config.json").read_text())

# 好：启动时加载，内存持有
CONFIG = json.loads(Path("config.json").read_text())
def handle_request(req):
    return CONFIG[req.key]
```

---

## 何时停止优化

```
✓ 已达到目标（SLA/用户体验标准）
✓ 进一步优化的 ROI 不值得（边际收益递减）
✓ 优化代码的可读性损失超过性能收益

✗ 不能因为"代码看起来可以更快"就继续优化
✗ 不能优化非热路径（< 1% 时间的代码）
```

---

## 输出模板

```
## 性能优化报告

### 问题描述
[现象：哪个操作慢，慢到多少]

### 基线测量
- P50: xxxms
- P95: xxxms
- P99: xxxms

### Profiling 结果
- 热点函数：xxx（占 xx% CPU）
- 根因：xxx

### 优化方案
[描述改动]

### 优化后测量
- P50: xxxms（↓ xx%）
- P95: xxxms（↓ xx%）

### 代码改动
[diff 或链接]
```

---

## 与其他 Skill 的关系

- 与 `systematic-debugging` 配合：性能问题的根因分析用调试方法论
- 与 `tdd` 配合：用 benchmark 测试固化性能基线，防止回退
- 与 `deployment-checklist` 配合：部署后监控响应时间变化
