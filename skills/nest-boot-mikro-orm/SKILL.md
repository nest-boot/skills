---
name: nest-boot-mikro-orm
description: Best practices for using `@nest-boot/mikro-orm` EntityService to simplify NestJS database access. Learn how to leverage built-in methods (create, findOne, update, remove, etc.) to eliminate boilerplate code and CRUD wrapper functions in Service classes. Use this skill whenever building or refactoring NestJS services interacting with a database via MikroORM or when creating new features that require persistent storage.
---

## 概览

在基于 MikroORM 进行数据交换的 NestJS 模块化场景下，该项目内部的默认及标准化策略要求一律采用 `@nest-boot/mikro-orm`。通过去继承 `EntityService` ，能够极其有效地为应用缩减样板级别代码规模。

**请永远在每次打算手工于 Service 层写死任何的读取/写入增删改查方法之前，首去验证 `EntityService` 父类原生底座是否已包含了满足该诉求的内置方法。**

## 核心设计概念

- **继承 `EntityService`**: 大部分负责功能域的 Service 对象均应当通过继承 `EntityService<T>` 获得一套完整的企业标准数据交互套件。
- **杜绝二次包装内置的方法**: 如果类似于原生 `create()` 或是 `findAll()` 本就已经足够契合你的查询处理初衷，请放任上层的控制器 (Controller/Resolver) 跨过藩篱直接调用它！千万不要自己又跑回 `Service` 重画一个毫无作为的方法仅仅当作代理包裹（Proxy Wrapper）。

## 参考文档

- [MikroOrm 模块安装与配置指南](references/install.md) - 详解工程初始化或者接入时如何安装 `@nest-boot/mikro-orm` 及其事务护卫队，并在全局公共模块实现最清爽的零配置注册。
- [EntityService 运用与最佳实践标准](references/entity-service.md) - 这是这份规范极其细致的代码层剖析，直观明了指出了应当抛弃的废代码模型以及详尽的强悍方法矩阵图（如 `create`, `findOneOrFail`, 以及流式处理块的 `chunkById` 详解）。
- [Entity 实体字段抽象守则](references/entity.md) - 详解在 MikroORM 的层级下如何处理具备有限集业务意图字段（比如 `status`, `type`），强硬约束并切断松散字符串映射。
- [MikroORM 迁移 (Migration) 命令指南](references/migration.md) - 详解基于 `pnpm mikro-orm migration:*` 构建的体系里该如何规范使用差异比对、创建迁移记录和正确安全的执行 `up/down` 回滚。
- [MikroORM 向量数据 (pgvector) 操作规范](references/vector.md) - 详解针对 AI 的大模型存储场景，应当如何安全声明指定维度宽带的向量属性，并利用底层方言定制创建带有运算符指向的 HNSW 索引。
- [关联处理最佳实践：多对多与关系表管理](references/service-many-to-many.md) - 使用 `IdOrEntity`、`em.upsert` 和 `em.nativeDelete` 实现高性能、强容错的声明式多对多关联维护手段。
