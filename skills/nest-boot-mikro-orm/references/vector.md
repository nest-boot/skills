# MikroORM 向量数据 (pgvector) 操作规范

在需要针对大语言模型 (LLM) 进行检索增强生成 (RAG) 或是构建语义索引的各类实体中（诸如 `SourceChunk`），我们会大量用到 PostgreSQL 的原生向量支持库 `pgvector`。

为了在 `@nest-boot/mikro-orm` 底座上完美整合这一扩展并确保查询性能不塌陷，请严格按照以下规范对实体 (Entity) 模型中的向量属性进行雕琢。

## 1. 字段类型声明与维度约束

传统的 `number[]` 类型无法正确在数据库中映射为受到约束的连续数值阵列。必须利用来自于我们专用包 `@nest-boot/mikro-orm` 中的 `VectorType` 实例，并在初始化阶段为其**强行注入维度尺寸**。

### ✅ 规范范例：1536维度的声明

```typescript
// source-chunk.entity.ts
import { Property } from '@mikro-orm/postgresql';

// 重点1：导入正确的环境拓展类型
import { VectorType } from '@nest-boot/mikro-orm';

export class SourceChunk {
  // 重点2：传入确切的维度（如 OpenAI text-embedding-ada-002 的标准 1536 维）
  @Property({ type: new VectorType(1536), nullable: true })
  embedding?: number[];
}
```

## 2. 向量近似最近邻索引 (HNSW)

原生的普通 B-Tree 等老式倒排树索引对于向量而言毫无用处。如果不特地增加向量级的高级索引，随着 Chunk 的增多查询效率将会崩塌。我们需要借助 MikroORM 的 `@Index` 暴露的原生回调能力，手写 `hnsw` 索引：

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
- `using hnsw`：强制声明使用基于图的近似最近邻搜索索引架构（相较于 `ivfflat` 无需事先用足够的数据量 `fit`，即用即建，召回率表现卓然）。
- `vector_cosine_ops`：明确声明针对“余弦相似度”（Cosine Similarity）去预编排图距。如果你在查询应用端使用的是其他的比对基准（如 `L2 距离 / 欧式操作 (vector_l2_ops)`），这里的操作符名必须更换对齐！

## 3. 防污关联提醒

**极其重要！**：就像《[MikroORM 迁移指南](migration.md)》的第四节所言，当你初次在一个数据库或者新建表内使用该类型声明时，请务必在运行 `pnpm run migration:up` 之前，去人工编辑生成的迁移脚本并手动于上方执行：

```typescript
    this.addSql(`create extension if not exists vector;`);
```

一旦遗漏，后续所有牵扯到该实体的 `VectorType` 建表语句均会当场报错。
