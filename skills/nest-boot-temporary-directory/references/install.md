# 安装与模块注册

## 依赖与运行时

安装 package 及其 request-context peer dependency：

```bash
pnpm add @nest-boot/temporary-directory @nest-boot/request-context
```

选择版本时先检查 package 的 `engines` 和 `peerDependencies`。`@nest-boot/temporary-directory` 7.x 要求 Node.js `>=24.4.0`、NestJS 11 和兼容的 `@nest-boot/request-context` 7.x；workspace 中应解析到兼容的 request-context 实例，避免上下文状态来自不同 package 副本。

## 注册模块

`TemporaryDirectoryModule` 是静态全局模块，并自行导入 `RequestContextModule`。在宿主应用的组合根或公共基础设施模块中通过 `imports` 注册一次：

```typescript
import { TemporaryDirectoryModule } from '@nest-boot/temporary-directory';
import { Global, Module } from '@nestjs/common';

@Global()
@Module({
  imports: [TemporaryDirectoryModule],
})
export class FilesystemInfrastructureModule {}
```

不要调用不存在的 `register()`/`registerAsync()`，也不要把 `TemporaryDirectoryModule` 放入 `providers`。模块不接受自定义 base path：request root 位于 `node:os.tmpdir()` 下，而不是仓库内的 `temp` 目录。

## 非 HTTP 入口

HTTP 和 GraphQL 入口由 request-context 集成建立上下文。对于没有框架集成的 scheduled job、CLI 或自定义 worker，在 Nest 完成模块初始化后显式包住完整工作：

```typescript
import { RequestContext } from '@nest-boot/request-context';

await RequestContext.run(new RequestContext({ type: 'job' }), async () => {
  const directory = await temporaryDirectoryService.create('import');
  await downloadSource(directory);
  await processSource(directory);
  await persistResult(directory);
});
```

不要只在 `RequestContext.run()` 中创建目录后把路径返回给外部使用；callback 结束时目录会被清理。使用 `@nest-boot/bullmq` 等已提供 RequestContext 的入口时复用其生命周期，不要嵌套一个只为绕过报错的短生命周期上下文。
