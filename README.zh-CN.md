# LocVela（位航）

[English](README.md)

**位置由你设定，轨迹清晰可控。**

本地优先的 Android / iOS 位置模拟与轨迹控制工程，以可观察状态、可靠退出和微信分项兼容验证为核心。

> 当前为 **M0 工程基线**，不是已经可以安装使用的手机产品。尚未交付 APK、IPA、设备注入后端或桌面界面，也没有完成微信真机验证。

## 本次已有代码

Rust 核心包含 WGS-84 坐标校验、球面距离和插值、跨日期变更线处理、有界确定性时间线及保守会话状态机。Python 工具校验兼容报告的字段、证据层级、版本、清理状态及输入边界。

两台首发目标设备：三星 Galaxy S25 / Android 16、iPhone 16 / iOS 18.4.1。完整系统构建号、微信版本和安装渠道待真机测试时记录。所有兼容状态初始化为“未验证”，不会因单元测试通过而自动改变。

## 开发验证

需要 Rust 1.85.1 和 Python 3.10+，本阶段不依赖第三方运行库。

```sh
cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo run -p locvela-core --example replay --locked
python -m unittest discover -s tests -v
python -m tools.report compatibility/android.unverified.json compatibility/ios.unverified.json
```

`replay` 只向终端输出合成坐标，不连接手机。`VALID ... unverified` 只代表报告结构合法，绝不代表功能通过。报告校验器不鉴定人工提交证据的真实性。

## 路线

Android 优先无 Root 原生模拟位置；Google FLP 是单独的可选适配器。iPhone 优先桌面助手保持开发服务会话，本机独立模式后续单独验收。不要求尾插、越狱或服务器，不默认操作用户电脑、手机系统或现有 VPN。

定位下发、独立系统读回、微信实际采用分开记录。暂停默认保持模拟点，停止执行清理；断连必须显示未知。设备坐标不等同于公网 IP、账号地区或服务端位置判断。普通系统模拟也不是“只修改微信”。

## 文档

[产品规格](docs/SPEC.zh-CN.md) · [技术架构](docs/ARCHITECTURE.zh-CN.md) · [兼容矩阵](docs/COMPATIBILITY.zh-CN.md) · [真机测试](docs/TEST-PLAN.zh-CN.md) · [恢复策略](docs/RECOVERY.zh-CN.md) · [隐私](docs/PRIVACY.zh-CN.md) · [里程碑](docs/ROADMAP.md) · [研发接管](docs/HANDOFF.zh-CN.md)

原创代码采用 [AGPL-3.0-only](LICENSE)。参考项目尚未作为依赖引入；引入前固定版本并保留原许可，详见 [第三方登记](THIRD_PARTY_NOTICES.md)。本项目与微信、三星、Apple 无官方关联。
