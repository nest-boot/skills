# nest-boot/skills

Nest Boot 相关 AI Agent Skills 仓库，用于沉淀 `@nest-boot` 生态下的工程规范、框架集成和最佳实践。

## 使用

建议在项目根目录中以项目级别安装本仓库中的所有 skills，并同时安装到 Claude Code 与通用 `.agents/skills/` 目录：

```sh
npx skills add https://github.com/nest-boot/skills \
  --all \
  --agent claude-code \
  --agent universal \
  --copy \
  -y
```

如只需安装单个 skill，可以使用 `--skill <skill-name>` 指定名称：

```sh
npx skills add https://github.com/nest-boot/skills \
  --skill nest-boot-best-practices \
  --agent claude-code \
  --agent universal \
  --copy \
  -y
```

## Skills 列表

| Skill                                                        | 描述                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| [nest-boot-best-practices](skills/nest-boot-best-practices/) | 使用 `@nest-boot` 框架构建 NestJS 应用时的代码组织与架构规范 |
| [nest-boot-bullmq](skills/nest-boot-bullmq/)                 | 使用 `@nest-boot/bullmq` 实现类型安全的异步任务队列          |
| [nest-boot-graphql](skills/nest-boot-graphql/)               | 使用 `@nest-boot/graphql` 构建 GraphQL API                   |
| [nest-boot-logger](skills/nest-boot-logger/)                 | 使用 `@nest-boot/logger` 实现结构化日志                      |
| [nest-boot-mikro-orm](skills/nest-boot-mikro-orm/)           | 使用 `@nest-boot/mikro-orm` 进行数据库操作的最佳实践         |

## 维护

维护本仓库的 skill 前，请先安装并使用 `skill-creator`：

```sh
npx skills add https://github.com/anthropics/skills \
  --skill skill-creator \
  --agent claude-code \
  --agent universal \
  --copy \
  -y
```
