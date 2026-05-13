# 关联处理最佳实践：多对多与关系表管理

在 MikroORM 开发中，处理中间表（如代表多对多关系的联合实体 `NotebookSource`、`UserGroup` 等）通常会涉及到关联的创建和销毁。

## 使用 IdOrEntity

在编写用于操作关联关系的专门方法时，参数必须使用 `IdOrEntity<T>` 以兼容接收实体的完整对象或它的主键 `id`，这不仅为接口赋予了极大灵活性，也方便上层 Resolver 直传参数：

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

对于多对多关联表的创建，应当采用 `em.upsert` 方案，并通过配置 `onConflictAction: 'ignore'` 平滑地处理可能遇到的唯一索引冲突。这避免了传统的“先查再建”引发的条件竞争 (Race Condition) 并显著降低了连接开销。

> **前置条件**：该中间层 Entity 必须拥有 `@Unique` 装饰器标识唯一键，例如 `@Unique({ properties: ['notebook', 'source'] })`

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

与常规的 `remove` 加载完整对象后再删除不同，直接通过 `em.nativeDelete` 在大多数场景下更加极致精简、防止产生无意义的 SELECT 操作：

```typescript
async removeSource(
  notebookIdOrEntity: IdOrEntity<Notebook>,
  sourceIdOrEntity: IdOrEntity<Source>,
): Promise<Source> {
  const [notebook, source] = await Promise.all([
    this.findOneOrFail(notebookIdOrEntity),
    this.em.findOneOrFail(Source, sourceIdOrEntity),
  ]);

  // 直接执行原生删除语句、不会触发级联钩子，极其高效
  await this.em.nativeDelete(NotebookSource, {
    notebook,
    source,
  });

  return source;
}
```

## 清理孤儿实体（Orphan Cleanup）

在解绑多对多关系后，如果发现目标载体是一个孤儿（没有任何关联对象），需要用极短的代码补全生命周期的兜底销毁，可以通过 `count` 快速排查：

```typescript
// 紧接上面的 removeSource 逻辑
const remaining = await this.em.count(NotebookSource, {
  source, // 检查该 source 仍旧挂载的其他 NotebookSource 数量
});

if (remaining === 0) {
  await this.em.remove(source).flush();
}
```
