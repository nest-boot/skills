---
name: nest-boot-mikro-orm
description: 使用 `@nest-boot/mikro-orm` 构建 NestJS 持久化层的通用规范，覆盖 Entity、EntityService、关系、迁移、Seeder、外部供应商中立建模、锁与数据库验证。适用于新增或重构持久化功能，修改表、列、枚举、外键或索引，重命名实体，生成或审查迁移，以及排查 schema drift。
---

## 概览

在已经采用 `@nest-boot/mikro-orm` 的 NestJS 应用中，优先复用其 `EntityService`、配置加载与迁移集成，减少重复的数据访问样板。目录、包过滤器、脚本名和数据库部署入口应从宿主代码库识别，不要硬编码某个 monorepo 的约定。

新增 Service 数据访问方法前，先检查 `EntityService` 是否已提供相同语义；只有业务规则、跨实体协调或特殊查询确实增加价值时才封装自定义方法。

## 核心设计概念

- **复用 `EntityService`**：以单一实体为中心的 Service 可继承 `EntityService<T>`，获得类型化的创建、查询、更新、删除与分块处理能力。
- **避免无语义包装**：如果继承的 `create()`、`findAll()` 等已经表达调用意图，直接通过该 Service 使用它；自定义方法应体现权限、事务、领域校验或跨实体操作等新增语义。

## 参考文档

- [MikroORM 模块安装与配置指南](references/install.md) - 说明 `@nest-boot/mikro-orm`、可选请求事务模块与 CLI 配置。
- [EntityService 使用与扩展边界](references/entity-service.md) - 说明内置方法、无语义包装和 `IdOrEntity` 的适用范围。
- [Entity 字段建模](references/entity.md) - 说明有限集字段、标识符与索引的建模取舍。
- [MikroORM 迁移 (Migration) 命令指南](references/migration.md) - 详解基于 `pnpm mikro-orm migration:*` 构建的体系里该如何规范使用差异比对、创建迁移记录和正确安全的执行 `up/down` 回滚。
- [MikroORM 向量数据 (pgvector) 操作规范](references/vector.md) - 说明向量维度、距离操作符、扩展迁移与 HNSW 索引取舍。
- [关联处理最佳实践：多对多与关系表管理](references/service-many-to-many.md) - 使用 `IdOrEntity`、`em.upsert` 和 `em.nativeDelete` 维护显式关系实体。
- [MikroORM Seeder 规范](references/seeder.md) - 使用幂等 Seeder 管理部署数据、有效期和稳定业务标识，并纳入宿主应用的数据库部署流程验证。
- [多供应商持久化建模](references/provider-neutral-schema.md) - 区分供应商目录 ID 与实例 ID，避免把单一供应商或当前 UI 分层写死进通用表结构。
