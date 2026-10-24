# 依赖、注册与启停

## 依赖和连接

在已有 NestJS 12 / ESM 应用中安装与锁文件一致的 peers，例如：

```bash
pnpm add @nest-boot/queue@^8.2 @nest-boot/request-context@^8 \
  @nest-boot/command@^8 bullmq@^6.3.12 zod@^4
```

核对 manifest 中其余 peers。队列核心使用 Redis。

根模块静态导入 `QueueModule`。默认连接来自 `REDIS_URL`；自定义 connection、prefix 和 defaultJobOptions 传给各队列的 `super(options)`，Worker 继承该队列的 connection/prefix。

## 注册领域 providers

队列和处理器的完整定义见 [类型与使用](usage.md)。所属模块注册 class；只导出其他模块需要注入的队列或服务：

```typescript
// source.module.ts
import { Module } from '@nestjs/common';

import { SourceProcessor } from './processors/source.processor.js';
import { SourceQueue } from './queues/source.queue.js';
import { SourceService } from './source.service.js';

@Module({
  providers: [SourceQueue, SourceProcessor, SourceService],
  exports: [SourceService],
})
export class SourceModule {}
```

在应用组合根导入 `QueueModule` 和 `SourceModule`，不要把 queue class 写进 imports。生产者也可仅注册和导出 SourceQueue，不注册 Processor。

## 启动模型

应用初始化后，每个注册队列都有自己的原生 QueueEvents reader，纯生产者进程也一样。Worker 只有显式 start 才会运行。

宿主已接入 `@nest-boot/command` 的 CLI 时：

```bash
pnpm exec nb queue:start
pnpm exec nb queue:start --queue source
pnpm exec nb queue:start --queue source --queue job
pnpm exec nb queue:start --queue job
```

- 不传 `--queue` 时启动所有已注册 Processor，包括可选 queue-api 的 `job`。
- 重复 `--queue` 只过滤所选名称；未知名称在启动前报错。
- `--queue job` 保留单独运行历史同步/清理消费者的能力。

需要同一进程提供 HTTP 并消费任务时，在 bootstrap 中显式启动：

```typescript
// main.ts
import { QueueManager } from '@nest-boot/queue';
import { NestFactory } from '@nestjs/core';

import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();
  await app.init();
  await app.get(QueueManager).start();
  await app.listen(process.env.PORT ?? 3000);
}

void bootstrap();
```

`start(['source'])` 只启动 source；`stop(names?)` 会排空对应 Worker，队列和事件 reader 仍可使用。沿用宿主已有的启动与关闭流程，不额外手建 Worker 或 Redis 连接。可用 QueueHealthIndicator 检查已注册队列的 Redis 连接。
