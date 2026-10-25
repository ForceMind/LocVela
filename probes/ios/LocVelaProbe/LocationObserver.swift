// SPDX-License-Identifier: AGPL-3.0-only
import Combine
import CoreLocation
import Foundation

/// Independent Core Location observations; no imports or IPC from the controller.
@MainActor
final class LocationObserver: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    @Published private(set) var latest: CLLocation?
    @Published private(set) var baseline: CLLocation?
    @Published private(set) var recoveryBoundary: Date?
    @Published private(set) var receivedCount = 0
    @Published private(set) var observing = false
    @Published private(set) var authorization = CLAuthorizationStatus.notDetermined
    @Published private(set) var diagnostic = "not_started"
    @Published private(set) var subscriptionStart = Date.distantFuture
    private var requested = false
    private var foreground = true

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = kCLDistanceFilterNone
        authorization = manager.authorizationStatus
    }
    func start() {
        requested = true
        if authorization == .notDetermined {
            manager.requestWhenInUseAuthorization()
        } else {
            activateIfPermitted()
        }
    }
    func stop() {
        requested = false
        manager.stopUpdatingLocation()
        observing = false
        diagnostic = "observation_stopped"
    }
    func setForeground(_ value: Bool) {
        foreground = value
        if value { activateIfPermitted() }
        else {
            manager.stopUpdatingLocation()
            observing = false
            diagnostic = "paused_in_background"
        }
    }
    private func activateIfPermitted() {
        guard requested, foreground else { return }
        guard authorization == .authorizedWhenInUse || authorization == .authorizedAlways else {
            diagnostic = "location_permission_required"
            observing = false
            return
        }
        guard !observing else { return }
        subscriptionStart = Date()
        observing = true
        diagnostic = "waiting_for_location"
        manager.startUpdatingLocation()
    }
    func fresh(_ value: CLLocation?, now: Date) -> Bool {
        guard observing, let value else { return false }
        let age = now.timeIntervalSince(value.timestamp)
        return value.timestamp >= subscriptionStart && age >= 0 && age <= 10
            && value.horizontalAccuracy.isFinite && value.horizontalAccuracy >= 0
    }
    func captureBaseline() {
        guard let value = latest, fresh(value, now: Date()),
              value.sourceInformation?.isSimulatedBySoftware == false,
              value.horizontalAccuracy <= 100 else {
            diagnostic = "baseline_unavailable"
            return
        }
        baseline = value
        recoveryBoundary = nil
        diagnostic = "baseline_captured_not_verified"
    }
    func markRecovery() {
        guard baseline != nil, observing else { diagnostic = "baseline_required"; return }
        recoveryBoundary = Date()
        diagnostic = "recovery_observation_started"
    }
    func clearMemory() {
        latest = nil; baseline = nil; recoveryBoundary = nil; receivedCount = 0
        diagnostic = "memory_cleared"
    }
    // This manager is initialized on MainActor. Apple delivers its delegate calls
    // on that initialization thread's runloop. Enforce that runtime contract rather
    // than suppressing concurrency diagnostics or marking the manager Sendable.
    // https://developer.apple.com/videos/play/wwdc2024/10169/ (39:32-40:06)
    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        MainActor.assumeIsolated {
            authorization = self.manager.authorizationStatus
            if authorization != .authorizedWhenInUse && authorization != .authorizedAlways {
                self.manager.stopUpdatingLocation(); observing = false
            }
            activateIfPermitted()
        }
    }
    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        MainActor.assumeIsolated {
            guard observing else { return }
            for value in locations {
                guard CLLocationCoordinate2DIsValid(value.coordinate),
                      value.coordinate.latitude.isFinite, value.coordinate.longitude.isFinite else { continue }
                // Do not let an out-of-order callback replace a newer observation.
                if let previous = latest, value.timestamp < previous.timestamp { continue }
                latest = value
                receivedCount += 1
                diagnostic = "system_callback_received"
            }
        }
    }
    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        MainActor.assumeIsolated {
            // Do not expose localized exception text or device identifiers in diagnostics.
            diagnostic = "location_read_failed"
        }
    }
}
