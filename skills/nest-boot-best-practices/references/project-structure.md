# `nest-boot` 模块结构指南

使用 `@nest-boot` 构建或修改 NestJS 模块时，先识别宿主应用的源码根目录、业务模块根目录、数据库目录和公共基础设施目录。不要把某个仓库的包名或路径当成框架要求。

## 1. 识别宿主目录

在新建文件前检查相邻模块、`nest-cli.json`、`tsconfig` 路径映射、ORM 配置和 `package.json` 脚本，以确认：

- 业务模块位于 `src/app`、`src/modules`，还是 monorepo 中某个应用包内；
- migration、Seeder 与生成 schema 的实际输出位置；
- 公共基础设施由根模块、`CommonModule` 或其他组合模块承载；
- 文件命名、导入别名和模块导出方式。

新增模块应进入已有业务模块根目录，不要在 `src/` 下创建一套平行结构。若宿主尚无明确约定，优先选择 `src/modules/<domain>`，并让数据库与基础设施目录保持独立。

## 2. 将泛型枚举提取至独立文件

被 Entity、Resolver、Input 或客户端契约共享的 TypeScript `enum` 应提取到模块的 `enums/` 目录，以提供稳定导入路径并避免重复字面量。仅用于单个局部实现、不会进入持久化或公开契约的类型可沿用宿主项目约定。

### 坏代码示范 (反直觉模式)

```typescript
// source-chunk.entity.ts （堆砌）
export enum SourceChunkStatus {
  WAITING = 'WAITING',
  COMPLETED = 'COMPLETED',
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
  WAITING = 'WAITING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
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

以下仅展示一种可适配的布局。实际路径以宿主应用为准，关键是不混合业务模块、数据库工件与公共基础设施：

```text
<application-root>/src
├── modules
│   ├── user
│   │   ├── user.entity.ts
│   │   ├── user.module.ts
│   │   ├── user.resolver.ts
│   │   └── user.service.ts
│   ├── team
│   │   ├── enums/
│   │   ├── inputs/
│   │   ├── team.connection-definition.ts
│   │   ├── team.entity.ts
│   │   ├── team.module.ts
│   │   ├── team.resolver.ts
│   │   └── team.service.ts
│   └── team-member
│       ├── enums/
│       ├── inputs/
│       ├── types/
│       ├── team-member.connection-definition.ts
│       ├── team-member.entity.ts
│       ├── team-member.module.ts
│       ├── team-member.resolver.ts
│       └── team-member.service.ts
├── common
│   └── ... (共享基础设施)
└── database
    ├── migrations
    │   └── ... (各类基于前缀日期生成的数据库迁移文件)
    └── seeders
        └── ... (MikroORM Seeder)
```

保持这种职责边界有助于减少循环依赖，并让其他模块按最小粒度导入枚举、接口或服务。
