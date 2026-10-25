# 架构与接口约定

## 已实现与预留边界

`crates/locvela-core` 是无依赖几何/轨迹/抽象会话库。`tools/report.py` 校验报告结构和证据一致性，不鉴定证据真实性。

Android Alpha 已实现：`apps/android/controller`（Kotlin/Compose 控制端）、`apps/android/model`（纯 JVM 定位源事务）、`probes/android`（独立只读 APK）。独立包名、进程、权限和存储；探针没有 model/controller 依赖，不通过控制端缓存取得结果。

iOS 已新增 `adapters/ios_pymobiledevice3` 持久 stdio 后端，以及独立前台 SwiftUI Probe。Tauri 桌面图形界面、设备准备向导和 iPhone 本机控制器尚未实现。Android 首版不连接 Rust FFI，也未实现 Google Play services FLP 或地图/路线界面。固定点后端先验证原生平台生命周期，不复制 Rust 轨迹算法。

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

iOS helper 使用 pymobiledevice3 11.31.0 的持久开发服务连接与本机 stdio JSON Lines，单行上限 64 KiB，输入队列上限 16，白名单方法，无控制监听端口或任意 shell。明确设备 UDID 文件和系统版本；默认 UserspaceRsdTunnel(serial=expected, autopair=False)，不会选择第一台设备或回退 native tunnel。也支持用户明确提供的可路由 RSD 端点。

事件循环串行处理请求和每秒固定点，所有请求有递增 ID，会话绑定随机 token；旧请求和跨会话命令拒绝。60 秒客户端租约和 60 分钟总时长，EOF/中断尽力清理。下发前先写待恢复布尔标记；本机文件锁阻止同一设备的重复 helper，不能隔离其他工具。

上游 DVT stopLocationSimulation 的 expects_reply=False。因此状态为 CLEAR_SENT，而不是 CLEARED_WAITING 或 cleanup confirmed。保留待恢复标记；只有用户明确独立核验后才接受 verify_recovery 并标记 user_confirmation_only。没有自动真实定位或微信通过。独立 Swift Probe 不保证后台持续观测，返回前台建立新订阅；来源信息缺失保持 unknown。更详细协议、数据边界和尚未实现项见 IOS-DEVELOPER-QUICKSTART。

## 报告与构建

兼容报告 v1 见 `schemas/report.schema.json`，语义约束由 Python 补充；cleanup=confirmed 只确认清理。未知字段拒绝，不能塞入 UDID 或原始私人坐标。

Android 使用固定 AGP/Kotlin/Compose/JDK/Gradle 版本。`android-alpha` 执行 JVM 测试、两个 APK 构建和 Lint 后才打包；构建元数据的硬件与微信字段始终为未验证，不由 CI 自动升级。完整依赖锁与生产签名属于发布工程，当前不宣称字节级可重复构建。
