---
id: api-design
name: API 设计规范
summary: "REST API 设计：资源命名、状态码、版本控制、错误格式统一"
tags: [coding, api, design, rest]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
---
# API 设计规范 Skill

## 概述

好的 API 设计让接口**一致、可预测、难以误用**。
适用场景：新 REST API、现有 API 重构、API 文档评审。

---

## 资源命名规则

```
# 集合用复数名词
GET    /users           # 列表
POST   /users           # 创建
GET    /users/{id}      # 详情
PATCH  /users/{id}      # 部分更新
PUT    /users/{id}      # 完整替换
DELETE /users/{id}      # 删除

# 嵌套资源表达从属关系
GET  /users/{id}/orders          # 用户的订单列表
GET  /users/{id}/orders/{oid}    # 特定订单详情

# 动作用动词（非资源操作）
POST /users/{id}/activate
POST /emails/send
POST /orders/{id}/cancel
```

**禁止**：
- `/getUser`, `/createUser`（动词混入）
- `/user` 当集合（单数）
- 多层嵌套超过 3 级

---

## HTTP 方法语义

| 方法 | 幂等 | 安全 | 用途 |
|------|------|------|------|
| GET | ✓ | ✓ | 读取，不改变状态 |
| POST | ✗ | ✗ | 创建、触发动作 |
| PUT | ✓ | ✗ | 完整替换 |
| PATCH | ✗ | ✗ | 部分更新 |
| DELETE | ✓ | ✗ | 删除 |

---

## 状态码规范

```
2xx 成功
  200 OK          - GET/PUT/PATCH 成功
  201 Created     - POST 创建成功（附 Location 头）
  204 No Content  - DELETE 成功 / 无返回体的 PATCH

4xx 客户端错误（可修复）
  400 Bad Request       - 请求格式/参数错误
  401 Unauthorized      - 未认证（需要登录）
  403 Forbidden         - 已认证但无权限
  404 Not Found         - 资源不存在
  409 Conflict          - 冲突（重复创建/版本冲突）
  422 Unprocessable     - 格式正确但业务规则不通过
  429 Too Many Requests - 限流

5xx 服务器错误（用户无法修复）
  500 Internal Error    - 未预期的服务器错误
  503 Service Unavailable - 下游依赖不可用
```

---

## 统一错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "请求参数无效",
    "details": [
      {
        "field": "email",
        "code": "INVALID_FORMAT",
        "message": "邮件地址格式不正确"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

**原则**：
- `code` 是机器可读的常量，用于客户端逻辑分支
- `message` 是人类可读的描述（可本地化）
- `request_id` 便于追踪日志

---

## 版本控制

```
# 推荐：URL 路径版本
/v1/users
/v2/users

# 可选：请求头版本
Accept: application/vnd.myapi.v2+json
```

**版本升级策略**：
- 向后兼容的改动（增加字段）→ 不需要新版本
- 破坏性改动（删除/重命名字段）→ 必须新版本
- 旧版本至少维护 6 个月

---

## 分页规范

```
# Cursor 分页（大数据集推荐）
GET /posts?cursor=eyJpZCI6MTIzfQ&limit=20
→ {"data": [...], "next_cursor": "xxx", "has_more": true}

# Offset 分页（小数据集可用）
GET /users?page=2&per_page=20
→ {"data": [...], "total": 100, "page": 2, "per_page": 20}
```

---

## 输出模板

```
## API 设计审查

### 端点清单
| 方法 | 路径 | 功能 | 状态码 |
|------|------|------|--------|
| GET | /v1/users | 用户列表 | 200 |

### 错误码清单
| code | 状态码 | 触发场景 |
|------|--------|---------|

### 破坏性变更说明
[无 / 描述变更]
```

---

## 与其他 Skill 的关系

- 与 `error-handling` 配合：API 错误响应格式来自错误处理规范
- 与 `pr-review` 配合：API 变更的 PR 需要检查版本兼容性
- 与 `documentation` 配合：API 设计完成后输出 OpenAPI 文档
