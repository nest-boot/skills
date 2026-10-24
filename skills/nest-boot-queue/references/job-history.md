# 可选 Job 历史与 API

## 注册与实体发现

`@nest-boot/queue-api` 8.1+ 依赖应用已配置的全局 DatabaseModule、GraphQLModule 与 AuthModule。核心 queue 包不需要这些模块；需要历史与 API 时额外静态导入 QueueApiModule。

将导出的 JobEntity 加入运行时与迁移 CLI 的实体发现：

```typescript
// mikro-orm.config.ts
import { withAuthDatabaseConfig } from '@nest-boot/auth';
import { getDatabaseConfig } from '@nest-boot/database';
import { JobEntity } from '@nest-boot/queue-api';

export default async () => {
  const config = withAuthDatabaseConfig(await getDatabaseConfig());
  return {
    ...config,
    entities: [...config.entities, JobEntity],
    entitiesTs: [...config.entitiesTs, JobEntity],
  };
};
```

应用运行时的 DatabaseModule 也使用这份配置。CLI 不启动 Nest，不能只依赖 QueueApiModule 的 imports 来完成 entity discovery。数据库表通过应用 migration 创建。

任务类型 `Job<Q, N>` 从 `@nest-boot/queue` 导入，持久化实体 JobEntity 从 `@nest-boot/queue-api` 导入，避免把两者混为一谈。

## API 可见性与作用域

只有在 API 应用注册的具体队列 class 上显式添加无参 `@QueueVisible()`，该队列的记录才可从 API 读取：

```typescript
// queues/visible-source.queue.ts
import { BaseQueue, Queue } from '@nest-boot/queue';
import { QueueVisible } from '@nest-boot/queue-api';
import { z } from 'zod';

@QueueVisible()
@Queue()
export class VisibleSourceQueue extends BaseQueue {
  readonly jobSchemas = {
    sync: { data: z.object({ sourceId: z.string() }) },
  };
}
```

这是独立的标记示例；已有 SourceQueue 应直接加标记，不通过新建子类迁移 Redis 名称。仅继承标记、未注册的队列或无标记队列不会公开。未标记任务仍可同步、清理；标记不提供授权或允许公开 payload。

- `userJob` / `userJobs`：当前用户范围。
- `workspaceJob` / `workspaceJobs`：当前工作区，仍检查有效成员与 read 权限。
- `systemJob` / `systemJobs`：userId 和 workspaceId 都缺失或 JSON null，只允许管理员 session，不把有 owner 的任务混入。
- 不提供无范围的 job/jobs；GraphQL 隐藏 data、returnValue、failedReason 等字段。

JobService 在服务层统一执行可见队列、身份和权限过滤，包括单条、分页和 count。JobEntity 没有 RLS；不要为 API 人工拼 user/workspace OR policy，也不要把直接 ORM 读取当作已经授权的公开入口。

Job 分页仅公开 CREATED_AT 排序，UUID id 作为内部游标 tie-breaker；标量 bigint 流版本不对外暴露。user/workspace JSON 路径组合索引与 system 部分索引从实体配置自动命名，按真实查询计划验证。

## 同步、清理与事件边界

内置 `job` 队列包含 sync 与 cleanup，由 JobQueue / JobProcessor 执行；不要求 ScheduleModule。同步源事件按 qualified queue name + Redis Stream ID 做 24 小时 deduplication，防止多个 QueueEvents reader 重复投递。

每个队列的 `<prefix>:<queue>:events` 是独立 Redis Stream，回调第二参数是 `ms-seq` ID。JobEntity 的 bigint lastEventMs/lastEventSeq 通过数据库原子顺序条件防止乱序覆盖；流 ID 只能在同一源队列内比较，不能拿不同队列的 ID 作全局顺序。历史记录 id 是数据库生成的 UUID，与 BullMQ jobId 分开。

读取异步同步结果允许短暂延迟。默认 reader 不回放历史，不承诺处理启动前或 reader 不在线期间的全部事件。`@QueueVisible()` 不改变这项保证。

cleanup 在每天 00:00 UTC 分批删除最后事件超过 30 天的数据库记录，lastEventMs 为 0 时退回 createdAt，适用于所有状态；不删除 Redis job。后续新事件可能重新创建记录并得到新 UUID。队列过滤同样作用于 `job`，只启动业务 worker 而不消费 job 队列时历史不会落库。
