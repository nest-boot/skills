# `nest-boot-best-practices` 枚举 (Enum) 规范指南

在使用 `@nest-boot` 的应用中声明 TypeScript `enum` 时，应保持定义独立且字面量一致，以便数据库约束、GraphQL schema 和客户端生成类型共享同一语义。

---

## 1. 物理位置与文件命名规范

可复用枚举应有稳定的导入路径，避免 Entity、Resolver 和客户端契约分别维护不同字面量。

- **独立定义**：被 Entity、GraphQL 或多个文件共享的枚举放到独立文件；仅供一个局部实现使用且不会进入持久化或公开契约的类型可沿用宿主项目现有做法。
- **目录**：优先使用对应业务模块的 `enums/` 目录。例如 User 领域可放在 `<module-root>/user/enums/`；`<module-root>` 以宿主应用现有布局为准。
- **文件命名**：使用 kebab-case 和 `.enum.ts` 后缀，例如 `user-status.enum.ts`。

## 2. 内部结构与大小写代码规范

对于进入数据库或 GraphQL 契约的字符串枚举，保持键和值一致的大写形式：

- **键值一致**：使用 `ACTIVE = 'ACTIVE'`，避免同一状态在 TypeScript、数据库和客户端出现多套大小写。
- **兼容既有契约**：已有外部协议或数据库值不是大写时，保留兼容值并明确映射，不要为了格式破坏存量数据或第三方契约。

---

## 3. 示范参考 (对比参照)

### 不推荐：共享枚举与 Entity 混放

不要把代码包裹在一起，更不要随便使用小写或随意匹配字母。

```typescript
// 文件位置混乱：直接写在了 entity 文件里
// user.entity.ts

// 错误：不仅没独立成文件，字面量还配了小写
export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  BANNED = 'banned',
}

@Entity()
export class User {
   // ...
}
```

### 推荐：独立枚举文件

将共享枚举独立并保持稳定命名：

```typescript
// 文件存放位置：<module-root>/user/enums/user-status.enum.ts

export enum UserStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE',
  BANNED = 'BANNED',
}
```

---

## 4. 规范背后的工程价值

- **契约一致性**：当 MikroORM enum/check constraint 与 GraphQL enum 共用同一份定义时，键值一致能减少 `Waiting`、`waiting`、`WAITING` 混用。
- **重构安全**：独立文件让 Entity、Resolver、Input 与客户端生成类型引用同一语义源，也更容易审计旧值残留。
