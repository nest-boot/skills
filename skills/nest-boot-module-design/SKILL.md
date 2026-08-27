---
name: nest-boot-module-design
description: 使用 NestJS 与 `@nest-boot` 新增、拆分或重构业务模块时的目录、边界、文件和类型组织规范。适用于创建新领域，安排 Entity、Service、Resolver、Controller、DTO/Input、interface/type 或 enum，拆分职责混杂的大文件，判断公共基础设施与业务代码的位置，以及沿用宿主项目的模块根目录和命名约定；领域整体改名应使用 `nest-boot-domain-renaming`。
---

## 概览

先从宿主代码库识别真实模块根目录和现有边界，再扩展同一套结构。Nest Boot 不要求固定 monorepo 包名或源码路径；目录设计应服务于职责、运行时元数据和稳定导入，而不是机械套模板。

## 开发流程

1. **发现宿主约定。** 检查相邻模块、`nest-cli.json`、`tsconfig` 路径映射、ORM/GraphQL 配置和构建脚本，确认业务模块、数据库工件与公共基础设施的位置。
2. **划定领域边界。** 明确模块拥有的实体、入口、业务服务、持久化和公开契约；跨领域协调放在有明确所有权的 service，不建立平行目录体系。
3. **按运行时职责拆分。** Entity、Service、Resolver/Controller、Module 与需要装饰器元数据的 Input/Args/DTO 使用独立 class 文件；局部短小辅助类型可就近保留。
4. **提取稳定共享定义。** 跨文件复用的 interface/type 和 enum 使用稳定路径；只在单点使用的简单定义不要为了形式制造空文件夹。
5. **检查模块表面。** imports/providers/controllers/exports 只暴露实际消费者需要的内容，避免循环依赖、重复 provider 和无语义 re-export。
6. **验证结构与契约。** 运行类型检查、相关单元测试和真实框架生成/启动验证；若涉及 GraphQL、MikroORM 或 RLS，继续使用对应专项技能。

## 核心边界

- 模块根目录来自宿主项目证据，不硬编码 `src/app`、`src/modules` 或某个 workspace 包名。
- `interface`/`type` 只存在于编译期；需要 GraphQL、class-validator、class-transformer 或 Swagger 元数据时使用 class。
- 共享 enum 只保留一份源定义。GraphQL 注册交给 `nest-boot-graphql`，数据库映射与迁移交给 `nest-boot-mikro-orm`。
- 文件分离不等于每个符号一个文件。按复用范围、运行时职责和宿主惯例决定是否提取。
- 本技能不负责跨层整体改名；实体、表、GraphQL、客户端与迁移同步改名使用 `nest-boot-domain-renaming`。

## 参考文档

- [模块边界与目录结构](references/project-structure.md) — 发现宿主布局、安排模块文件和控制公开表面。
- [Type、Interface、DTO 与 Enum](references/types-and-enums.md) — 编译期类型、运行时模型和共享有限集的提取规则。
