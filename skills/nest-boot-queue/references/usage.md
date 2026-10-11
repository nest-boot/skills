# 类型安全的定义与运用全景图

队列的生产者和消费者分开运行，任务名或 payload 漂移通常只能在运行时暴露。使用 BullMQ 的泛型与可辨识联合，可以把这类不一致提前到 TypeScript 检查阶段。

## 1. 结构化定义作业载荷 (Types)

利用 BullMQ 提供的 `Job<DataType, ResultType, NameType>` 泛型，预先把支持分发的多种操作分别定义、并打包成联合类。

**`types/source-queue-job.type.ts`**
```typescript
import type { Job } from 'bullmq';

// 定义每一项专属行动的数据结构与固定名
export type SourceQueueProcessJob = Job<{ sourceId: string }, void, 'process'>;
export type SourceQueueDeleteJob = Job<{ sourceId: string }, void, 'delete'>;

// 统一对外暴露的超集、联合类型
export type SourceQueueJob = SourceQueueProcessJob | SourceQueueDeleteJob;
```

## 2. 安全投递任务 (Service)

使用 `@InjectQueue` 时，将上方设计好的常量与超集类型挂入 `Queue` 类。这样一来，开发者如果敲错了 Job Name 或者漏传了强制要求的数据，编辑器和 TypeScript 将直接抛红阻止。

**`source.service.ts`**
```typescript
import { InjectQueue } from '@nest-boot/queue';
import { EntityManager } from '@mikro-orm/postgresql';
import { EntityService } from '@nest-boot/database';
import { Injectable } from '@nestjs/common';
import { Queue } from 'bullmq';

import { SOURCE_QUEUE_NAME } from './source.constants.js';
import type { SourceQueueJob } from './types/source-queue-job.type.js';
import { Source } from './source.entity.js';

@Injectable()
export class SourceService extends EntityService<Source> {
  constructor(
    // 1. 常量注入
    @InjectQueue(SOURCE_QUEUE_NAME)
    // 2. 强类型守卫载荷
    private readonly sourceQueue: Queue<SourceQueueJob>,
    protected readonly em: EntityManager,
  ) {
    super(Source, em);
  }

  async enqueueTask(sourceId: string): Promise<void> {
    // 3. Job name 与 payload 由 SourceQueueJob 约束
    await this.sourceQueue.add(
      'process', // 完全类型约束，不可乱写
      {
        sourceId,
      },
      {
        jobId: `source-${sourceId}`,
      },
    );
  }
}
```

> **自定义 jobId**
> BullMQ 不接受纯整数形式的自定义 job ID。以数据库 ID 构造 job ID 时加入稳定的领域前缀，例如 `` `source-${sourceId}` ``，同时也能降低不同任务类型间的碰撞风险。

## 3. 安全消费任务 (Processor)

处理器继承 `WorkerHost`，并让 `process` 接收同一个 `SourceQueueJob` 联合。`switch` 根据 `job.name` 缩窄到具体任务类型。

**`processors/source.processor.ts`**
```typescript
import { Processor, WorkerHost } from '@nest-boot/queue';
import { Logger } from '@nest-boot/logger';

import { SOURCE_QUEUE_NAME } from '../source.constants.js';
import type {
  SourceQueueDeleteJob,
  SourceQueueJob,
  SourceQueueProcessJob,
} from '../types/source-queue-job.type.js';

@Processor(SOURCE_QUEUE_NAME) // 利用统一名称约束
export class SourceProcessor extends WorkerHost {
  constructor(private readonly logger: Logger) {
    super();
    this.logger.setContext(SourceProcessor.name);
  }

  // 接管强类型载体输入：只负责结构路由与日志注入
  async process(job: SourceQueueJob) {
    // 注入 Job 相关的全链路追踪标识
    this.logger.assign({ jobId: job.id, jobName: job.name, sourceId: job.data.sourceId });

    switch (job.name) {
      case 'process': {
        await this.handleProcess(job);
        return;
      }

      case 'delete': {
        await this.handleDelete(job);
        return;
      }

    }
  }

  // ---- 下方为独立抽离的具体业务逻辑承载函数 ----

  private async handleProcess(job: SourceQueueProcessJob): Promise<void> {
    this.logger.log('开始处理资料源');

    // TODO: 1. 拉取内容 (Fetch Webpage / Extract Text)
    // TODO: 2. 内容分片 (Chunking)
    // TODO: 3. 计算向量并落盘 (Embedding & Save)

    await job.updateProgress(100);
    this.logger.log('资料源处理完成');
  }

  private async handleDelete(job: SourceQueueDeleteJob): Promise<void> {
    this.logger.log('开始清理资料源');
    // ...
  }
}
```

`@nest-boot/queue` 的 `@Processor` 会为每个 job 建立 `RequestContext`，因此处理器内可安全使用 `Logger.assign()` 绑定 job 级字段。保持 `process` 只负责路由，让具体处理方法接收缩窄后的 Job 类型。

持久化在队列中的数据不会经过 TypeScript 验证；外部 producer、旧任务或不可信 payload 仍需在入口做运行时校验，不把类型联合当成安全边界。

## 4. 事件回调也需要上下文

v8 的 `OnWorkerEvent`、`OnQueueEvent` 从 `@nest-boot/queue` 导入。它们包装事件回调并建立自己的 RequestContext；上游同名装饰器不提供 Nest Boot 的生命周期。事件回调并不继承原 HTTP 用户/成员身份，需要业务查询时从可信 job 数据重新授权并设置精确 scope。只记录 job/resource 标识，不记录完整 payload。
