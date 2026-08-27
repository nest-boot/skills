# 配置与局部模块注册

在使用队列进行任务分发处理时，首先需要在专属领域（Domain Module）中注册该队列。

假定你现在要为一个业务域（类似于 `Source`）创建后台任务队列，请依照如下步骤操作：

## 1. 定义队列名称常量

在依赖注入、模块注册与 Processor 装饰器之间共享同一个队列名称常量，避免重命名时遗漏字符串。

**`xxx.constants.ts`**
```typescript
export const SOURCE_QUEUE_NAME = 'source';
```

## 2. 注册队列至专属 Module

前往该领域的 `Module`，通过 `@nest-boot/bullmq` 提供的 `BullModule.registerQueue(...)` 按需注册队列通道。同时，切记将您的 `Processor` 追加到 `providers` 列表。

**`source.module.ts`**
```typescript
import { BullModule } from '@nest-boot/bullmq';
import { Module } from '@nestjs/common';

import { SOURCE_QUEUE_NAME } from './source.constants';
import { SourceProcessor } from './processors/source.processor';
import { SourceService } from './source.service';

@Module({
  imports: [
    // 注入定义好的名称分配一条工作队列管道
    BullModule.registerQueue({
      name: SOURCE_QUEUE_NAME,
    }),
  ],
  providers: [SourceProcessor, SourceService],
  exports: [SourceService],
})
export class SourceModule {}
```

在注册 feature queue 前，先检查宿主应用是否已经在根模块或公共基础设施模块中完成 BullMQ/Redis 的一次性全局配置。不要假定模块一定名为 `CommonModule`，也不要在每个业务模块中重复初始化连接。
