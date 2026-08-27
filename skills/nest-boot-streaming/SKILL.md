---
name: nest-boot-streaming
description: 在 NestJS 与 `@nest-boot` 应用中设计、实现、重构和测试内存有界的 Node.js Stream 与 Web Streams 数据路径。适用于新增上传、下载、代理、对象存储、multipart、外部 HTTP 请求/响应、媒体处理或子进程集成，以及编写 `Readable`、`pipeline`、`createReadStream`、Multer/Busboy、流式重试、超时、取消、字节上限和 OOM 回归；也用于排查或审查伪流式整体缓冲、背压失效、未消费响应、跨重试复用 stream 和并发放大。
---

## 概览

本技能用于把高容量数据路径开发成可证明内存有界、可取消、可重试且生命周期明确的实现。流式 API 只提供分块传输的可能性，不自动保证安全；设计时要同时处理来源、转换、消费者、失败路径和并发预算。

## 开发流程

1. **先定义数据契约。** 明确最大字节数、是否需要 seek/重试/多次消费、允许的耗时、并发数、最终 sink 和失败后的清理责任。
2. **选择数据路径。** 单次顺序消费可直接 `pipeline()`；需要重试或随机访问时先流式写入上下文拥有的临时文件，再为每次消费创建新 stream。
3. **实现背压和限制。** 同时做 header 预检与实际字节计数，让 source、transform、sink 的 error/abort 双向传播，不在中间收集完整 payload。
4. **实现完整生命周期。** 为整个交换设置 deadline；客户端断开、非 2xx、超限、解析失败或 sink 失败时停止生产者、取消未读响应并等待清理。
5. **实现重试与并发预算。** 每次 attempt 重建 source，重试保持串行；把 high-water mark、SDK 分片队列、解析副本乘以 worker/request 并发，必要时限制并发或拒绝过载。
6. **补真实行为测试。** 覆盖慢速输入、未知 `Content-Length`、跨块超限、早返回、重试和并发；内存测试关注 `arrayBuffers`、`external`、RSS 与请求结束后的回落。

## 核心规则

- **接收与下载：** 大文件用 Multer disk storage 或 `pipeline()` 落盘，header 预检后仍在真实流中累计字节；越界时中止 source 与 sink。
- **转换与消费：** 优先使用 `pipeline()`、异步迭代或可证明保留背压的框架代理；不要用裸 `data` 监听器把 chunk 推入无界数组或队列。
- **临时文件：** 需要 seek、重试或多次消费时，先流式写入上下文拥有的临时文件，每次消费重新 `createReadStream()`；生命周期同时遵循 `nest-boot-temporary-directory`。
- **multipart 与重试：** 每次串行 attempt 重建 body、boundary 和文件流，不能复用已经读取或失败的 stream；可计算时发送准确 `Content-Length`。
- **HTTP 响应：** `Response.json()`、`text()`、`arrayBuffer()` 仍会整体缓冲。先实现按字节有界读取；非成功或不再读取的响应必须取消，完整交换必须有 deadline。
- **对象存储与代理：** 核对具体 SDK/框架实现是否真正流式，显式传递已知长度，配置分片大小与队列并发，并把 abort/error 传播到原始 source。
- **子进程：** 不需要的输出设为 `ignore`；需要的输出限制字节数，并在超时或超限时终止进程。不要无上限拼接 stdout/stderr 字符串。
- **下游处理：** JSON 解析、字符数组、语言检测、日志序列化或响应映射可能再次复制整个结果；开发完成前检查它们不会使前面的流式设计失效。

## 参考文档

- [流式架构、实现模式与验证](references/stream-safety.md) — 有界下载、HTTP 响应、重试、SDK、子进程和内存回归的具体开发方法。
