---
name: nest-boot-temporary-directory
description: 使用 `@nest-boot/temporary-directory` 在 NestJS HTTP、GraphQL、队列或其他 `RequestContext` 工作单元中创建并自动清理临时目录。适用于模块注册、临时文件生命周期、Multer/流式上传、后台任务、命名空间、上下文丢失或清理测试；重点保证目录只在活动上下文中分配、异步消费者不会越过上下文边界、清理所有权保持单一。
---

## 概览

`@nest-boot/temporary-directory` 为每个 `RequestContext` 创建一个位于系统临时目录下的隔离根目录。`TemporaryDirectoryService.create()` 返回该根目录中的随机子目录；上下文成功或失败结束时，模块递归清理整个根目录。

## 核心原则

1. **在应用组合根导入静态全局模块。** `TemporaryDirectoryModule` 没有 `register()` 或 `registerAsync()`；通过 Nest `imports` 注册一次，不要把 Module 当 provider，也不要在业务项目复制一套本地临时目录服务。
2. **只在活动且已初始化的 `RequestContext` 中调用 `create()`。** HTTP/GraphQL 请求可以使用框架建立的上下文；队列、定时任务、CLI 或自定义入口必须确认入口已建立上下文，并让完整临时文件工作留在该上下文的 awaited callback 内。
3. **在可靠的上下文边界解析路径。** Multer、Busboy、事件监听器或第三方流式回调可能晚于拦截器入口执行，也可能看不到原有异步上下文。应先在 Controller/Interceptor/Processor 等已知边界 `await create()`，后续回调只捕获返回的字符串路径；不要在回调里再次读取 `RequestContext`。
4. **不要跨上下文保留临时路径。** 必须等待所有读写、上传、解压或转换完成，并在上下文结束前把需要保留的结果复制到持久存储。不要把路径写入数据库、发送给后续任务或交给 detached promise。
5. **让请求上下文拥有清理责任。** 业务成功、异常和解析失败都由模块在上下文结束时统一清理。业务代码不要对 package-owned 目录重复 `rm`；测试中的假目录由创建该 fixture 的测试负责清理。
6. **每次调用返回独立目录。** 需要按用途分组时传入可选 namespace；它只能是 1–64 个 ASCII 字母、数字、连字符或下划线，不能是路径、空字符串、点段或任意业务输入。

## 实现检查

- 请求专属路径只保存在当前调用的局部变量中，不放到 singleton provider 字段。
- 需要把路径传给回调式 API 时，优先传固定字符串或闭包捕获的字符串。
- `FileInterceptor()` 等依赖 Nest provider 的动态 mixin 必须由 Nest DI 或 `ModuleRef.create()` 实例化，不能直接 `new` 后绕过全局配置。
- 自定义非 HTTP 入口使用 `RequestContext.run(...)` 时，目录创建和所有使用者都位于同一个 awaited callback 内。
- 集成测试使用真实 `TemporaryDirectoryModule` 和真实入口生命周期，覆盖成功、异常后的最终删除；流式上传增加延迟分块请求，验证回调不依赖 `RequestContext`。

## 参考文档

- [安装与模块注册](references/install.md) — 依赖、运行时要求、组合根注册与非 HTTP 上下文。
- [生命周期、流式集成与测试](references/usage.md) — `create()`、namespace、Multer 模式、持久化边界和可观察验证。
