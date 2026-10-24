# 向量字段与索引

使用 `@nest-boot/database` 的 VectorType 声明 PostgreSQL vector 字段。数据库需启用 vector 扩展；在字段和索引迁移之前执行：

```typescript
this.addSql('create extension if not exists vector;');
```

## 字段与 HNSW 索引

```typescript
import { raw } from '@mikro-orm/core';
import { Entity, Index, PrimaryKey, Property } from '@mikro-orm/decorators/legacy';
import { VectorType } from '@nest-boot/database';

@Entity()
@Index({
  properties: ['embedding'],
  expression: (columns, table, indexName) =>
    raw('create index ?? on ?? using hnsw (?? vector_cosine_ops)', [
      indexName,
      table.qualifiedName,
      columns.embedding,
    ]),
})
export class SourceChunk {
  @PrimaryKey({ type: 'integer' })
  id!: number;

  @Property({ type: new VectorType(1536), nullable: true })
  embedding?: number[];
}
```

- 数据使用非空、元素均为有限 number 的数组；null/undefined 原样保留。
- 显式维度使用正整数，与 embedding 模型输出一致。属性 metadata 的 dimensions 优先于构造参数；省略维度时列为 vector。向量长度和存储范围由 PostgreSQL 校验。
- `vector_cosine_ops` 用于余弦距离。其他距离度量需匹配相应 operator class 和查询运算符。
- Index callback 参数为 `(columns, table, indexName)`，表名使用 `table.qualifiedName`，索引名由 ORM 自动生成。
- HNSW 用于近似最近邻检索；根据数据规模、查询计划和精度需求决定是否创建。
- 使用 `{ $exists: true/false }` 查询向量是否为空。

在测试数据库执行迁移，检查扩展、列维度及实际查询计划。
