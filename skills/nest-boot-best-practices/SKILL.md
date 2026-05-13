---
name: nest-boot-best-practices
description: 在当前项目中使用 `@nest-boot` 框架构建 NestJS 应用时的常规代码组织与架构规范。当您生成、修改、重构 Entity（实体）、Resolver 或者是 DTO 时，请触发并使用本技能以确保代码拆分、目录层级以及针对类型（如 Enum 枚举）的提取等行为，皆充分符合当前工程的标准规范。
---

## 概述

在当前项目内的任何 NestJS 模块下开发功能时，必须严格遵守目录布局准则与文件关注点分离原则，以确保代码库能够在长期维护中具备良好的扩展性。

**在执行任何结构调整或新建任务前，请务必阅读并对照下方参考文档，以确保所做修改符合项目规范。**

## 核心概念

- **文件分离 (File Separation)**：禁止将多重职能或内嵌类型（比如枚举 Enums）全部糅杂堆积在单一的 Entity 或 Resolver 文件内。
- **独占目录 (Dedicated Folders)**：需将特定的辅助类型、输入对象（inputs）和枚举定义，归类放置于具备极强预测性的独立二级目录中 (例如：`enums/`，`inputs/`)。

## 参考文档

- [项目结构规范](references/project-structure.md) - 该指南提供了针对模块化组织的详尽结构图，并明确规定 Typescript 文件的位置限制原则。
- [枚举 (Enum) 安全与格式规范](references/enums.md) - 详解在系统中创建独立 Enum 时，为何及如何严格贯彻键值全大写的铁律。
- [纯接口 (Interfaces/Types) 架构规范](references/interfaces.md) - 详解如何安全地存放和区分系统内的纯净底层泛型与数据类型（例如 `export interface XXX`）。
