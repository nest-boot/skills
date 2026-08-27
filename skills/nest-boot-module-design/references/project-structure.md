# 模块边界与目录结构

## 1. 发现真实模块根目录

创建文件前检查：

- 相邻领域模块的目录、文件后缀和导入方式；
- `nest-cli.json`、`tsconfig` paths 和 workspace 配置；
- ORM migration/Seeder 与 GraphQL schema 的输出位置；
- 公共基础设施由根模块、Global Module 还是普通 feature module 装载；
- 测试、代码生成和构建脚本接受的路径。

已有业务模块位于 `src/app` 时继续使用它；位于 `src/modules` 或 monorepo app 内时也同理。不要在 `src/` 下另建一套平行结构。宿主没有约定时才选择清晰的默认值，例如 `src/modules/<domain>`。

## 2. 从领域职责设计文件

一个常见但非强制的模块可以包含：

```text
<module-root>/<domain>/
├── <domain>.module.ts
├── <domain>.entity.ts
├── <domain>.service.ts
├── <domain>.resolver.ts 或 <domain>.controller.ts
├── inputs/
├── enums/
├── interfaces/ 或 types/
└── *.spec.ts
```

只有实际存在对应职责时才创建目录和文件：

- `Entity` 表达持久化模型，不承载 Resolver 或 Controller 逻辑；
- `Service` 承载业务规则或有意义的数据访问语义，不包装一遍已有 API；
- `Resolver`/`Controller` 处理协议入口、参数和响应映射，把业务工作委托给 Service；
- `Module` 只负责组合 imports、providers、controllers 与 exports；
- Input/Args/DTO 是带运行时元数据的边界模型，不用纯 interface 替代；
- 多处复用或复杂的编译期定义再进入 `interfaces/`、`types/` 或 `enums/`。

仅供一个短函数使用的 type、只被一个类引用的简单常量或单个私有 helper 可以就近保留。不要为了目录整齐制造大量只有一行的文件。

## 3. 控制模块公开表面

- providers 默认留在模块内部；只有其他模块确实需要注入时才 export；
- 复用稳定定义时直接从其文件导入，不用层层 barrel 隐藏依赖方向；
- 共享基础设施进入已有公共模块，不复制到每个业务领域；
- 双向领域依赖通常说明边界或协调 service 需要调整，不先用 `forwardRef()` 掩盖；
- 动态模块、全局模块和框架 package 的注册方式由对应 package 文档或专项 skill 决定。

## 4. 验证

1. 运行 TypeScript 类型检查和相关测试；
2. 启动或编译 Nest 应用，捕获 provider/module 装配错误；
3. 涉及 GraphQL 时生成 schema 并执行真实 operation；
4. 涉及 MikroORM 时检查 metadata 和 migration diff；
5. 用 `rg` 检查旧导入、重复定义和意外平行目录；
6. 审查 `git diff`，确认没有只为形式移动无关文件。
