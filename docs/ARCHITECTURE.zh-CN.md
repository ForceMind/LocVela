# 架构与接口约定

## 已实现与预留边界

`crates/locvela-core` 是无依赖几何/轨迹/抽象会话库。`tools/report.py` 校验报告结构和证据一致性，不鉴定证据真实性。

Android Alpha 已实现：`apps/android/controller`（Kotlin/Compose 控制端）、`apps/android/model`（纯 JVM 定位源事务）、`probes/android`（独立只读 APK）。独立包名、进程、权限和存储；探针没有 model/controller 依赖，不通过控制端缓存取得结果。

iOS SwiftUI、Tauri 桌面、pymobiledevice3 适配器及 iOS Probe 尚未实现。Android 首版不连接 Rust FFI，也未实现 Google Play services FLP 或地图/路线界面。固定点后端先验证原生平台生命周期，不复制 Rust 轨迹算法。

## Android 定位事务

只有可见界面明确启动才创建 location 前台服务。服务单线程串行操作，自带通知停止；START_NOT_STICKY，无开机启动，无自动续跑。每秒约一次下发，带正的墙钟与严格递增 elapsedRealtimeNanos，保留系统模拟标记。精度字段是模拟参数，不是现实准确性证明。

定位源仅允许 gps/network/fused 且启动时必须实际存在。framework fused 不等于 Google FLP。默认 GPS；其他通道由用户明确选择。ProviderProperties 声明固定点可提供的能力，不伪造卫星观测或不支持字段。

在添加测试源前，先同步写入待清理名称；部分注册或下发失败会逐项撤销，失败不跳过其他源。清理后才持久化确认，未确认记录跨进程保留。仅保存源名称，不存坐标。Android 不公开测试源归属，无法保证排除另一工具的并发改动；恢复前必须停止其他工具、重新授权 LocVela 并由用户确认。

状态：IDLE / RUNNING / HOLDING / CLEARED_WAITING / RECOVERY_REQUIRED。HOLDING 仍下发同一点；清理后进入等待独立读回，不自动变成“真实位置已恢复”。新进程看到未清理日志就阻止开始。异常日志损坏时拒绝猜测定位源，不清除任意名字。

活跃会话使用带超时的 PARTIAL_WAKE_LOCK，进程正常存活时 60 分钟停止；finally/onDestroy 均不是系统强停时的保证。源码/构建成功不证明三星省电或锁屏行为。

## 独立系统观察

Probe 通过 LocationManager 原生回调读取可用通道；前台服务支持切换应用后观察。每个源仅保留最新读数与计数。新鲜位置要求时间戳在本轮订阅开始后，且与单调时钟的年龄在 0–10 秒内；过期或停止后不标记新鲜。

基线必须由用户在模拟前明确采集；限定新鲜、非模拟、有合理精度字段。清理后用户手动标记观察起点，仅显示之后新收到的非模拟读数和距基线距离。这些观察不自动宣布恢复或微信成功。

## Rust 核心约定

Coordinate 只接受有限 WGS-84；球面距离不是测绘级椭球解。插值走短大圆弧并支持跨日期变更线，对跖点要求中间点。Route 含 2–100000 个点，相对毫秒从 0 起严格递增；相同坐标可停留，尾后钳制，不自动循环。当前无 GPX 和坐标系转换。

Session 提交序号为正且递增；暂停可保持点。清理回执只进入等待真实位置状态。未来传输适配器须核对 sessionId/deviceAlias/epoch/requestId 后再调用 apply，拒绝旧会话回执。

## 后续统一后端协议

```text
probeCapabilities()
prepareSession(deviceAlias, options)
pushFix(sessionId, sequence, fix)
pause(sessionId)
stopAndClear(sessionId)
getBackendHealth(sessionId)
```

iOS helper 计划使用持久开发服务连接与本机 stdio JSON Lines，消息限制 64 KiB，白名单方法，无公网端口或任意 shell；断连不能确认清理时必须未知。接口仍是设计，不表示 iOS 实现完成。

## 报告与构建

兼容报告 v1 见 `schemas/report.schema.json`，语义约束由 Python 补充；cleanup=confirmed 只确认清理。未知字段拒绝，不能塞入 UDID 或原始私人坐标。

Android 使用固定 AGP/Kotlin/Compose/JDK/Gradle 版本。`android-alpha` 执行 JVM 测试、两个 APK 构建和 Lint 后才打包；构建元数据的硬件与微信字段始终为未验证，不由 CI 自动升级。完整依赖锁与生产签名属于发布工程，当前不宣称字节级可重复构建。
