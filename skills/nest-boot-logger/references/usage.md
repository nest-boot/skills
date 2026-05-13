# 使用方法与最佳实践

## Logger API

`Logger` 类实现了 NestJS 的 `LoggerService` 接口，底层基于 pino。以下是完整的方法列表：

| 方法 | 描述 | 典型场景 |
|---|---|---|
| `setContext(name)` | 设置日志归属的上下文名称，通常设为类名 | 构造函数中调用一次 |
| `assign(bindings)` | 绑定结构化键值对，后续同一请求链路的日志自动携带 | 方法入口处绑定关键业务参数 |
| `log(message, ...params)` | 输出 INFO 级别日志 | 操作成功、流程完成 |
| `warn(message, ...params)` | 输出 WARN 级别日志 | 业务校验失败、非致命异常 |
| `error(message, ...params)` | 输出 ERROR 级别日志 | 不可恢复错误、需告警 |
| `debug(message, ...params)` | 输出 DEBUG 级别日志 | 开发阶段调试细节 |
| `verbose(message, ...params)` | 输出 TRACE 级别日志 | 极细粒度追踪 |

## 注入方式

通过构造函数依赖注入获取：

```typescript
import { Logger } from '@nest-boot/logger';
import { Injectable } from '@nestjs/common';

@Injectable()
export class MyService {
  constructor(private readonly logger: Logger) {
    this.logger.setContext(MyService.name);
  }
}
```

> **注意：** 导入的是 `@nest-boot/logger` 的 `Logger`，而不是 `@nestjs/common` 的 `Logger`。二者同名但完全不同。

## 标准用法模式

### 1. 构造函数中设置上下文

在构造函数里调用 `setContext` 一次，后续所有日志都会自动标注归属类名：

```typescript
constructor(private readonly logger: Logger) {
  this.logger.setContext(MyService.name);
}
```

### 2. 方法入口处绑定关键参数

使用 `assign` 在方法开始处绑定跟业务相关的追踪参数。这些参数会自动附着到这条请求链路里所有后续的日志条目：

```typescript
async createGroup(workspace: Workspace, input: CreateGroupInput) {
  this.logger.assign({ workspaceId: workspace.id, name: input.name });

  // 后续的 log/warn/error 都会自动携带 workspaceId 和 name
  this.logger.log('开始创建成员组');
  // 输出: {"level":"info","context":"MyService","workspaceId":"123","name":"test","msg":"开始创建成员组"}
}
```

### 3. 按级别输出日志

```typescript
// 信息级 — 操作成功
this.logger.log('成员组创建成功', { groupId: group.id });

// 警告级 — 业务逻辑校验失败（非致命）
this.logger.warn('成员组名称已存在', { name: input.name });

// 错误级 — 不可恢复的系统错误
this.logger.error('数据库连接失败', { error: err.message });
```

## 完整示例

以下摘自本项目中的 `WorkspaceMemberGroupService`，展示了一个典型的生产级日志集成：

```typescript
import { EntityManager } from '@mikro-orm/postgresql';
import { Logger } from '@nest-boot/logger';
import { EntityService } from '@nest-boot/mikro-orm';
import { BadRequestException, Injectable } from '@nestjs/common';

@Injectable()
export class WorkspaceMemberGroupService extends EntityService<WorkspaceMemberGroup> {
  constructor(
    protected readonly em: EntityManager,
    private readonly logger: Logger,
  ) {
    super(WorkspaceMemberGroup, em);
    this.logger.setContext(WorkspaceMemberGroupService.name);
  }

  async createWorkspaceMemberGroup(workspace: Workspace, input: CreateInput) {
    // 1. 入口处绑定追踪参数
    this.logger.assign({ workspaceId: workspace.id, name: input.name });

    // 2. 校验逻辑中使用 warn
    const existing = await this.findOne({ name: input.name, workspace });
    if (existing) {
      this.logger.warn('成员组名称已存在', { name: input.name });
      throw new BadRequestException('成员组名称已存在');
    }

    const group = this.em.create(WorkspaceMemberGroup, { ... });
    await this.em.persist(group).flush();

    // 3. 成功时使用 log
    this.logger.log('成员组创建成功', { groupId: group.id });

    return group;
  }
}
```

## 常见错误

### ❌ 错误：使用 NestJS 内置的 Logger

```typescript
// 错误 — 这是 NestJS 内置的，不支持 assign
import { Logger } from '@nestjs/common';
```

### ✅ 正确：使用 @nest-boot/logger

```typescript
// 正确 — 支持结构化绑定
import { Logger } from '@nest-boot/logger';
```

### ❌ 错误：手动 new Logger()

```typescript
// 错误 — 脱离了 DI 容器，无法获取请求上下文
const logger = new Logger(this);
```

### ✅ 正确：通过构造函数注入

```typescript
// 正确 — 由 NestJS DI 容器管理生命周期
constructor(private readonly logger: Logger) {}
```
