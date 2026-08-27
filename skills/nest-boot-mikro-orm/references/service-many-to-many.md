# 关联处理最佳实践：多对多与关系表管理

在 MikroORM 开发中，处理中间表（如代表多对多关系的联合实体 `NotebookSource`、`UserGroup` 等）通常会涉及到关联的创建和销毁。

## 使用 IdOrEntity

当关联方法需要同时接受主键与已加载实体时，使用 `IdOrEntity<T>`；如果边界只允许主键，保留 ID 类型更容易验证权限与来源：

```typescript
import { IdOrEntity } from '@nest-boot/mikro-orm';

async addSource(
  notebookIdOrEntity: IdOrEntity<Notebook>,
  sourceIdOrEntity: IdOrEntity<Source>,
): Promise<Source> {
  // 解析主实体
  const [notebook, source] = await Promise.all([
    this.findOneOrFail(notebookIdOrEntity),
    this.em.findOneOrFail(Source, sourceIdOrEntity),
  ]);

  // 构建并持久化关联...
}
```

## `upsert` 处理冲突：添加关联

对于要求幂等添加的显式关系实体，可以使用 `em.upsert` 和 `onConflictAction: 'ignore'` 处理唯一键冲突。这避免“先查再建”的竞态。

> **前置条件**：数据库必须存在与 `onConflictFields` 对应的唯一约束，例如 `@Unique({ properties: ['notebook', 'source'] })`。

```typescript
async addSource(
  notebookIdOrEntity: IdOrEntity<Notebook>,
  sourceIdOrEntity: IdOrEntity<Source>,
): Promise<Source> {
  const [notebook, source] = await Promise.all([
    this.findOneOrFail(notebookIdOrEntity),
    this.em.findOneOrFail(Source, sourceIdOrEntity),
  ]);

  await this.em.upsert(
    NotebookSource,
    { notebook, source },
    {
      onConflictAction: 'ignore', // 存在则忽略，实现安全的等幂添加
      onConflictFields: ['notebook', 'source'],
    },
  );

  return source;
}
```

## `nativeDelete`：移除关联

不需要加载关系实体或触发其 ORM 生命周期 hooks 时，可以用 `em.nativeDelete` 直接按条件删除：

```typescript
async removeSource(
  notebookIdOrEntity: IdOrEntity<Notebook>,
  sourceIdOrEntity: IdOrEntity<Source>,
): Promise<Source> {
  const [notebook, source] = await Promise.all([
    this.findOneOrFail(notebookIdOrEntity),
    this.em.findOneOrFail(Source, sourceIdOrEntity),
  ]);

  // 不触发关系实体的 ORM hooks；数据库 FK 的 cascade/restrict 仍然生效。
  await this.em.nativeDelete(NotebookSource, {
    notebook,
    source,
  });

  return source;
}
```

## 清理孤儿实体（Orphan Cleanup）

只有领域所有权明确规定“失去最后一个关联即可删除”时才清理孤儿实体。把解绑、计数和删除放进同一事务，并在并发添加关系的场景使用合适的锁或数据库约束：

```typescript
// 紧接上面的 removeSource 逻辑
const remaining = await this.em.count(NotebookSource, {
  source, // 检查该 source 仍旧挂载的其他 NotebookSource 数量
});

if (remaining === 0) {
  await this.em.remove(source).flush();
}
```

若 Source 可被其他领域引用或需要审计保留，不要仅凭当前关系表计数自动删除。
