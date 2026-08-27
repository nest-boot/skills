# 流式架构、实现模式与验证

## 目录

- [1. 先设计端到端数据路径](#1-先设计端到端数据路径)
- [2. 有界写盘与转换](#2-有界写盘与转换)
- [3. Node.js fetch 请求与 Web Response](#3-nodejs-fetch-请求与-web-response)
- [4. 可重试 multipart 与对象存储](#4-可重试-multipart-与对象存储)
- [5. 框架适配](#5-框架适配)
- [6. 子进程输出](#6-子进程输出)
- [7. 回归测试](#7-回归测试)

## 1. 先设计端到端数据路径

开始编码前，为每条数据路径确定以下设计：

| 环节 | 开发决策 |
| --- | --- |
| Source | 谁产生数据？能否暂停、取消或销毁？单个 chunk 是否受控？ |
| Transform | 是否尊重背压？是否把 chunk 收集到数组、字符串、JSON 或对象图？ |
| Sink | 写盘、网络、SDK 或客户端断开时，错误能否反向停止 source？ |
| Retry | 每次是否创建新 source？失败 attempt 是否已销毁或取消？ |
| Limits | header 预检与实际字节计数是否都存在？deadline 是否覆盖读完整个 body？ |
| Concurrency | 单操作缓冲乘以 HTTP、队列和 SDK 并发后是否仍低于进程预算？ |
| Ownership | 谁等待完成、谁取消、谁清理部分文件或临时目录？是否只有一个所有者？ |

实现完成后再沿同一张表验证端到端有界。以下写法只是“参数叫 stream”，不能单独证明安全：

- SDK 方法接收 `Readable`，但内部为了签名、重试或 multipart 上传缓存整个对象；
- 框架代理先 `await request.arrayBuffer()`，再构造一个新的 response stream；
- 上游上传是流式的，但成功响应直接 `response.json()` 且没有响应上限；
- `for await` 读取文件后把所有 chunk 放入数组，最后 `Buffer.concat()`；
- 每个任务只缓冲 20 MiB，但 worker concurrency 为 20。

## 2. 有界写盘与转换

已知 `Content-Length` 可以提前拒绝，但可能缺失或不可信。实际流仍要计数，并用 `pipeline()` 让 sink 错误和背压传播：

```typescript
import { createWriteStream } from 'node:fs';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

async function writeWithinLimit(
  source: NodeJS.ReadableStream,
  destination: string,
  maxBytes: number,
): Promise<void> {
  let received = 0;
  const limiter = new Transform({
    transform(chunk: Buffer, _encoding, callback) {
      received += chunk.byteLength;
      callback(
        received <= maxBytes ? null : new Error('payload too large'),
        received <= maxBytes ? chunk : undefined,
      );
    },
  });

  await pipeline(source, limiter, createWriteStream(destination, { flags: 'wx' }));
}
```

超限时还要确认真实 source 被 abort/destroy，部分文件由明确的生命周期所有者清理。不要在 pipeline 外另开 detached 消费者。

限流器要放在所保护的表示边界。压缩、解压、解码或其他会改变数据大小的 Transform 前后需要独立预算：同时限制压缩输入、展开输出和必要的 expansion ratio，不能用 10 MiB 压缩输入上限推导解压结果也只有 10 MiB。对象模式的 `highWaterMark` 计算对象数而不是字节数；对象大小可变时还要限制单对象和累计字节。

## 3. Node.js fetch 请求与 Web Response

Node.js 原生 `fetch` 使用 `ReadableStream`、`Readable` 或 `AsyncIterable` 作为请求 body 时，需要在 `RequestInit` 中显式设置 `duplex: 'half'`；遗漏时 Node 会在请求发出前抛出 `TypeError`。根据锁定的 Node.js 与类型定义使用 `Readable.toWeb()`、`Readable.fromWeb()` 或运行时直接支持的 body 类型，不要用 `Buffer` 转换来绕开类型错误。请求 deadline、调用方取消和 source 错误应共享同一个 abort 生命周期。

`fetch()` 在收到响应头后即可返回；`response.json()`、`text()` 和 `arrayBuffer()` 会继续读取并整体缓冲 body。先检查 `Content-Length`，再通过 `ReadableStreamDefaultReader` 对实际 chunk 累计字节。越界、解析失败或调用方放弃响应时调用 `reader.cancel()` 或 `response.body?.cancel()`。

读取 deadline 必须覆盖响应 body，而不只是建立连接。可使用传给 `fetch` 的 `AbortSignal.timeout()`，或由调用方持有 `AbortController` 并在完整读取结束后清理定时器。

解析 JSON 至少会同时保留文本和对象图，字符串解码也可能放大字节占用。因此响应字节上限应显著低于进程可用内存，并结合最大并发计算；不要把容器内存本身当作单响应上限。

对非成功响应，如果业务不读取错误 body，应立即取消。只抛异常而留下未消费 body，会延长连接、缓冲和 socket 的占用。

## 4. 可重试 multipart 与对象存储

文件可能需要重试或被多个消费者读取时，应先写入磁盘或其他可重新打开的持久 source。每次 attempt 都执行：

1. 创建新的 boundary 和字段 header；
2. 新建 `createReadStream(path)`；
3. 构造新的 multipart body；
4. 串行等待 request 成功或失败；
5. 销毁失败的 request body，取消未读 response body；
6. 只有清理完成后才进入下一次 attempt。

不要重用 `FormData`、生成器或已读 stream。不要为了可重试而把文件 `readFile()` 成 Buffer。

对象存储 SDK 要检查当前版本的实现和选项：

- 已知文件大小时传 `Content-Length`；
- multipart uploader 的内存通常近似 `partSize × queueSize`，再乘业务并发；
- 明确设置业务可接受的 part/queue 并发，避免默认值与 worker concurrency 叠加；
- 上传失败或请求取消时，把 abort 传播给 SDK 和输入 stream；
- 不要仅凭类型签名或 mock 中保留了同一个 `Readable` 就断言端到端流式。

## 5. 框架适配

Express、Fastify、NestJS 或其他框架只负责暴露 source/sink，不会自动提供端到端内存上限。应检查当前适配器和插件版本：

- request body、multipart parser 和 response 是否直接传递 stream；
- 客户端断开是否会 abort pipeline、上游 fetch 和对象存储操作；
- parser 的 field/file limits 是否只是 header 限制，实际字节是否仍会计数；
- middleware、interceptor 或序列化器是否会在流前后整体缓冲；
- handler 是否等待 pipeline 完成，而不是启动后台消费后提前结束请求上下文。

需要临时文件时，由一次请求或任务拥有目录并等待全部消费者结束后清理。在 Nest Boot 中使用 `@nest-boot/temporary-directory` 时，目录必须在活动 `RequestContext` 中分配，流式工作也必须在上下文结束前完成。

代理应核对当前实现是否直接转发 request/response body，并用慢速大文件集成测试确认；不要用猜测替换已有的流式代理。

## 6. 子进程输出

子进程 pipe 有自己的背压，但应用把每个 `data` chunk 拼接到字符串或数组后仍会无限增长。若 stderr 只用于生成公开错误，优先 `stdio: ['ignore', 'pipe', 'ignore']` 并返回固定、脱敏的错误。需要诊断输出时使用环形/截断缓冲，仅保留固定字节数。

stdout 预期很小时应设置与协议相符的上限；达到上限或 deadline 时 kill 子进程，并防止 `error`、`close`、timeout 多次 settle 同一个 Promise。

## 7. 回归测试

至少覆盖与改动相关的场景：

- `Content-Length` 已知超限，在消费 body 前拒绝并取消；
- 未知长度的 chunked body 在跨块超限时停止 source；
- sink 写入失败会使 source 停止；
- 上游早返回非 2xx，response body 被取消；
- request 或 response 超时后 stream/进程被终止；
- Node.js `fetch` 的流式请求使用 `duplex: 'half'`，取消会停止本地 source；
- 每次重试得到不同且完整的 stream，attempt 不并行；
- 压缩输入未超限但展开输出或 expansion ratio 超限时停止 transform 和 sink；
- 临时文件在成功、异常和客户端断开后最终删除；
- SDK 或代理使用慢速真实流验证，而不是只检查 mock 参数类型；
- 重复和并发处理后 `arrayBuffers`、`external` 与 RSS 保持在预算内，并在请求结束和 GC 后回落。

内存断言应允许运行时抖动，并固定输入大小、迭代次数和并发数。除了最终数值，还要断言实际发出/写入的字节数正确，防止“没有泄漏”其实是流提前截断。
