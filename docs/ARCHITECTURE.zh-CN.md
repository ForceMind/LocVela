# 架构与接口约定

## 已实现与预留边界

`crates/locvela-core` 是无依赖纯逻辑库，不能改手机定位。`tools/report.py` 是报告结构及证据一致性校验器，不鉴定证据真实性。

Android Kotlin/Compose、iOS SwiftUI、Tauri 桌面、pymobiledevice3 适配器和独立原生 Probe 尚未实现。不要因目录或设计文档存在而宣称可安装。

## 核心约定

Coordinate 仅接受有限 WGS-84 经纬度，内部字段私有；距离使用球面近似，不作测绘级精度声明。插值走短大圆弧，支持跨日期变更线；对跖点缺少唯一轨迹，要求加中间点。

Route 含 2–100000 个点，相对毫秒从 0 起且严格递增。相同坐标不同时间允许停留；采样越过尾点时停在尾点，不自动循环、不自动计算真实设备时钟。当前没有 GPX 解析、地图转换、速度编辑或 FFI。

Session 接受准备、提交、暂停、停止、清理回执及恢复观察事件。提交序号必须为正且递增；暂停态允许下发保持点。失败事件不修改为成功；清理回执只进入等待真实位置状态。

状态机是单会话逻辑。未来传输层必须先核对 sessionId、deviceAlias、epoch、requestId，拒绝旧会话和迟到回执，再调用 apply。序号不能代替身份验证。

## 平台后端（待实现）

```text
probeCapabilities()
prepareSession(deviceAlias, options)
pushFix(sessionId, sequence, fix)
pause(sessionId)
stopAndClear(sessionId)
getBackendHealth(sessionId)
```

能力分为可连接、可提交、可独立读回和实际应用可用；后者不得从前三者自动推断。Android 原生与 Google FLP 独立探测；没有 GMS 时不能伪装成 Google FLP 已启用。

iOS 桌面 helper 采用持久开发服务连接。计划通过本机标准输入/输出 JSON Lines 消息，stderr 写脱敏日志，消息大小上限 64 KiB。只接受白名单方法；不暴露公网端口、不允许任意 shell 命令。EOF、超时、退出信号应尽力清理；设备已断连时必须报告未知。

## 观测与恢复

独立 Probe 记录坐标系、单调/墙钟时间、精度、来源标记和设备会话。计算器自身缓存不能作为系统证据。当前 Rust 恢复事件要求新鲜、明确非软件模拟且基线一致；它是保守策略而非证明绝对真实性的算法。无法提供来源信息的环境维持待确认，后续由明确测试规程补充人工恢复事件，而不是伪填 false。

## 数据协议

兼容报告 v1 结构见 `schemas/report.schema.json`，语义约束由 `tools/report.py` 补充。已测结论要求完整软件版本和证据 ID，成功还要求清理确认。`cleanup=confirmed` 仅确认清理，不宣称真实位置已恢复。

新增版本需显式迁移；未知字段拒绝，不能随意把 UDID、配对材料或原始坐标塞入公共报告。
