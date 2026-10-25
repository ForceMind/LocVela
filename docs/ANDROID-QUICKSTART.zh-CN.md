# Android 固定点 Alpha 使用与恢复

版本：0.1.0-alpha.1。目标：三星 Galaxy S25 / Android 16。最低安装要求 Android 12（API 31），不是所有该版本设备均已验证。

本版含两个独立 APK：`LocVela-0.1.0-alpha.1-debug.apk`（控制端）和 `LocVela-Probe-0.1.0-alpha.1-debug.apk`（只读探针）。它们是 debug 签名测试包，不是生产发布。查看同包 `build-info.json` 和 `SHA256SUMS.txt` 核对提交、构建类型与哈希；实际构建是否成功以对应 Actions 记录为准。

## 安装与首轮测试

1. 在自有测试设备上安装两个 APK。Android 可能要求为你使用的安装来源授权；三星 Auto Blocker 或设备管理策略也可能阻止安装。仅针对可信、已核验的测试包按设备提示操作，不自动关闭全局保护。
2. 控制端点“授予权限”，允许精确定位与通知；开启系统定位。到开发者选项的“选择模拟位置信息应用”选择 **LocVela 位航**，不要选探针。返回控制端后状态自动刷新。
3. 先打开探针、授权、开始读取。获得新鲜且 isMock=false 的位置后点“采集测试前基线”。精度很差或无信号时不要伪填基线。
4. 回到控制端，输入明确的 **WGS-84 十进制度坐标**。纬度在前，经度在后，英文句点；默认只勾选 gps。没有 GCJ-02 转换，不要直接复制高德/腾讯地图偏移坐标后当作 WGS-84。
5. 点“开始模拟”并阅读系统级影响提示。计数只表示下发批次，不是微信通过。打开独立探针，核对对应定位源、坐标、数据年龄和 isMock。不要隐藏 isMock 标记。
6. gps 通道确认后，才根据需求明确勾选设备实际存在的 network / fused，重复同样测试。framework fused 不等于 Google Play services FLP；本版未实现 Google FLP 适配。
7. 系统验证后再测试微信。发送地图卡片时手工选点不算修改成功；实时共享必须观察知情接收方的另一台未模拟设备。微信版本/渠道及系统构建号写入测试记录，当前项目未验证任何微信功能。

## 停止与恢复

“保持位置”仍持续发送当前点，不是恢复。“停止并清理”和通知中的停止按钮会停止定时下发，逐个移除本项目记录的测试源。只有全部清理操作和本地确认完成才显示“清理已确认”；它不等于真实位置已恢复。

在探针仍运行且基线仍存在时，点“控制端已清理，开始恢复观察”，等待时间戳更新且非模拟的位置，对比基线与现实环境。探针只给观察事实，不自动把非模拟标志解释为位置绝对真实。导航、出行等场景前应独立核对。

发生强制停止、权限撤销、系统回收、重启或异常中断时，清理回调未必执行。控制端只持久化待清理定位源名称，不保存坐标；重新打开可能显示“定位状态未知”。先停止其他工具并重新将 LocVela 选为模拟位置应用，再明确确认重试清理。Android 不公开测试定位源归属信息，恢复期间不要运行竞争工具。不能确定恢复时不要直接删除应用或清空其数据，否则会丢失待清理记录。

活跃控制会话使用有超时的 CPU 唤醒锁，每秒约一次下发；进程正常存活时最迟 60 分钟自动停止。锁屏、耗电、系统杀进程表现仍需 S25 实测。强制杀进程后不能承诺定时清理一定发生。

## 数据与权限

两个 APK 都没有 INTERNET 权限、登录、遥测或服务器。探针独立包名/进程，无模拟位置权限，不依赖控制端代码；只保留每个源最新读数、计数、基线和错误于内存。“复制诊断”不含经纬度，但截图仍可能暴露屏幕坐标。用户点源码链接时会在外部浏览器打开 GitHub。

首次 Alpha 不含地图、搜索、GPX、路线编辑、Rust FFI、GMS FLP 或 iOS 客户端。不要求 Root、越狱、尾插，也不修改微信 APK 或绕过来源标记。

## 开发构建

安装 JDK 17、Android SDK platform 36 / build-tools 35.0.0，设置 ANDROID_HOME。项目根目录执行：

```sh
python tools/android_gradle.py :model:test :controller:assembleDebug :probe:assembleDebug :controller:lintDebug :probe:lintDebug --no-daemon
```

脚本下载官方 Gradle 8.13 并核对固定 SHA-256，不安装到系统目录。Android Studio 可直接打开 `apps/android`，指定 Gradle 8.13。当前未提交标准 Gradle Wrapper，勿假设存在 `./gradlew`。

CI 在独立云端构建 APK、运行 JVM 测试和 Android Lint，生成带校验值的工件；构建不等于真机通过。每次干净 CI 的 debug 签名可能不同，覆盖安装报签名不匹配时，先完成停止和恢复核验，再卸载旧测试版后安装。不要为了覆盖安装删除尚未恢复的应用数据。

## 依据与版本固定

- Android Gradle Plugin 8.13.0 / Gradle 8.13 / JDK 17： https://developer.android.com/build/releases/agp-8-13-0-release-notes
- Gradle 8.13 bin SHA-256：`20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78`，来源 https://gradle.org/release-checksums/
- LocationManager 测试源和清理： https://developer.android.com/reference/android/location/LocationManager
- 定位前台服务与权限： https://developer.android.com/develop/background-work/services/fgs/service-types
- Kotlin 2.2.10 / Compose BOM 2025.08.01 / Activity 1.10.1 / Core KTX 1.16.0；采用固定历史版本，不宣称最新。
