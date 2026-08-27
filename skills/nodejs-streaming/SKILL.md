---
name: nodejs-streaming
description: 在 Node.js 服务、CLI 与 worker 中设计、实现、重构和测试内存有界的 Node.js Stream 与 Web Streams 数据路径。适用于上传、下载、代理、对象存储、multipart、fetch 请求/响应、媒体处理、压缩解压或子进程集成，以及编写 `Readable`、`Writable`、`Transform`、`pipeline`、`createReadStream`、背压、重试、超时、取消、字节上限、并发预算和 OOM 回归；覆盖 Express、Fastify、NestJS 等框架，也用于排查伪流式整体缓冲、未消费响应、跨重试复用 stream 和并发放大。
---

## 概览

本技能用于把高容量 Node.js 数据路径开发成可证明内存有界、可取消、可重试且生命周期明确的实现。流式 API 只提供分块传输的可能性，不自动保证安全；设计时要同时处理来源、转换、消费者、失败路径和并发预算。

## 开发流程

1. **先定义数据契约。** 明确最大字节数、是否需要 seek/重试/多次消费、允许的耗时、并发数、最终 sink 和失败后的清理责任。
2. **选择数据路径。** 单次顺序消费可直接 `pipeline()`；需要重试或随机访问时先流式写入临时文件或其他可重新打开的 source，再为每次消费创建新 stream。
3. **实现背压和限制。** 同时做 header 预检与实际字节计数，让 source、transform、sink 的 error/abort 双向传播，不在中间收集完整 payload。
4. **实现完整生命周期。** 为整个交换设置 deadline；客户端断开、非 2xx、超限、解析失败或 sink 失败时停止生产者、取消未读响应并等待清理。
5. **实现重试与并发预算。** 每次 attempt 重建 source，重试保持串行；把 high-water mark、SDK 分片队列、解析副本乘以 worker/request 并发，必要时限制并发或拒绝过载。
6. **补真实行为测试。** 覆盖慢速输入、未知 `Content-Length`、跨块超限、早返回、重试和并发；内存测试关注 `arrayBuffers`、`external`、RSS 与请求结束后的回落。

## 核心规则

- **接收与下载：** 大 payload 直接从请求或远端 body `pipeline()` 到目标 sink；header 预检后仍在真实流中累计字节，越界时中止 source 与 sink。
- **转换与消费：** 优先使用 `pipeline()`、异步迭代或可证明保留背压的框架代理；不要用裸 `data` 监听器把 chunk 推入无界数组或队列。
- **临时文件：** 需要 seek、重试或多次消费时，先流式写入由当前操作拥有的临时文件，每次消费重新 `createReadStream()`；所有成功、失败和取消路径都由同一个生命周期所有者清理。
- **multipart 与重试：** 每次串行 attempt 重建 body、boundary 和文件流，不能复用已经读取或失败的 stream；可计算时发送准确 `Content-Length`。
- **Node.js fetch 请求：** 原生 `fetch` 发送流式 body 时显式设置 `duplex: 'half'`，并按运行时要求使用或转换 Node/Web stream；把同一个 abort signal 传给请求和本地 source。
- **HTTP 响应：** `Response.json()`、`text()`、`arrayBuffer()` 仍会整体缓冲。先实现按字节有界读取；非成功或不再读取的响应必须取消，完整交换必须有 deadline。
- **压缩与解压：** 分别限制压缩输入和展开输出，必要时限制 expansion ratio；输入字节有界不代表解压后的磁盘、内存或下游对象有界。
- **对象存储与代理：** 核对具体 SDK/框架实现是否真正流式，显式传递已知长度，配置分片大小与队列并发，并把 abort/error 传播到原始 source。
- **子进程：** 不需要的输出设为 `ignore`；需要的输出限制字节数，并在超时或超限时终止进程。不要无上限拼接 stdout/stderr 字符串。
- **下游处理：** JSON 解析、字符数组、解压、日志序列化或响应映射可能再次复制或放大整个结果；开发完成前检查它们不会使前面的流式设计失效。

## 框架集成

- **Express、Fastify 与 NestJS：** 确认请求/响应适配器直接传递 stream 并保留背压；不要先调用 `arrayBuffer()`、`formData()` 或把完整 body 收集进内存。客户端断开时应把 abort 传播到 pipeline、远端请求和子进程。
- **NestJS 上传：** 大文件通常使用 Multer disk storage 或自定义流式解析器。若动态 interceptor 依赖请求级配置，按 NestJS 依赖注入生命周期创建，不要脱离容器直接实例化。
- **Nest Boot 临时目录：** 使用 `@nest-boot/temporary-directory` 时遵循 `nest-boot-temporary-directory`，在可靠的 `RequestContext` 边界分配目录，并在上下文结束前等待所有流式消费者完成。
- **框架与 SDK 版本：** 代理、multipart parser、fetch 实现和对象存储 SDK 的缓冲策略可能变化；根据项目锁定版本核对实现，并用慢速大流集成测试验证。

## 参考文档

- [流式架构、实现模式与验证](references/stream-safety.md) — 有界写盘、HTTP 响应、重试、SDK、框架适配、子进程和内存回归的具体开发方法。
