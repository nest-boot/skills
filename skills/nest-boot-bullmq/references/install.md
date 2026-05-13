# 配置与局部模块注册

在使用队列进行任务分发处理时，首先需要在专属领域（Domain Module）中注册该队列。

假定你现在要为一个业务域（类似于 `Source`）创建后台任务队列，请依照如下步骤操作：

## 1. 定义队列名称常量

永远不要在依赖注入或装饰器中硬编码队列的名字字符串。第一时间在对应的 `constants` 文件中声明它。

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

*(注意：底层与 Redis 链接通信所需的全局 `BullModule` 配置化已统一在项目 `CommonModule` 等基础设施层启动，各子系统只需聚焦于自己 `registerQueue` 的声明即可。)*
