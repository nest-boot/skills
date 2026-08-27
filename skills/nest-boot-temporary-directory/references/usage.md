# 生命周期、流式集成与测试

## 创建与使用目录

通过依赖注入使用 `TemporaryDirectoryService`。返回值是已创建的目录路径，调用方在其中创建文件：

```typescript
import { TemporaryDirectoryService } from '@nest-boot/temporary-directory';
import { Injectable } from '@nestjs/common';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

@Injectable()
export class ReportService {
  constructor(
    private readonly temporaryDirectory: TemporaryDirectoryService,
  ) {}

  async render(): Promise<Buffer> {
    const directory = await this.temporaryDirectory.create('report');
    const output = join(directory, 'result.pdf');

    await writeFile(output, await this.renderPdf());
    return await this.readResult(output);
  }
}
```

每次 `create()` 都返回独立的随机子目录。同一 namespace 只共享父目录，不共享工作目录。namespace 是代码控制的用途标签，不应直接使用文件名、tenant 名、URL path 或其他未经约束的输入。

`create()` 会拒绝以下情况：

- 没有活动 `RequestContext`；
- 模块 middleware 未初始化当前上下文；
- namespace 不是 1–64 个 ASCII 字母、数字、`-` 或 `_`；
- 底层文件系统操作失败。

不要吞掉上下文错误并回退到仓库内的固定目录。这会绕过隔离与自动清理，通常也会掩盖入口生命周期配置错误。

## Multer 与延迟回调

不要在 Multer `destination` callback 中调用 `create()`。请求体可能在拦截器入口之后分块到达，Busboy/Multer 的流事件回调不应承担读取 `RequestContext` 的责任。

在拦截器入口先解析当前请求的目录，并构造只捕获该路径的 per-request delegate：

```typescript
@Injectable()
export class UploadInterceptor implements NestInterceptor {
  constructor(
    private readonly temporaryDirectory: TemporaryDirectoryService,
  ) {}

  async intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Promise<Observable<unknown>> {
    const directory = await this.temporaryDirectory.create('upload');
    const Delegate = FileInterceptor('file', {
      storage: diskStorage({ destination: directory }),
    });

    return await new Delegate().intercept(context, next);
  }
}
```

不要把 `directory` 或构造后的 request-specific delegate 写入 singleton interceptor 字段，否则并发请求可能共享错误路径。若第三方 API 必须接收 callback，callback 只使用局部变量中已经解析好的字符串。

## 生命周期与持久化

目录在上下文 resolve 或 reject 后递归删除。所有消费者必须在上下文内部完成：

```typescript
const directory = await temporaryDirectoryService.create('archive');
await extractArchive(source, directory);
const artifact = await buildArtifact(directory);
await objectStorage.put(artifact);
```

以下模式会在目录清理后继续访问路径：

```typescript
const directory = await temporaryDirectoryService.create('archive');
void queueDetachedWork(directory);
return { directory };
```

需要跨请求或跨任务使用的文件应在上下文结束前复制到对象存储、持久卷或其他明确的持久层，并传递持久化标识而不是临时路径。

## 测试策略

### 集成测试

使用真实 `TemporaryDirectoryModule` 和真实 HTTP/GraphQL/队列入口，至少验证：

1. 上下文内创建的目录和文件可访问；
2. 成功响应后最终收到 `ENOENT`；
3. handler 抛错后仍最终收到 `ENOENT`；
4. 并发上下文获得不同 root；
5. 对上传场景，用延迟分块 multipart 请求验证 destination 不在流 callback 中读取上下文。

清理可能在响应完成后的事件循环阶段发生，使用有界重试检查最终删除，不要用固定长时间 sleep。

### 单元测试

普通业务 Service 单测可以 mock `TemporaryDirectoryService.create()`，返回由测试创建的目录。此时 package middleware 不拥有该 fixture，测试必须在 `afterEach` 中清理它。不要把这种测试清理复制到生产业务代码。
