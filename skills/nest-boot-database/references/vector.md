# MikroORM 向量数据 (pgvector) 操作规范

在需要为检索增强生成 (RAG) 或语义搜索构建索引的实体中，可以使用 PostgreSQL 的 `pgvector` 扩展。

在 `@nest-boot/database` 中使用向量字段时，先固定模型维度与距离度量，再根据数据规模和查询计划决定索引。

## 实现与版本

以包含 [PR #427](https://github.com/nest-boot/nest-boot/pull/427) 的 `@nest-boot/database@8.1.1` 修复为基线。VectorType 直接继承 `@mikro-orm/core` 公开的 `Type`，不再依赖 npm 的 `pgvector` 包；PostgreSQL 的 `vector` 扩展仍需由数据库部署安装。

已发布的 8.1.0 存在旧声明继承链导致的 TS2322（[Issue #426](https://github.com/nest-boot/nest-boot/issues/426)），升级到包含修复的版本后复验消费者类型，不再把它列为当前实现的阻断限制。不用 `as any`、忽略错误或额外安装旧 pgvector adapter 绕过问题。

核对宿主锁定的包版本与实际声明；修复是否进入 main、是否已发布、项目是否已升级是不同状态。公开消费者应能通过 strict NodeNext 编译，覆盖实例形式、class 形式及 MikroORM Type 赋值，而不仅是内部 mock 测试。

## 1. 字段类型声明与维度约束

TypeScript 的 `number[]` 本身不会提供 PostgreSQL vector 列类型。使用 `@nest-boot/database` 的 `VectorType`，并传入与 embedding 模型输出一致的维度。

### ✅ 规范范例：1536维度的声明

```typescript
// source-chunk.entity.ts
import { Property } from '@mikro-orm/decorators/legacy';

// 重点1：导入正确的环境拓展类型
import { VectorType } from '@nest-boot/database';

export class SourceChunk {
  // 重点2：传入与所选 embedding 模型输出一致的确切维度
  @Property({ type: new VectorType(1536), nullable: true })
  embedding?: number[];
}
```

VectorType 的 JS 值是非空、元素均为有限 number 的数组；不把数字字符串强制转为数字。空数组、NaN、Infinity、非数值元素和非法数据库向量文本会被拒绝，null/undefined 原样保留。显式维度必须为正整数；属性 metadata 的 dimensions 优先于构造参数，不指定维度时列为 vector。实际向量长度与维度匹配、float32 存储范围仍由 PostgreSQL 校验，不能把本地数值检查当作完整数据库校验。

`$exists: true/false` 的布尔值是查询指令，MikroORM 的查询转换路径会保留它；这不代表字段本身接受布尔向量值。验证时检查正常向量序列化、非法输入拒绝和 `$exists` 查询生成，不能据此宣称已完成带 vector 扩展的数据库往返测试。

## 2. 向量近似最近邻索引 (HNSW)

B-Tree 不能加速向量距离查询。数据量和延迟目标需要近似最近邻索引时，可通过 MikroORM `@Index` expression 创建 HNSW；小表或要求精确搜索时，先基准测试再决定。

### ✅ 规范范例：动态索引建构注入

```typescript
// 在顶部连带导入 raw 和 Index
import { raw } from '@mikro-orm/core';
import { Entity, Index } from '@mikro-orm/decorators/legacy';

// 直接挂载于 class 顶部，利用 expression 进行底层越级改写
@Entity()
@Index({
  properties: ['embedding'],
  expression: (columns, table, indexName) =>
    raw(`create index ?? on ?? using hnsw (?? vector_cosine_ops)`, [
      indexName,
      table.qualifiedName,
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

MikroORM 7.2 的 Index callback 参数顺序是 `(columns, table, indexName)`；table 是包含 name、schema、qualifiedName 的对象，SQL 使用 `table.qualifiedName`。索引名交给 ORM 根据 properties 自动生成，不硬编码 name。

当数据库首次使用该类型时，审查生成迁移是否已经启用扩展。若未启用，用先于向量列/索引运行的独立基础设施迁移安装扩展：

```typescript
    this.addSql(`create extension if not exists vector;`);
```

如果目标数据库尚未启用扩展，vector 列和索引迁移会失败。应在 disposable PostgreSQL 上执行迁移并检查扩展、列维度和查询计划。
