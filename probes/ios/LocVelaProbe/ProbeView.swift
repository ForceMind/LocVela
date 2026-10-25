// SPDX-License-Identifier: AGPL-3.0-only
import CoreLocation
import SwiftUI

@MainActor
struct ProbeView: View {
    @StateObject private var observer = LocationObserver()
    @Environment(\.scenePhase) private var scenePhase
    private func flag(_ value: Bool?) -> String {
        guard let value else { return "unknown / 未提供" }
        return value ? "true" : "false"
    }
    var body: some View {
        NavigationStack {
            TimelineView(.periodic(from: .now, by: 1)) { timeline in
                Form {
                    Section("Independent observation / 独立读取") {
                        Text("Reads Core Location only. No controller cache or location injection.\n仅读取系统，不读取控制端缓存，也不会修改定位。")
                        Text(observer.observing ? "Reading / 读取中" : "Stopped or backgrounded / 已停止或处于后台")
                        Button("Start reading / 开始读取") { observer.start() }
                        Button("Stop reading / 停止读取", role: .destructive) { observer.stop() }
                    }
                    Section("Latest system fix / 最新系统位置") {
                        if let fix = observer.latest {
                            Text(String(format: "WGS-84: %.6f, %.6f", fix.coordinate.latitude, fix.coordinate.longitude))
                                .monospacedDigit().textSelection(.enabled)
                            Text(String(format: "Accuracy / 精度: %.1f m", fix.horizontalAccuracy))
                            Text(String(format: "Age / 数据年龄: %.1f s", timeline.date.timeIntervalSince(fix.timestamp)))
                            Text("isSimulatedBySoftware: \(flag(fix.sourceInformation?.isSimulatedBySoftware))")
                            Text("isProducedByAccessory: \(flag(fix.sourceInformation?.isProducedByAccessory))")
                            Text(observer.fresh(fix, now: timeline.date) ? "Fresh / 新鲜读数" : "Stale or unconfirmed / 过期或未确认")
                            Text("Callbacks / 回调: \(observer.receivedCount)")
                            if let baseline = observer.baseline {
                                Text(String(format: "Baseline distance / 距基线: %.1f m", fix.distance(from: baseline)))
                            }
                            if let boundary = observer.recoveryBoundary, fix.timestamp > boundary,
                               observer.fresh(fix, now: timeline.date) {
                                Text("New fix after recovery marker. Independently check your real surroundings.\n已收到恢复标记后的新位置，请独立核对现实位置。")
                            }
                        } else { Text("Waiting for callbacks / 等待系统回调") }
                    }
                    Section("Recovery evidence / 恢复观察") {
                        Button("Capture pre-test baseline / 采集测试前基线") { observer.captureBaseline() }
                        Button("Clear sent: begin observation / 已发清理指令，开始观察") { observer.markRecovery() }
                        Text("A false/unknown source flag is NOT proof of real location. DVT clear has no device reply. No automatic recovery or WeChat pass is declared.\n来源标志不能证明位置真实。DVT 清理没有设备回复，本工具不自动宣布恢复或微信通过。")
                    }
                    Section("Privacy / 隐私") {
                        Text("Screen coordinates are sensitive. Nothing is saved or uploaded. Foreground observation only; returning to the app starts a fresh subscription.\n屏幕坐标属于敏感信息，不落盘、不上传。仅前台读取，返回后开始新的订阅。")
                        Button("Clear in-memory data / 清空内存数据") { observer.clearMemory() }
                        Text("Diagnostic / 诊断: \(observer.diagnostic)")
                        Text("AGPL-3.0-only · No warranty / 无担保")
                        Link("Source and license / 源码与许可证", destination: URL(string: "https://github.com/ForceMind/LocVela")!)
                    }
                }
                .navigationTitle("LocVela Probe")
            }
        }
        .onChange(of: scenePhase) { _, phase in observer.setForeground(phase == .active) }
    }
}
