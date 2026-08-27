---
name: nest-boot-best-practices
description: 使用 `@nest-boot` 构建或重构 NestJS 业务模块时的通用组织与命名规范。适用于新增领域，调整 Entity、Service、Resolver、DTO 或 Enum，重命名实体、表或模块，以及检查服务端、客户端与数据库之间的跨层一致性。
---

## 概述

在使用 `@nest-boot` 的 NestJS 应用中开发业务模块时，应遵守宿主代码库已有的目录布局，并保持文件关注点分离。不要假定固定的 monorepo 包名或源码根目录；先从现有模块、配置和构建脚本识别约定，再在同一边界内扩展。

执行结构调整或新建模块前，按任务涉及的内容阅读下方参考文档。

## 核心概念

- **文件分离 (File Separation)**：让 Entity、Resolver、Service 与可复用类型各自承担单一职责，避免一个文件同时承载多层逻辑。
- **可预测目录 (Predictable Folders)**：沿用宿主模块的 `enums/`、`inputs/`、`types/` 等目录；只有单个局部辅助类型时，不必为了形式额外制造层级。
- **领域命名闭环 (Domain Naming Closure)**：一次领域重命名必须同时覆盖目录、文件、类、依赖注入变量、GraphQL 类型/字段、ORM 关系、数据库表/列、测试和文档；不要只改 Entity 名称。

## 参考文档

- [模块结构规范](references/project-structure.md) - 说明如何从宿主应用识别模块根目录，并在不硬编码仓库布局的前提下组织文件。
- [枚举 (Enum) 安全与格式规范](references/enums.md) - 说明枚举的文件位置、命名与键值约定。
- [纯接口 (Interfaces/Types) 架构规范](references/interfaces.md) - 详解如何安全地存放和区分系统内的纯净底层泛型与数据类型（例如 `export interface XXX`）。
- [领域重命名与迁移检查表](references/renames.md) - 用于实体、模块或表重命名，防止服务端、客户端、迁移、关系字段和文档残留旧语义。
