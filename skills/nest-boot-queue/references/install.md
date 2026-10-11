# 配置与局部模块注册

在使用队列进行任务分发处理时，首先需要在专属领域（Domain Module）中注册该队列。

v8 安装 `@nest-boot/queue@^8`、`@nest-boot/request-context@^8`、`@nestjs/bullmq@^12` 与兼容的 `bullmq@^5.81.5`，并核对其他 peers。Node.js >=24.21.0、NestJS 12、原生 ESM 是运行时基线。

假定你现在要为一个业务域（类似于 `Source`）创建后台任务队列，请依照如下步骤操作：

## 1. 定义队列名称常量

在依赖注入、模块注册与 Processor 装饰器之间共享同一个队列名称常量，避免重命名时遗漏字符串。

**`xxx.constants.ts`**
```typescript
export const SOURCE_QUEUE_NAME = 'source';
```

## 2. 注册队列至专属 Module

前往该领域的 `Module`，通过 `@nest-boot/queue` 提供的 `QueueModule.registerQueue(...)` 按需注册队列通道。同时，将 Processor 追加到 `providers` 列表。

**`source.module.ts`**
```typescript
import { QueueModule } from '@nest-boot/queue';
import { Module } from '@nestjs/common';

import { SOURCE_QUEUE_NAME } from './source.constants.js';
import { SourceProcessor } from './processors/source.processor.js';
import { SourceService } from './source.service.js';

@Module({
  imports: [
    // 注入定义好的名称分配一条工作队列管道
    QueueModule.registerQueue({
      name: SOURCE_QUEUE_NAME,
    }),
  ],
  providers: [SourceProcessor, SourceService],
  exports: [SourceService],
})
export class SourceModule {}
```

在注册 feature queue 前，先检查宿主应用是否已经在根模块或公共基础设施模块中完成 BullMQ/Redis 的一次性全局配置。不要假定模块一定名为 `CommonModule`，也不要在每个业务模块中重复初始化连接。

根模块可直接导入 `QueueModule`，使用 `REDIS_URL`，或用 `forRoot()` / `forRootAsync()` 指定连接。

## 3. 可选的作业持久化

`@nest-boot/queue-database` 导出抽象 `JobEntity`，应用需要声明自己的具体实体；它不是 `bullmq` 的 `Job` 类型，也没有可直接导入的具体 `Job` 表：

```typescript
// entities/queue-job.entity.ts
import { Entity } from '@mikro-orm/decorators/legacy';
import { JobEntity } from '@nest-boot/queue-database';

@Entity()
export class QueueJob extends JobEntity {}
```

让数据库运行时及迁移 CLI 都发现 `QueueJob`，再在应用模块注册：

```typescript
import { QueueDatabaseModule } from '@nest-boot/queue-database';
import { Module } from '@nestjs/common';

import { QueueJob } from './entities/queue-job.entity.js';

@Module({
  imports: [QueueDatabaseModule.forRoot({ jobEntity: QueueJob })],
})
export class JobsModule {}
```

`jobEntity` 是必填配置，不能只把静态 `QueueDatabaseModule` 放进 imports。只有在回调中写业务数据时，不必启用作业持久化模块。

引入 `HealthCheckModule` 后使用 `QueueHealthIndicator` 检查已注册队列的 Redis 连接。保留上游 `@nestjs/bullmq` 包名，但使用 Nest Boot 包导出的 Processor 和事件装饰器以获得上下文集成。
