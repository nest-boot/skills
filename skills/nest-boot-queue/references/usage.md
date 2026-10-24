# 类型、校验和事件

## Queue 是任务契约的单一来源

```typescript
// queues/source.queue.ts
import { BaseQueue, Queue } from '@nest-boot/queue';
import { z } from 'zod';

@Queue()
export class SourceQueue extends BaseQueue {
  readonly jobSchemas = {
    sync: {
      data: z.object({ sourceId: z.string() }),
      result: z.object({ sourceId: z.string() }),
    },
    'delete-source': {
      data: z.object({ sourceId: z.string() }),
    },
  };

  constructor() {
    super({
      defaultJobOptions: {
        attempts: 3,
        backoff: { type: 'exponential', delay: 1000 },
        removeOnComplete: { age: 86400, count: 1000 },
      },
    });
  }
}
```

`@Queue()` 将 SourceQueue 命名为 `source`。需要兼容已有 Redis 名称时显式用 `@Queue('stable-name')`；只改 class 名就可能改变推导名称。

`jobSchemas` 保留具体 key 和 schema 的推导。不要写 `readonly jobSchemas: JobSchemas = ...`，也不要把已经是整个 Job 的联合塞入原生 `Queue<JobUnion>` 的 data 泛型。

## 直接注入队列并投递

```typescript
// source.service.ts
import { Injectable } from '@nestjs/common';

import { SourceQueue } from './queues/source.queue.js';

@Injectable()
export class SourceService {
  constructor(private readonly queue: SourceQueue) {}

  async synchronize(sourceId: string): Promise<void> {
    await this.queue.add('sync', { sourceId }, { jobId: `source-sync-${sourceId}` });
  }
}
```

`add` / `addBulk` 关联校验 name 与 data；addBulk 会在写入任何任务前校验整个批次。稳定 jobId 或 BullMQ deduplication 可抑制重复投递，但有保留/清除窗口；业务副作用仍应幂等。不要使用纯整数或包含冒号的自定义 jobId。

## 每个任务一个方法

```typescript
// processors/source.processor.ts
import { Logger } from '@nest-boot/logger';
import { BaseProcessor, type Job, type JobResult, Processor } from '@nest-boot/queue';

import { SourceQueue } from '../queues/source.queue.js';

@Processor(SourceQueue)
export class SourceProcessor extends BaseProcessor {
  constructor(private readonly logger: Logger) {
    super({ concurrency: 2 });
  }

  async processSync(
    job: Job<SourceQueue, 'sync'>,
  ): Promise<JobResult<SourceQueue, 'sync'>> {
    this.logger.assign({ jobId: job.id, jobName: job.name, sourceId: job.data.sourceId });
    // 真实同步工作委托给领域 Service，并在返回前 await 完成。
    await job.updateProgress(100);
    return { sourceId: job.data.sourceId };
  }

  async processDeleteSource(job: Job<SourceQueue, 'delete-source'>): Promise<void> {
    this.logger.assign({ jobId: job.id, jobName: job.name, sourceId: job.data.sourceId });
    // 在这里 await 领域 Service 的删除操作，不保存当前 job 到 singleton 字段。
    await job.updateProgress(100);
  }
}
```

`@Processor(SourceQueue)` 检查所有必需 handler 及其 Job/返回契约。缺少方法、用另一任务的 Job 或返回错误结果都应在类型检查时暴露；显式宽泛 any、断言等可绕过 TS，不能把这些当成正确用法。

- `send-email` → `processSendEmail`，`sendEmail` 也会映射到同名方法；这样的任务组合会在编译期与运行时被拒绝。
- 不实现通用 `async process(job)`；未知任务、缺失 handler 等无法分发的任务在运行时失败，不自动无限重试。
- 类名前缀由 `@nest-boot/queue/processor-name` ESLint 规则约束，例如 SourceQueue / SourceProcessor；TS 装饰器约束的是任务方法与类型，不比较 class 名字符串。
- Processor 的 `worker`、Queue 的 `queueEvents` 是受框架管理的只读访问器；worker 启动前或事件 reader 初始化前读取会报错。Processor 不提供旧 `this.queue` 或 `this.on` 封装，需要队列操作时直接注入 SourceQueue。

## Zod 是异步验证，不是持久化转换

data 顶层必须是 `z.object()`，result 可以是任意 Zod schema，省略 result 时返回 void。队列按 `z.input` 推导类型，用 `parseAsync` 支持异步 refine，但保留原 data/result，丢弃解析结果。

因此 `z.coerce`、default、strip 或 transform 不会替换 Redis 中的值，也不会把 handler 的输入改成解析输出。例如 string-to-number transform 不会让 consumer 收到 number；需要规范化时在业务边界显式完成，再投递稳定的 JSON 契约。不要用 Date、bigint、undefined 等无法稳定 JSON 往返的值表达任务数据。

add/addBulk、upsertJobScheduler 模板、消费前和结果完成前都会校验。直接调用 BullMQ 的 `job.updateData()` 等底层 API 不经过这层封装，消费时仍会复验；不可信 producer 和旧版本消息不能只依赖 TS。

## RequestContext 与事件

每个消费任务使用独立的 `type: 'queue'` RequestContext。Logger.assign、数据库 fork、临时目录等生命周期包住完整 awaited handler，但原 HTTP 身份不会自动传播。载荷含 userId/workspaceId 也不等于已经授权，先查可信业务关系再执行写入。

QueueManager 为每个注册队列创建 QueueEvents；每个 reader 只监听该队列，各实例会收到重复事件。可以在应用初始化后通过 `queue.queueEvents.on(...)` 使用原生回调；如回调要访问 RequestContext 依赖，需显式建立并等待自己的完整上下文，不能假定回调继承原 job 的上下文。

不使用已移除的 OnWorkerEvent、OnQueueEvent 或 QueueEventsHost。原生 Worker 事件可以通过 `processor.worker.on(...)` 监听，同样自行处理异步回调的错误和上下文。

reader 沿用 BullMQ 默认起点，不回放历史，也不维护 lastEventId。事件读取与 job 创建之间有启动窗口，不能把这些事件当作可靠补偿日志；需要历史查询时使用可选 queue-api。

依据：[Queue 教程](https://github.com/nest-boot/nest-boot/blob/main/apps/docs/content/docs/tutorial/queue.mdx)、[类型定义](https://github.com/nest-boot/nest-boot/blob/main/packages/queue/src/interfaces/job.interface.ts)。
