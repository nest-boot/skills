# 类型安全的定义与运用全景图

在大型架构中，队列系统是微服务隐性崩溃的重灾区。为了保障极高的重构容错率，我们通过泛型联合（Generic Unions）彻底封死任务类型缺失或拼写错误的可能。

## 1. 结构化定义作业载荷 (Types)

利用 BullMQ 提供的 `Job<DataType, ResultType, NameType>` 泛型，预先把支持分发的多种操作分别定义、并打包成联合类。

**`types/source-queue-job.type.ts`**
```typescript
import { Job } from 'bullmq';

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
import { InjectQueue } from '@nest-boot/bullmq';
import { EntityService } from '@nest-boot/mikro-orm';
import { Injectable } from '@nestjs/common';
import { Queue } from 'bullmq';

import { SOURCE_QUEUE_NAME } from './source.constants';
import { SourceQueueJob } from './types/source-queue-job.type';
import { Source } from './source.entity';

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

  async enqueueTask(sourceId: string) {
    // 3. 一旦此处撰写不规范，TSC 将即刻阻截您的调用动作
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

> **[BullMQ 避坑警示] jobId 前缀规范**
> 自定义的 `jobId` **绝对不能为纯数字字符串** (Numerical String)。这是因为 BullMQ 底层默认会为未指定 `jobId` 的任务分配自增数字 ID，如果你的自定义 ID 也是纯数字，极易引发不可预知的覆盖冲突和解析故障。
> **最佳实践**：如果 `jobId` 的主体是数据库实体 ID，**必须使用实体名称作为前缀**连接（如上文中的 `` `source-${sourceId}` ``）。

## 3. 安全消费任务 (Processor)

对应的处理器文件必须继承 `WorkerHost`，将入参同样限制为自己领域内的联合任务池 `SourceQueueJob`。由于参数有了约束，因此 `switch-case` 会自动匹配和推断下游参数，再也不用担心发生强转。

**`processors/source.processor.ts`**
```typescript
import { Processor, WorkerHost } from '@nest-boot/bullmq';
import { Logger } from '@nest-boot/logger';

import { SOURCE_QUEUE_NAME } from '../source.constants';
import { SourceQueueJob } from '../types/source-queue-job.type';

@Processor(SOURCE_QUEUE_NAME) // 利用统一名称约束
export class SourceProcessor extends WorkerHost {
  constructor(private readonly logger: Logger) {
    super();
    this.logger.setContext(SourceProcessor.name);
  }

  // 接管强类型载体输入：只负责结构路由与日志注入
  async process(job: SourceQueueJob) {
    // 注入 Job 相关的全链路追踪标识
    this.logger.assign({ jobId: job.id, jobName: job.name, jobData: job.data });

    switch (job.name) {
      case 'process': {
        await this.handleProcess(job);
        return;
      }

      case 'delete': {
        await this.handleDelete(job);
        return;
      }

      default: {
        this.logger.warn('未知的任务类型', { name: job.name });
      }
    }
  }

  // ---- 下方为独立抽离的具体业务逻辑承载函数 ----

  private async handleProcess(job: SourceQueueJob) {
    this.logger.log('开始处理资料源');

    // TODO: 1. 拉取内容 (Fetch Webpage / Extract Text)
    // TODO: 2. 内容分片 (Chunking)
    // TODO: 3. 计算向量并落盘 (Embedding & Save)

    await job.updateProgress(100);
    this.logger.log('资料源处理完成');
  }

  private async handleDelete(job: SourceQueueJob) {
    this.logger.log('开始清理资料源');
    // ...
  }
}
```

这套严格规范包含了两个极佳的架构优势：
1. **类型安全路由**：让 Queue 通道具备了如同 GraphQL 参数一般的防呆检错能力；
2. **逻辑拆分解耦**：`process` 万能路由函数保持极致精简，将核心加工逻辑分发到各个私有的 `handle` 函数中去执行。
