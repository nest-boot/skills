# 使用方法与最佳实践

## Logger API

`Logger` 类实现了 NestJS 的 `LoggerService` 接口，底层基于 pino。以下是完整的方法列表：

| 方法 | 描述 | 典型场景 |
|---|---|---|
| `setContext(name)` | 覆盖自动推断的日志上下文名称 | 动态 Processor 等无法正确推断注入类名时 |
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
  constructor(private readonly logger: Logger) {}
}
```

> **注意：** 导入的是 `@nest-boot/logger` 的 `Logger`，而不是 `@nestjs/common` 的 `Logger`。二者同名但完全不同。

## 标准用法模式

### 1. 使用自动上下文

通过构造函数注入时，Logger 通常会自动把注入类名作为 context，无需重复调用 `setContext()`：

```typescript
constructor(private readonly logger: Logger) {}
```

如果动态 Processor 或工厂场景无法推断正确类名，再显式调用 `setContext(MyProcessor.name)`。

### 2. 方法入口处绑定关键参数

使用 `assign` 在活动 RequestContext 中绑定业务追踪参数。这些参数会附着到该上下文后续的日志条目：

```typescript
async createProject(tenant: Tenant, input: CreateProjectInput) {
  this.logger.assign({ tenantId: tenant.id });

  // 后续的 log/warn/error 都会自动携带 tenantId
  this.logger.log('开始创建项目');
  // 输出: {"level":"info","context":"MyService","tenantId":"123","msg":"开始创建项目"}
}
```

HTTP/GraphQL 请求和 `@nest-boot/bullmq` Processor 会建立 RequestContext。独立脚本、原生 BullMQ worker 或其他后台入口中，先使用宿主应用的 RequestContext helper 建立上下文；否则不要调用 `assign()`，改为在单次日志调用中传入安全字段。

### 3. 按级别输出日志

```typescript
// 信息级 — 操作成功
this.logger.log('项目创建成功', { projectId: project.id });

// 警告级 — 业务逻辑校验失败（非致命）
this.logger.warn('项目名称已存在', { name: input.name });

// 错误级 — 不可恢复的系统错误
this.logger.error('数据库连接失败', { error: err.message });
```

## 完整示例

以下通用示例展示一个典型的结构化日志集成：

```typescript
import { EntityManager } from '@mikro-orm/postgresql';
import { Logger } from '@nest-boot/logger';
import { EntityService } from '@nest-boot/mikro-orm';
import { BadRequestException, Injectable } from '@nestjs/common';

@Injectable()
export class ProjectService extends EntityService<Project> {
  constructor(
    protected readonly em: EntityManager,
    private readonly logger: Logger,
  ) {
    super(Project, em);
  }

  async createProject(tenant: Tenant, input: CreateInput) {
    // 1. 入口处绑定追踪参数
    this.logger.assign({ tenantId: tenant.id });

    // 2. 校验逻辑中使用 warn
    const existing = await this.findOne({ name: input.name, tenant });
    if (existing) {
      this.logger.warn('项目名称已存在');
      throw new BadRequestException('项目名称已存在');
    }

    const project = this.em.create(Project, { ... });
    await this.em.persist(project).flush();

    // 3. 成功时使用 log
    this.logger.log('项目创建成功', { projectId: project.id });

    return project;
  }
}
```

## 常见错误

### ❌ 错误：记录凭证或完整第三方载荷

```typescript
this.logger.assign({ authorization: request.headers.authorization });
this.logger.error('Webhook failed', { body: request.body });
```

认证头、Cookie、API key、私钥、供应商签名与完整 webhook body 可能包含长期
凭证或个人信息。即使是调试环境也不要记录。

### ✅ 正确：记录安全业务标识与分类后的错误

```typescript
this.logger.assign({
  provider: event.provider,
  eventId: event.id,
  resourceId: resource.id,
});
this.logger.error('Webhook processing failed', {
  errorName: error.name,
  failureKind: 'signature_verification',
});
```

如果错误对象可能携带请求配置或 header，不要直接展开/序列化整个对象；
使用预先分类的安全字段；只有证明 `error.message` 已脱敏时才可记录。
生产排障还应结合健康端点、运行实例状态和限定时间窗口的日志，
不要把一次启动期重试误判为持续故障。

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
