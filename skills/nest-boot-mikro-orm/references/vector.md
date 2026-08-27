# MikroORM 向量数据 (pgvector) 操作规范

在需要为检索增强生成 (RAG) 或语义搜索构建索引的实体中，可以使用 PostgreSQL 的 `pgvector` 扩展。

在 `@nest-boot/mikro-orm` 中使用向量字段时，先固定模型维度与距离度量，再根据数据规模和查询计划决定索引。

## 1. 字段类型声明与维度约束

TypeScript 的 `number[]` 本身不会提供 PostgreSQL vector 列类型。使用 `@nest-boot/mikro-orm` 的 `VectorType`，并传入与 embedding 模型输出一致的维度。

### ✅ 规范范例：1536维度的声明

```typescript
// source-chunk.entity.ts
import { Property } from '@mikro-orm/postgresql';

// 重点1：导入正确的环境拓展类型
import { VectorType } from '@nest-boot/mikro-orm';

export class SourceChunk {
  // 重点2：传入与所选 embedding 模型输出一致的确切维度
  @Property({ type: new VectorType(1536), nullable: true })
  embedding?: number[];
}
```

## 2. 向量近似最近邻索引 (HNSW)

B-Tree 不能加速向量距离查询。数据量和延迟目标需要近似最近邻索引时，可通过 MikroORM `@Index` expression 创建 HNSW；小表或要求精确搜索时，先基准测试再决定。

### ✅ 规范范例：动态索引建构注入

```typescript
// 在顶部连带导入 raw 和 Index
import { Entity, Index, raw } from '@mikro-orm/postgresql';

// 直接挂载于 class 顶部，利用 expression 进行底层越级改写
@Entity()
@Index({
  properties: ['embedding'],
  expression: (table, columns, indexName) =>
    raw(`create index ?? on ?? using hnsw (?? vector_cosine_ops)`, [
      indexName,
      table,
      columns.embedding,
    ]),
})
export class SourceChunk {
    // ...
}
```

**⚠️ 索引参数解读：**
- `using hnsw`：使用基于图的近似最近邻索引；它会增加构建时间、写入成本与存储占用。
- `vector_cosine_ops`：对应余弦距离。查询使用 L2、inner product 等其他度量时，索引 operator class 与查询运算符必须一致，否则索引可能无法使用或语义不一致。

## 3. 防污关联提醒

当数据库首次使用该类型时，审查生成迁移是否已经启用扩展。若生成器未覆盖此行为，在执行宿主应用的 `migration:up` 前对生成迁移做最小补充：

```typescript
    this.addSql(`create extension if not exists vector;`);
```

如果目标数据库尚未启用扩展，vector 列和索引迁移会失败。应在 disposable PostgreSQL 上执行迁移并检查扩展、列维度和查询计划。
