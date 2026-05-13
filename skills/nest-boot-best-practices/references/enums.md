# `nest-boot-best-practices` 枚举 (Enum) 规范指南

在本项目体系内声明并使用 TypeScript `enum` 时，必须要遵守极高标准的隔离与字面量约束，以保障系统全局的一致性，增强与数据库（特别是约束类查询）及前端交互映射时的安全性。

---

## 1. 物理位置与文件命名规范

首先，从架构防腐的角度出发，系统内使用的枚举类型绝不能混合在主要的逻辑实体中。

- **绝对禁止内联 (No Inline)**: 不要贪图方便在 `*.entity.ts` 或 `*.resolver.ts` 的顶部直接声明 `export enum ...`。这种做法会带来各种循环引用隐患与模块冗余。
- **专属二级目录**: 全部重构出的枚举只准存放于对应业务模块下的特制目录 `enums/` 内。比如，服务于 User 资料集的枚举只能放在 `./src/app/user/enums/` 目录下。
- **文件后缀与命名体系**:
  - 文件主名采用**脊柱命名法 (kebab-case)** 进行定名（如 `user-status`）。
  - 文件不得只用普通的 `.ts`。必须统一加上特征提取的**专有复合后缀名**: `.enum.ts`。

## 2. 内部结构与大小写代码规范

独立出来的 `.enum.ts` 其代码内部，对所有枚举键值存在强要求：

- **强一致性大写**: 所有暴露出来的枚举常量（枚举体内部的每一行），必须保障其**键名 (Key)** 与最终对应的 **字符字面量值 (Value)** 处于绝对相同，并且只能是**全大写字母 (UPPERCASE)**。

---

## 3. 示范参考 (对比参照)

### ❌ 坏代码示范（请勿踩坑）

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

### ✅ 优秀规范示范

必须单独剥离并严格规范命名法：

```typescript
// 文件存放位置：src/app/user/enums/user-status.enum.ts

export enum UserStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE',
  BANNED = 'BANNED', // 键与值百分百挂钩全大写
}
```

---

## 4. 规范背后的工程价值

- **数据库与 Graph API 安全网**: MikroORM 自动生成的实体校验以及 PostgreSQL 底层的 `check constraint`，都会对于字符串大小写进行严密绑定。强制大写作为统一定义底座能够根绝因书写粗心如 `Waiting` vs `waiting` 产生的一系列毫无意义的系统级校验报错。
- **降低前端接入的心智负担 (类型穿透)**: 全大写常量属于业界的标准通行定义。一旦统一贯彻后，无论前端是面向哪一个后端资源进行条件对比和获取封装的入参对象时，都无需再去考虑该变量是驼峰还是脊柱法带来的拼写麻烦。
