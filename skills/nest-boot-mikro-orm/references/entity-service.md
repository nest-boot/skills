# `nest-boot-mikro-orm` 之 EntityService 设计准则

在 NestJS 项目体系内当需要部署使用 `@nest-boot/mikro-orm` 架构时，一切围绕单一目标实体开发的业务服务类都请默认继承至 `EntityService<T>` 基类。该基类直接提供了一套威能强劲的底层数据访问集成库方案，旨在彻底剔除我们编写套路般重复增删改查 (CRUD) 冗余块所需的全部努力。

## 大前提铁律: 杜绝编写毫无意义的包装器 (Wrappers)

**不要**在你亲手捏造的 Service 主体类里，创建那些仅仅只是去呼叫、传递给 `EntityService` 早已开箱即用提供的操作方法的自定义包裹函数。

### 坏代码示范 (极差的反向案例)

```typescript
@Injectable()
export class SourceChunkService extends EntityService<SourceChunk> {
  constructor(protected readonly em: EntityManager) {
    super(SourceChunk, em);
  }

  // 极为差劲: 毫无存在意义的壳子方法！下述所需的所有实体处理其实 `EntityService.create` 都能做且做得更好。
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

### 优秀代码示范 (巧妙应用 EntityService 带来的赋能)

正确的做法其实是，无论你在 Controller 还是 Resolver 下直接去利用本就已经具备完善范型的底层方法 `.create()` 就好，此做法不仅免去了多余文件开销也极大化避免了不必要的心智折损：

```typescript
// Controller, Resolver, 或者 Workflow 系统执行的节点:
const chunk = await this.sourceChunkService.create({
  source: sourceEntity,
  index: input.index,
  content: input.content,
  embedding: input.embedding,
});
```

## 直接可用的强悍内置操作集

得益于 `EntityService<T>` 的深度整合，我们可以放任使用下面这一系列绝对类型安全的内置函数方法阵列：

- **`create(data: RequiredEntityData<T>): Promise<T>`**: 初始化、实例化并即时持久封存在库里的插入动作集成体。
- **`findOne(idOrEntityOrWhere): Promise<Loaded<T> | null>`**: 请求获取单独记录，并静默豁免因无法查获实体进而抛出任意报错的干扰。
- **`findOneOrFail(idOrEntityOrWhere): Promise<Loaded<T>>`**: 若目标未能找到即当场进行强约束型中断并掷出未寻找到的 404 (Not Found) 终端信号的可靠抓取法。
- **`findAll(where, options): Promise<Loaded<T>[]>`**: 支持搭配条件映射联合提取大批查询结果集的多重过滤器结构方法。
- **`update(idOrEntity, data): Promise<T>`**: 通过直达标识(ID)亦或者内存加载的对象即刻发起向源端修改赋值的刷新命令。
- **`remove(idOrEntity, softDelete?): Promise<T>`**: 发出极具宽容性的安全软硬删除指令清消对象。
- **`count(where, options): Promise<number>`**: 专门规避过度下载沉重的内存对象模型并单独计算列项数量极速求总合的函数。
- **`chunkById(where, options, callback): Promise<this>`**: 用于应对大批量且严酷数据堆中基于分布式或者批处理分片进行按 ID 步进流式游标执行处理的神奇手段，可极力压低下标显存使用。

## 什么时候才轮到自行订制扩大的自研方法？

除非业务范畴涉及之下情况的边缘场景，否则请再三审视是否真的有自定义挂载查询的必要：
1. **需牵引横跨多个域表的强一致性分布式锁事物** (比如运用上了严格排查隔离度序列化的更新流处理)。
2. **极度特异化的图谱和分组求总逻辑** (Aggregations and grouped statements)，单纯依靠通用 `findAll` 已经完全无法轻松解析组装出结构。
3. **关联关系的定制处理** 比如多对多关系的维护、中间表的写库封装等。
4. **牵连到了极为复杂的重度外部业务侧** 比如在写库期间要伴随发出远程外部 API 网络信号且要求即时失效某些周边缓存机制的处理。

### 自定义方法的参数规范：全面使用 `IdOrEntity<T>`

当你确认必须编写自定义的 Service 方法时，请**务必将接受实体的参数声明为 `IdOrEntity<T>`**，而非单一的 `T`（全量实体对象）或 `string`/`number`（仅 ID）。

**这是由于所有继承至 `EntityService` 的底层方法（`findOneOrFail`、`update` 等），天生完美兼容 `IdOrEntity<T>` 的联合类型体。**

#### 优势：
- 高度扩展性：让上层客户端（如 Resolver/Controller/其它 Agent）不用纠结于传递进来的是一个刚提取完毕的完整实体，还是仅仅是一个外键 ID 字符串。
- 零开销加载：你可以在方法内部统一使用 `this.findOneOrFail(idOrEntity)` 或 `this.em.findOneOrFail(Entity, idOrEntity)` 揽收对象；若传入的本身就是实体缓冲池记录的完整对象，MikroORM 的 Identity Map 机制会直接将其作为脱水载体返还，**绝对不会由此多产生一次无意义的 SQL SELECT 扫描。**

#### 范例：
```typescript
import { EntityService, IdOrEntity } from '@nest-boot/mikro-orm';

@Injectable()
export class NotebookService extends EntityService<Notebook> {
  // 规范写法：参数兼容 ID 亦或者是 对象
  async doComplexAction(
    notebookIdOrEntity: IdOrEntity<Notebook>,
    sourceIdOrEntity: IdOrEntity<Source>
  ): Promise<void> {
    const [notebook, source] = await Promise.all([
      this.findOneOrFail(notebookIdOrEntity),
      this.em.findOneOrFail(Source, sourceIdOrEntity),
    ]);

    // ... 执行强业务逻辑
  }
}
```

最后重申，永远在企图亲手制造某个特定基础逻辑前先行查阅 `EntityService` 原生能够带来哪些福利供给。
