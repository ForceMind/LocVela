# LocVela（位航）

[English](README.md)

**位置由你设定，轨迹清晰可控。**

本地优先的 Android / iOS 位置模拟工程，以可观察状态、清理恢复和微信分项兼容验证为核心。

> 当前进入 **Android 固定点 Alpha**：已实现控制端和独立探针源码，成功的 `android-alpha` Actions 会生成两个 debug APK。**S25 真机及微信兼容仍未验证**。新增 iOS 桌面 JSONL 后端与独立 Swift 探针源码；尚无签名 IPA 或桌面图形界面。

## 本版内容

控制端 `app.locvela.controller` 支持 WGS-84 固定坐标、设备定位源检测、GPS/network/framework fused 选择、持续下发、保持/继续、前台通知停止和清理恢复。清理事务预先记录定位源名称，异常退出不自动续跑，也不把清理回执当作真实定位。

独立探针 `app.locvela.probe` 使用另一个包名/进程，无模拟位置权限、不依赖控制端代码或缓存，读取系统回调、来源标记、数据新鲜度，并支持测试前基线及清理后的观察起点。

**安装前阅读 [Android 使用与恢复说明](docs/ANDROID-QUICKSTART.zh-CN.md)。** 工件包含 APK、SHA-256 与构建版本信息。debug 签名可能随干净 CI 改变，覆盖安装失败时，必须先停止模拟并验证恢复，再卸载旧版。不能为安装新版直接删除尚未清理的应用数据。

最低安装版本 Android 12（API 31），不代表所有设备都经过测试。首个目标仍是三星 S25 / Android 16。

尚未包含：地图搜索、GPX/路线界面、Google FLP、Rust FFI，以及微信全功能兼容结论。framework fused 不等于 Google FLP。控制会话在进程正常存活时有 60 分钟上限，强停/系统回收可能使清理无法执行，需要重新打开明确恢复。

## iPhone 开发版

已实现固定版本 pymobiledevice3 11.31.0 的持久连接后端：明确指定设备及系统版本，默认使用进程内隧道、不自动配对、不使用 native 后备路径；支持固定点、保持、停止、失联租约、待恢复记录和重连清理。独立 SwiftUI 探针只前台读取 Core Location，不读取目标缓存。

**核验后的上游 clear 接口没有设备回复**，因此只记录“指令已发送”，不宣称清理已确认或定位恢复。人工核对恢复后的确认也单独标为用户确认，不算自动验证。详见 [iOS 开发版操作说明](docs/IOS-DEVELOPER-QUICKSTART.zh-CN.md)。当前没有可直接安装的 IPA、设备准备向导或桌面地图界面；真机与微信状态仍为未验证。

## 工程基础

Rust 核心负责 WGS-84 几何、确定性轨迹和抽象状态机；Python 校验兼容报告；Android 的 Kotlin 事务模型负责原生定位源与清理日志的生命周期。JVM 单元测试不等于三星系统验证。

两个 Android 应用均无 INTERNET 权限、登录、遥测或坐标落盘，不要求 Root，不修改微信安装包，不隐藏模拟来源标记。源码链接仅由用户点击后在外部浏览器打开。

## 开发验证

Rust 1.85.1、Python 3.10+：

```sh
cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
python -m unittest discover -s tests -v
python -m tools.report compatibility/android.unverified.json compatibility/ios.unverified.json
```

Android 另需 JDK 17、SDK platform 36 / build-tools 35.0.0，并设置 ANDROID_HOME：

```sh
python tools/android_gradle.py :model:test :controller:assembleDebug :probe:assembleDebug :controller:lintDebug :probe:lintDebug --no-daemon
```

构建脚本下载并校验固定版 Gradle，不安装到系统目录；当前尚无标准 `gradlew`。Rust `replay` 仍只是终端合成轨迹示例。报告 `VALID` 仅表示格式一致，不代表设备通过。

## 后续路线

先完成 S25 真机启停/锁屏/恢复及微信逐项验收，再补充独立 Google FLP 适配和地图/轨迹产品功能。iPhone 16 / iOS 18.4.1 已建立桌面持久开发服务后端源码，仍需真机与签名验收，本机独立运行模式后续单独验收。不默认操作用户 Mac、手机系统、现有 VPN 或部署公网网站。

[产品规格](docs/SPEC.zh-CN.md) · [技术架构](docs/ARCHITECTURE.zh-CN.md) · [兼容矩阵](docs/COMPATIBILITY.zh-CN.md) · [真机测试](docs/TEST-PLAN.zh-CN.md) · [恢复](docs/RECOVERY.zh-CN.md) · [里程碑](docs/ROADMAP.md) · [接管文档](docs/HANDOFF.zh-CN.md)

原创代码采用 [AGPL-3.0-only](LICENSE)，依赖及参考项目见 [第三方登记](THIRD_PARTY_NOTICES.md)。本项目与微信、三星、Apple 无官方关联，不提供保证。
