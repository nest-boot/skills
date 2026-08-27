---
name: nest-boot-domain-renaming
description: 在 NestJS 与 `@nest-boot` 应用中执行跨层领域、实体、模块或持久化概念重命名的完整工作流。适用于同步修改目录、文件、TypeScript 符号、依赖注入、GraphQL schema/operation、MikroORM 实体与表列、迁移、RLS policy、队列、客户端、测试和文档，并区分本地概念、通用术语、外部协议与存量数据；普通文件组织使用 `nest-boot-module-design`。
---

## 概览

领域重命名不是文本替换。目标是让代码、公开契约、数据库和消费者只保留一套明确语义，同时保护外部协议兼容性与存量数据。

## 工作流程

1. **定义语义边界。** 写出 old → new 映射，并标记哪些同形词属于通用领域、供应商协议、URL、metadata 或历史数据，不能机械替换。
2. **建立影响清单。** 搜索目录、文件、类、变量、DI token、GraphQL、ORM、SQL、RLS、队列、客户端 operation、生成物、配置、测试和文档。
3. **修改源定义。** 先改拥有语义的 Entity、enum、Module、Service 和协议模型，再更新直接消费者；使用 `git mv` 保留文件历史。
4. **重新生成派生工件。** 从 Entity/装饰器生成 MikroORM migration，从代码生成 GraphQL schema 与客户端类型；不手工伪造 metadata diff 或生成文件。
5. **保护数据与兼容性。** 有存量数据时设计 rename/transform/backfill 和回滚；外部协议不允许改名时保留 wire key 并在边界显式映射。
6. **执行跨层验证。** 运行类型、测试、真实 GraphQL operation、数据库 migration 往返和 RLS 探针，最后逐条分类旧名称残留。

## 专项技能协作

- GraphQL 类型、字段、Input、operation 和 schema 验证使用 `nest-boot-graphql`。
- Entity、表列、约束、索引、数据搬迁与 migration 使用 `nest-boot-mikro-orm`。
- Policy metadata、policy 名、上下文和 PostgreSQL 行为使用 `nest-boot-row-level-security`。
- 文件落点与新模块结构使用 `nest-boot-module-design`。

这些技能共同完成一次改名，但规则只在其所有者中维护；本技能负责顺序、闭环和残留审计。

## 参考文档

- [跨层重命名与迁移工作流](references/renaming-workflow.md) — 语义边界、影响矩阵、数据迁移、生成物和验收清单。
