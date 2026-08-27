# EntityService 使用与扩展边界

`EntityService<T>` 提供带 DataLoader 的常用实体操作。以单一实体为中心、且宿主模块已经完成 EntityManager 注入的 Service，可以继承它来复用一致的数据访问行为。

## 避免无语义包装

不要创建只转发参数、没有权限校验、事务、领域规则或返回值转换的包装方法。

### 不推荐：重复实现 create

```typescript
@Injectable()
export class SourceChunkService extends EntityService<SourceChunk> {
  constructor(protected readonly em: EntityManager) {
    super(SourceChunk, em);
  }

  // 仅重复 EntityService.create 的行为，没有增加领域语义。
  async createSourceChunk(
    source: Source,
    input: { index: number; content: string; embedding: number[] },
  ): Promise<SourceChunk> {
    const chunk = this.em.create(SourceChunk, {
      source,
      ...input
    });

    await this.em.persist(chunk).flush();
    return chunk;
  }
}
```

### 推荐：复用继承方法

通过领域 Service 调用继承的 `.create()`，让类型和持久化行为保持一致：

```typescript
// Controller, Resolver, 或者 Workflow 系统执行的节点:
const chunk = await this.sourceChunkService.create({
  source: sourceEntity,
  index: input.index,
  content: input.content,
  embedding: input.embedding,
});
```

## 内置操作

当前 `EntityService<T>` 提供：

- **`create(data)`**：创建、持久化并 flush 一个实体。
- **`findOne(idOrEntityOrWhere)`**：按 ID、实体或过滤条件查询；未找到时返回 `null`。
- **`findOneOrFail(idOrEntityOrWhere)`**：未找到时抛出 NestJS `NotFoundException`。
- **`findAll(where, options)`**：按 MikroORM `FindOptions` 查询多个实体。
- **`update(idOrEntity, data, options?)`**：过滤 `undefined` 字段后 assign 并 flush。
- **`remove(idOrEntity, softDelete?)`**：默认尝试软删除；实体没有配置的软删除字段时执行硬删除。
- **`count(where, options?)`**：直接计数，不加载完整实体。
- **`chunkById(where, options, callback)`**：按 ID 升序分块处理；显式设置 `options.limit` 作为块大小。

修改框架版本后应重新对照 `EntityService` 源码或类型声明，不要让此方法清单成为过时副本。

## 何时增加自定义方法

以下情况通常具有独立领域语义：

1. 跨实体事务、锁或一致性边界；
2. 聚合、分组或不能由通用 `findAll` 清晰表达的查询；
3. 多对多关系和显式中间实体的维护；
4. 权限校验、状态机、缓存失效或外部系统协调；
5. 需要稳定封装 populate、过滤条件或返回 DTO 的读取路径。

### 需要兼容 ID 与实体时使用 `IdOrEntity<T>`

当调用方确实可能持有 ID 或已加载实体时，参数可声明为 `IdOrEntity<T>`。如果业务边界只允许 ID，保留窄类型更清晰，不必为了灵活性扩大 API。

`EntityService.findOneOrFail`、`update` 和 `remove` 原生接受 `IdOrEntity<T>`。直接调用 MikroORM `EntityManager` 时，应以其实际方法签名为准，不要假定所有 API 都接受同一联合类型。

#### 优势：
- 调用方已有受管实体时可以直接传入，只有 ID 时也无需预加载。
- `EntityService.findOneOrFail` 会先检查当前 UnitOfWork 的 identity map；是否执行 SQL 仍取决于实体是否受管和当前 EntityManager 上下文，不能把它视为无条件零查询。

#### 范例：
```typescript
import { EntityService, IdOrEntity } from '@nest-boot/mikro-orm';

@Injectable()
export class NotebookService extends EntityService<Notebook> {
  // 规范写法：参数兼容 ID 亦或者是 对象
  async doComplexAction(
    notebookIdOrEntity: IdOrEntity<Notebook>,
    sourceId: Source['id'],
  ): Promise<void> {
    const [notebook, source] = await Promise.all([
      this.findOneOrFail(notebookIdOrEntity),
      this.em.findOneOrFail(Source, sourceId),
    ]);

    // ... 执行强业务逻辑
  }
}
```
