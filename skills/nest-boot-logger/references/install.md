# 安装与配置指南

## 1. 安装依赖

```bash
pnpm add @nest-boot/logger
```

## 2. 全局注册 LoggerModule

在项目的全局公共模块 `CommonModule` 中导入 `LoggerModule`，这样所有业务模块自动获得日志注入的能力，无需在各自的 `Module` 文件里再次引入：

```typescript
import { LoggerModule } from '@nest-boot/logger';
import { Global, Module } from '@nestjs/common';

@Global()
@Module({
  imports: [
    LoggerModule,
    // ... 其他全局模块
  ],
})
export class CommonModule {}
```

## 3. 替换 NestJS 默认日志器 (main.ts)

为了让 NestJS 框架层面的启动日志、未捕获异常日志等同样走 pino 结构化输出，需要在应用引导期间将 `Logger` 实例设置为全局日志器：

```typescript
import { Logger } from '@nest-boot/logger';
import { NestFactory } from '@nestjs/core';

import { AppModule } from '@/app/app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true, // 缓冲启动期间的日志，等 Logger 就绪后统一输出
  });

  // 用 @nest-boot/logger 的 Logger 替换 NestJS 默认日志系统
  app.useLogger(await app.resolve(Logger));

  await app.listen(process.env.PORT ?? 4000);
}

void bootstrap();
```

关键点：
- **`bufferLogs: true`** 确保在 Logger 完成初始化之前产生的日志不会丢失。
- **`app.resolve(Logger)`** 使用 `resolve` 而非 `get`，因为 Logger 是请求作用域（transient）的。
