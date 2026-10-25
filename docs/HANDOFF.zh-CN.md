# LocVela 持续研发接管

仓库 ForceMind/LocVela，main，保持公开；这是已有工程，不要重新初始化。

先重新核对最新提交、PR、Issue、CI；阅读 AGENTS、README、SPEC、ARCHITECTURE、COMPATIBILITY、ROADMAP。本文件的阶段描述不能替代当前仓库状态。

## 当前工程

M0 Rust 核心与报告工具已在前次基线建立。Android Alpha 新增两个独立 APK 工程：`apps/android/controller` 和 `probes/android`；纯 JVM `apps/android/model` 实现固定点后端事务测试。控制端支持原生定位源、持续通知、保持/停止、写前清理日志、异常恢复；探针独立读取时间戳/来源/基线。两个应用无网络权限。

实际可下载 APK 以成功的 android-alpha Actions 工件为准。不得把源码存在、JVM 测试或构建通过说成 S25/微信验收。两台用户设备仍未连接测试。Google FLP、Rust FFI、地图/路线界面、桌面 UI 尚未完成；iOS 后端的新增情况见文末。

## 下一可执行任务

优先核对 Android 工件和实际安装反馈，修复运行期故障；增加独立 Google FLP 适配与 Probe 观测通道（具备 GMS 才启用）。Issue #3 已有固定上游、持久后端和 Swift Probe，接下来封装设备准备向导与桌面控制；clear 无设备回复，不能按清理回执处理。不要每秒创建一个 CLI 进程，也不要同时铺设多个空壳客户端。

Android 验证命令：

```sh
python tools/android_gradle.py :model:test :controller:assembleDebug :probe:assembleDebug :controller:lintDebug :probe:lintDebug --no-daemon
```

基础仍须运行 cargo test、Clippy 和 Python unittest，见 AGENTS。GitHub CI 是实际云端执行，不是用户 Mac。debug 签名可能随 CI 改变；换包前必须先清理并验证恢复。

不要操作用户 Mac、升级/Root/越狱手机、修改现有 VPN、清除微信数据或部署网站。无设备时如实交付待执行步骤，保留所有硬件兼容项未验证。每轮给出真实提交、测试结果、工件及未完成项，不承诺无执行机制的后台持续开发。


## iOS 持续连接增量（本轮）

新增 `adapters/ios_pymobiledevice3`、`probes/ios/LocVelaProbe.xcodeproj`、`docs/IOS-DEVELOPER-QUICKSTART.zh-CN.md` 和 ios-development CI。上游固定 pymobiledevice3 11.31.0。接口需要 Python 3.11；独立 Probe 需要用户自己的签名才能安装真机。

覆盖持久会话、白名单 stdio、明确目标、固定点/保持/停止、租约、持久待恢复标记。上游 clear 无回复，只记录 CLEAR_SENT；人工核对也仅是 user_confirmation_only。没有真机验证，不得把单元测试、依赖导入或 Swift 编译升级成兼容通过。

下一步：完成 iOS 设备准备向导/桌面图形控制与真机连接，Android 独立 Google FLP 通道仍待实现。先核对最新 PR 和 CI，修复实际失败后再增加功能。没有操作用户 Mac/手机。可在云端继续实现无需真机的工作，不必因真机缺席停掉整个工程。
