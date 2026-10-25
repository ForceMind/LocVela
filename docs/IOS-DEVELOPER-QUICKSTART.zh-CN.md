# iPhone 桌面开发版：持续会话与独立探针

这是 **开发者测试版**，不是带地图的桌面成品，也不是可以直接安装的 IPA。目标设备为用户的 iPhone 16 / iOS 18.4.1；当前尚无该真机的连接、定位或微信验收证据。

## 本轮交付

`adapters/ios_pymobiledevice3` 是本机 stdio JSONL 控制程序。默认使用固定版 pymobiledevice3 的进程内 UserspaceRsdTunnel，明确选择一台设备并复用 RSD → DVT → LocationSimulation 连接。支持固定坐标、更新坐标、保持/继续、停止、重新连接清理和人工恢复确认。没有任意命令执行接口，没有公网或本地控制监听端口。高级模式可复用用户事先建立的可路由 RSD 地址。

`probes/ios/LocVelaProbe.xcodeproj` 是独立 SwiftUI / Core Location 只读探针。它既不从 helper 读取目标缓存，也不执行模拟。只前台读取；切到微信后不承诺后台持续观测，重新回到探针时重新订阅并重新判断新鲜度。坐标和基线仅保留在内存。CI 编译模拟器及无签名设备目标，**不是生成可安装 IPA，更不是完成真机测试**。

## 重要：停止不是“恢复成功”

核验的上游版本 `11.31.0`（提交 `06f3c1c786e11b94c5e20f7d31a3b283f133fa0c`）中 `stopLocationSimulation` 明确标记 `expects_reply=False`。因此本工具只返回 `CLEAR_SENT` / `sent_unconfirmed`，不能伪称收到设备清理确认。

待恢复标记在写入任何坐标前落盘。发送 clear、断线或正常退出都不会擅自清除此标记。用户通过独立探针及现实环境核对后，可以显式 `verify_recovery`；返回 `user_confirmation_only`，仍不算工具自动验证或微信通过。没有独立证据时保持待恢复。

## 准备环境（由设备持有人自行授权）

在你的测试电脑上安装 Python 3.11，创建独立环境并安装固定依赖；本项目不会远程替你修改 Mac 或 iPhone：

```sh
python3 -m venv .venv-ios
# macOS/Linux
source .venv-ios/bin/activate
# Windows PowerShell 改为：.venv-ios\Scripts\Activate.ps1
python -m pip install -r adapters/ios_pymobiledevice3/requirements.txt
python -m tools.check_ios_backend_api
```

Windows 需要可用的 Apple 设备通信驱动，Linux 需要可用的 usbmuxd；错误不能用“模拟成功”遮掩。iPhone 必须由用户完成解锁、信任/配对、开发者模式及相应开发支持组件准备。相关操作可能有设备确认或重启；本 helper 不替你启用模式、升级系统、挂载未知镜像或更改现有 VPN。

可用同一虚拟环境中的上游 CLI 检查 USB 设备和开发支持，先查看当前固定版本帮助：

```sh
python -m pymobiledevice3 usbmux list
python -m pymobiledevice3 mounter auto-mount --help
```

首次 DDI/配对准备尚未封装成 LocVela 向导。只选择自己的设备，按上游固定版本说明准备；不要将工具打印的完整设备信息、UDID 或配对记录贴进公共 Issue。

将目标设备的 UDID 单独存入一个受保护的本地纯文本文件，例如用户私有目录下的 `iphone-id.txt`，不要放进仓库。启动时必须指定该文件，绝不默认选择第一台设备。默认期望系统版本 18.4.1，不一致会拒绝连接，避免把测试结论套用到另一版本。

```sh
python -m adapters.ios_pymobiledevice3 --device-id-file /你的私有目录/iphone-id.txt
```

Windows 使用自己的本地路径。默认进程内隧道不调用 sudo、不创建内核 VPN、不使用 native remoted 后备路径；实际可用性仍取决于主机驱动、设备配对与版本。显式 RSD 模式仅在已建立一个其他进程可达的隧道时使用：

```sh
python -m adapters.ios_pymobiledevice3 --device-id-file /私有目录/iphone-id.txt --rsd-host fd00::1 --rsd-port 58783
```

此地址只是示例，必须换成自己的实际隧道地址。不能从另一个程序的进程内隧道复制地址后假定可以跨进程访问。

## JSONL 命令协议

每行一个 JSON 对象，必须以换行结束。最大 64 KiB；重复键、未知字段/方法、NaN/Infinity、超范围坐标、旧请求和错误会话被拒绝。`id` 是递增正整数；第一条 `prepare` 的响应会给出 32 位十六进制 `session`，后续所有改变定位的命令必须原样使用这个值。以下 `SESSION` 是占位符，不可原样执行。

```json
{"v":1,"id":1,"session":null,"op":"prepare","params":{"consent":true}}
{"v":1,"id":2,"session":"SESSION","op":"set","params":{"latitude":37.7749,"longitude":-122.4194}}
{"v":1,"id":3,"session":"SESSION","op":"status","params":{}}
{"v":1,"id":4,"session":"SESSION","op":"hold","params":{}}
{"v":1,"id":5,"session":"SESSION","op":"resume","params":{}}
{"v":1,"id":6,"session":"SESSION","op":"stop","params":{}}
```

默认每秒重复下发当前点；保持位置不是恢复。`status` 的 `submitted_batches` 只表示调用完成，不是系统读回。带正确 session 的命令续期客户端租约；默认 60 秒没有续期就停止下发并尽力 clear。会话总上限 60 分钟，坐标更新不能延长总上限。`--lease-seconds` 允许测试时设置 5–300 秒；这是失联停止机制，不是无期限后台运行承诺。

独立核对恢复后才能发送：

```json
{"v":1,"id":7,"session":"SESSION","op":"verify_recovery","params":{"independently_checked":true}}
{"v":1,"id":8,"session":"SESSION","op":"quit","params":{}}
```

进程重启发现待恢复标记后，`prepare` 只建立连接，不允许 set；明确发送 `recover` 才重新连接同一设备并重试 clear。重新连接不会自动继续轨迹。EOF、Ctrl+C、SIGTERM、超长输入和输出管道断开都尽力清理；拔线、强制杀进程、断电无法保证执行清理，必须保留未知状态。

## 独立 Probe 的设备安装

用 Xcode 打开 `probes/ios/LocVelaProbe.xcodeproj`，在自己的 Apple 开发签名环境中选择 Team 与设备后构建。没有有效签名不能直接安装；不要把 CI 的无签名产物当作 IPA。

先在没有模拟时授权并采集基线，再运行 helper 的固定点。回到 Probe 看新鲜时间戳、原始坐标与来源信息，再单独测试微信。来源信息可能缺失，`false` 也不是“位置一定真实”；探针不自动给恢复或微信打勾。

## 数据、依赖与剩余工作

stdio 输出不包含坐标、UDID、端点、配对文件或原始异常。恢复文件只记录一个布尔状态，文件名采用设备标识 SHA-256（仍应视为关联标识，不是完全匿名）；本机锁防止本工具两个实例同时写同一设备，不能约束其他定位工具。POSIX 目录要求 0700；Windows 使用用户私有目录，未实现专门的 ACL 加固。配对材料由上游管理，不复制进本项目。

依赖固定为 pymobiledevice3 11.31.0，但传递依赖尚未形成完整锁文件/SBOM，不宣称生产级供应链封装。首版没有桌面图形界面、设备准备向导、路线编辑、自动签名、iPhone 本机独立控制。Android Google FLP 也仍未接入，不能因为本次 iOS 工作宣称 Android 已升级。

## 已核验的上游依据

- 固定版本与接口：https://github.com/doronz88/pymobiledevice3/tree/06f3c1c786e11b94c5e20f7d31a3b283f133fa0c
- Python 连接方式：`docs/guides/python-api.md`
- 进程内隧道范围：`docs/guides/ios17-tunnels.md`
- DVT 类型：`pymobiledevice3/services/dvt/instruments/dvt_provider.py`
- clear 无回复：`pymobiledevice3/services/dvt/instruments/location_simulation.py`
