# LocVela 持续研发接管

仓库 ForceMind/LocVela，main，保持公开；这是已有工程，不要重新初始化。

先重新核对最新提交、PR、Issue、CI；阅读 AGENTS、README、SPEC、ARCHITECTURE、COMPATIBILITY、ROADMAP。本文件的阶段描述不能替代当前仓库状态。

## 当前工程

M0 Rust 核心与报告工具已在前次基线建立。Android Alpha 新增两个独立 APK 工程：`apps/android/controller` 和 `probes/android`；纯 JVM `apps/android/model` 实现固定点后端事务测试。控制端支持原生定位源、持续通知、保持/停止、写前清理日志、异常恢复；探针独立读取时间戳/来源/基线。两个应用无网络权限。

实际可下载 APK 以成功的 android-alpha Actions 工件为准。不得把源码存在、JVM 测试或构建通过说成 S25/微信验收。两台用户设备仍未连接测试。Google FLP、Rust FFI、地图/路线界面、iOS 后端与桌面 UI 尚未完成。

## 下一可执行任务

优先核对 Android 工件和实际安装反馈，修复运行期故障；增加独立 Google FLP 适配与 Probe 观测通道（具备 GMS 才启用）。并行推进 Issue #3 的 iPhone 桌面最小链路：核验并固定 pymobiledevice3，持久会话、清理回执、断连未知及 Swift 原生 Probe。不要每秒创建一个 CLI 进程，也不要同时铺设多个空壳客户端。

Android 验证命令：

```sh
python tools/android_gradle.py :model:test :controller:assembleDebug :probe:assembleDebug :controller:lintDebug :probe:lintDebug --no-daemon
```

基础仍须运行 cargo test、Clippy 和 Python unittest，见 AGENTS。GitHub CI 是实际云端执行，不是用户 Mac。debug 签名可能随 CI 改变；换包前必须先清理并验证恢复。

不要操作用户 Mac、升级/Root/越狱手机、修改现有 VPN、清除微信数据或部署网站。无设备时如实交付待执行步骤，保留所有硬件兼容项未验证。每轮给出真实提交、测试结果、工件及未完成项，不承诺无执行机制的后台持续开发。
