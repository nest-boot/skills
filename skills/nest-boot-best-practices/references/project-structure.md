# `nest-boot` 项目结构架构指南

当跨 `@nest-boot` 基础 NestJS 构建或修改代码体系时，务必遵从下方声明的组织模式架构：

## 1. 核心目录限制 (仅限于 `./src/app`)

所有的 NestJS 系统功能模块（如 Controller、Service、Resolver、Entity）**必须**存放在 `./src/app/` 目录下。绝对禁止将新的业务模块直接放置在 `./src/` 的根级或者单独建立平行于 `app` 的子目录。

## 2. 将泛型枚举提取至独立文件

**绝对禁止**在 Entity 实体、Resolver 或是 Service 类型内，直接以行内（inline）形式进行原生 TypeScript `enum` 的声明与构建。
一切 Enum 都必须被单独切分、提取至包含该模块内容的 `enums/` 专属目录下的独立文件当中。

### 坏代码示范 (反直觉模式)

```typescript
// source-chunk.entity.ts （堆砌）
export enum SourceChunkStatus {
  WAITING = 'waiting',
  COMPLETED = 'completed',
}

@Entity()
export class SourceChunk {
  // ...
}
```

### 优秀代码示范 (规范的提取方式)

1. 首先创建一个相互隔离的枚举文件：

```typescript
// enums/source-chunk-status.enum.ts
export enum SourceChunkStatus {
  WAITING = 'waiting',
  COMPLETED = 'completed',
  FAILED = 'failed',
}
```

2. 然后再将其导入至需要它的 Entity 或 DTO 模型中运作：

```typescript
// source-chunk.entity.ts
import { SourceChunkStatus } from './enums/source-chunk-status.enum';

@Entity()
export class SourceChunk {
  @Enum({
    items: () => SourceChunkStatus,
    default: SourceChunkStatus.WAITING,
  })
  status: Opt<SourceChunkStatus> = SourceChunkStatus.WAITING;
}
```

## 3. 目录布局拓扑树全景标准

为了给后续所有代码生成的依赖和拆分提供精确参照，以下是我们整个应用（`./src/app`）最新的整体物理拓扑图谱，请严格照此结构来定位、新建或是管理对应模块层级：

```text
./src
├── app
│   ├── app.module.ts
│   ├── ... (其他业务模块)
│   ├── user
│   │   ├── user.entity.ts
│   │   ├── user.module.ts
│   │   ├── user.resolver.ts
│   │   └── user.service.ts
│   ├── workspace
│   │   ├── enums/
│   │   ├── inputs/
│   │   ├── workspace.connection-definition.ts
│   │   ├── workspace.entity.ts
│   │   ├── workspace.module.ts
│   │   ├── workspace.resolver.ts
│   │   └── workspace.service.ts
│   └── workspace-member
│       ├── enums/
│       ├── inputs/
│       ├── types/
│       ├── workspace-member-permission.enum.ts
│       ├── workspace-member.connection-definition.ts
│       ├── workspace-member.entity.ts
│       ├── workspace-member.module.ts
│       ├── workspace-member.resolver.ts
│       └── workspace-member.service.ts
└── database
    └── migrations
        └── ... (各类基于前缀日期生成的数据库迁移文件)
```

只要能够恒定遵循这种模式规范，我们就能从根源上缓解环形依赖产生的代码连锁困境，外部任意其他模块也能得以以最安全的颗粒度专门摄取其中纯净的枚举对象或者 Interface 而绝不可能导致引擎污染。
