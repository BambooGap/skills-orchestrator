---
id: security-review
name: 安全代码审查
summary: "OWASP Top 10 快速核查：输入验证、认证、注入、敏感数据暴露"
tags: [review, security, owasp]
load_policy: free
priority: 95
zones: [default]
conflict_with: []
---
# 安全代码审查 Skill

## 概述

安全审查不是找所有漏洞，而是**系统性排查最常见的高风险问题**。
适用场景：新功能 PR、第三方库升级、认证相关代码改动。

---

## 必查清单（每个 PR 都过）

### 输入验证

```python
# 检查点：用户输入是否经过验证后才使用？

# 危险
user_id = request.args.get("user_id")
db.query(f"SELECT * FROM users WHERE id = {user_id}")  # SQL 注入！

# 安全
user_id = int(request.args.get("user_id"))  # 类型验证
db.query("SELECT * FROM users WHERE id = ?", user_id)  # 参数化查询
```

**检查项**：
- [ ] 所有 SQL 使用参数化查询，无字符串拼接
- [ ] 文件路径不使用用户输入（路径遍历攻击）
- [ ] 命令执行不包含用户输入（命令注入）

---

### 认证与授权

```python
# 检查点：操作前是否验证了身份 AND 权限？

# 危险：只验证登录，未验证权限
@app.route("/users/<user_id>/data")
@login_required
def get_user_data(user_id):
    return User.get(user_id).data  # 任何登录用户都能查别人的数据！

# 安全：验证权限
@app.route("/users/<user_id>/data")
@login_required
def get_user_data(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        abort(403)
    return User.get(user_id).data
```

**检查项**：
- [ ] 每个受保护接口都有认证检查
- [ ] 对象级权限（IDOR）：不能通过猜 ID 访问他人资源
- [ ] 管理接口有额外的权限检查

---

### 敏感数据处理

```python
# 检查点：敏感数据是否出现在不该出现的地方？

# 危险
logger.info(f"用户登录: {user.email} 密码: {password}")
response = {"user": user.to_dict()}  # to_dict 包含了 password_hash！

# 安全
logger.info(f"用户登录: user_id={user.id}")
response = {"user": {"id": user.id, "email": user.email, "name": user.name}}
```

**检查项**：
- [ ] 日志中不含密码、token、信用卡号、身份证号
- [ ] API 响应不含 password_hash、secret_key 等字段
- [ ] 密码使用 bcrypt/argon2 存储，不是 MD5/SHA1

---

### 依赖安全

```bash
# Python
pip audit

# Node.js
npm audit

# 检查：是否有已知 CVE 的依赖？
```

**检查项**：
- [ ] 没有已知高危漏洞的直接依赖
- [ ] 第三方库的版本已锁定（不用 `>=` 无上限）

---

## 高风险场景专项检查

### 文件上传

```python
# 必须检查：
# 1. 文件类型（不能只信 Content-Type，要检查魔数）
# 2. 文件大小限制
# 3. 存储到非 web 可访问目录
# 4. 用随机文件名（防止猜测和覆盖）
import magic
def validate_upload(file):
    if file.size > 10 * 1024 * 1024:  # 10MB 限制
        raise ValueError("文件过大")
    mime = magic.from_buffer(file.read(1024), mime=True)
    if mime not in ALLOWED_TYPES:
        raise ValueError(f"不支持的文件类型: {mime}")
```

### 第三方重定向

```python
# 危险：开放重定向
return redirect(request.args.get("next"))

# 安全：验证域名
from urllib.parse import urlparse
next_url = request.args.get("next", "/")
if urlparse(next_url).netloc not in ALLOWED_HOSTS:
    next_url = "/"
return redirect(next_url)
```

---

## 输出模板

```
## 安全审查报告

### PR / 功能
[描述]

### 检查项
- [ ] SQL 注入：✓ 全部参数化
- [ ] 认证：✓ 接口已保护
- [ ] 权限：⚠️ 待确认对象级权限
- [ ] 敏感数据：✓ 日志无敏感信息
- [ ] 依赖：✓ npm audit 无高危

### 发现问题
| 严重度 | 位置 | 问题 | 修复建议 |
|--------|------|------|---------|

### 结论
[通过 / 需要修复后重审]
```

---

## 与其他 Skill 的关系

- 与 `pr-review` 配合：安全审查是 PR review 的专项扩展
- 与 `error-handling` 配合：错误消息不能暴露内部信息
- 与 `api-design` 配合：API 设计阶段就应考虑认证授权
