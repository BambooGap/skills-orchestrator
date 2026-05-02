---
id: error-handling
name: 错误处理规范
summary: "分层错误处理：业务错误 vs 技术错误，不吞异常，不过度防御"
tags: [coding, error, reliability]
load_policy: free
priority: 85
zones: [default]
conflict_with: []
---
# 错误处理规范 Skill

## 概述

好的错误处理让系统在出错时**可调试、可恢复、用户友好**。
坏的错误处理要么吞掉错误让问题隐形，要么暴露内部细节让系统不安全。

---

## 错误分类

### 业务错误（Expected Errors）

系统预期会发生的，需要传达给调用方：

```python
class UserNotFoundError(ValueError):
    def __init__(self, user_id: str):
        super().__init__(f"User {user_id} not found")
        self.user_id = user_id

class InsufficientBalanceError(Exception):
    def __init__(self, required: float, available: float):
        super().__init__(f"Need {required}, have {available}")
        self.required = required
        self.available = available
```

**原则**：自定义异常类型，携带结构化数据，让调用方可以按类型处理。

---

### 技术错误（Unexpected Errors）

系统 bug 或外部故障，通常应该让程序崩溃或快速失败：

```python
# 不要捕获你不知道如何处理的异常
# 错误示例：
try:
    result = compute(data)
except Exception:
    return None   # ← 吞掉了异常，调试噩梦

# 正确做法：让异常传播，在边界统一处理
result = compute(data)  # 如果崩，让它崩
```

---

## 分层处理原则

```
HTTP/CLI 边界    ← 捕获所有异常，转换为用户友好消息 + 日志
Service 层       ← 捕获业务异常，转换为领域错误
Infrastructure  ← 只捕获可重试的临时错误（网络超时）
核心业务逻辑     ← 通常不捕获，只抛出
```

**实现示例**：

```python
# Infrastructure：可重试的临时错误
def fetch_with_retry(url: str, max_retries: int = 3) -> Response:
    for attempt in range(max_retries):
        try:
            return requests.get(url, timeout=10)
        except requests.Timeout:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

# Service 层：转换异常
def get_user_profile(user_id: str) -> UserProfile:
    try:
        row = db.query("SELECT * FROM users WHERE id = ?", user_id)
    except DatabaseConnectionError as e:
        raise ServiceUnavailableError("用户服务暂时不可用") from e
    if row is None:
        raise UserNotFoundError(user_id)
    return UserProfile.from_row(row)

# API 边界：统一处理
@app.exception_handler(UserNotFoundError)
def handle_not_found(req, exc: UserNotFoundError):
    return JSONResponse({"error": "not_found", "id": exc.user_id}, status_code=404)
```

---

## 不要做的事

| 反模式 | 后果 | 替代方案 |
|--------|------|---------|
| `except Exception: pass` | 问题静默消失 | 至少 `logger.exception()` |
| 捕获后 `return None` | 调用方无法区分"没有"还是"出错" | 抛出具体异常 |
| 把堆栈暴露给用户 | 安全漏洞，暴露内部结构 | 日志记录，用户看友好消息 |
| 在循环里无限重试 | 雪崩效应 | 指数退避 + 最大次数 |
| `raise Exception("something went wrong")` | 调用方无法按类型处理 | 自定义异常类 |

---

## 日志规范

```python
import logging
logger = logging.getLogger(__name__)

# 技术错误：exception 级别（含堆栈）
try:
    result = dangerous_operation()
except UnexpectedError:
    logger.exception("dangerous_operation failed for user %s", user_id)
    raise

# 业务警告：warning 级别
if retry_count > 2:
    logger.warning("高重试次数 for %s: %d", resource_id, retry_count)

# 正常流程：debug 级别
logger.debug("处理完成 %s in %.2fs", item_id, elapsed)
```

---

## 输出模板

```
## 错误处理设计

### 错误类型清单
| 错误 | 类型 | 处理层 | 用户消息 |
|------|------|--------|---------|
| 用户不存在 | 业务 | Service | "未找到用户" |
| DB 连接失败 | 技术 | Infrastructure | "服务暂时不可用" |

### 重试策略
- 触发条件：[哪些错误可重试]
- 退避策略：[指数退避参数]
- 最大次数：[N 次]
```

---

## 与其他 Skill 的关系

- 与 `systematic-debugging` 配合：好的错误处理产生可调试的日志
- 与 `tdd` 配合：测试用例必须覆盖错误路径
- 与 `api-design` 配合：API 错误响应格式统一
