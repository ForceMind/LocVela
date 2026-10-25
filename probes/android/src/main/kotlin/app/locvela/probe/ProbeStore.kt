// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.probe

import android.location.Location
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/** Raw Android observations; there is no IPC or shared cache with the controller. */
data class Sample(
    val provider: String, val latitude: Double, val longitude: Double,
    val accuracyM: Float?, val elapsedNanos: Long, val wallMs: Long,
    val softwareMock: Boolean, val subscriptionStartNanos: Long,
) {
    fun fresh(nowNanos: Long): Boolean = elapsedNanos >= subscriptionStartNanos &&
        elapsedNanos > 0 && nowNanos >= elapsedNanos && nowNanos - elapsedNanos <= 10_000_000_000L
    fun distanceM(other: Sample): Float {
        val result = FloatArray(1)
        Location.distanceBetween(latitude, longitude, other.latitude, other.longitude, result)
        return result[0]
    }
}

object ProbeStore {
    var active by mutableStateOf(false)
    var samples by mutableStateOf<Map<String, Sample>>(emptyMap())
    var counts by mutableStateOf<Map<String, Long>>(emptyMap())
    var errors by mutableStateOf<Map<String, String>>(emptyMap())
    var baseline by mutableStateOf<Sample?>(null)
    var recoveryStartNanos by mutableStateOf<Long?>(null)
    var message by mutableStateOf<String?>(null)
    fun receive(location: Location, start: Long) {
        val name = location.provider ?: return
        if (name !in setOf("gps", "network", "fused")) return
        if (!location.latitude.isFinite() || !location.longitude.isFinite() ||
            location.latitude !in -90.0..90.0 || location.longitude !in -180.0..180.0) {
            errors = errors + (name to "invalid_fix")
            return
        }
        val accuracy = location.accuracy.takeIf { location.hasAccuracy() && it.isFinite() && it >= 0f }
        val sample = Sample(name, location.latitude, location.longitude, accuracy,
            location.elapsedRealtimeNanos, location.time, location.isMock, start)
        samples = samples + (name to sample)
        counts = counts + (name to ((counts[name] ?: 0L) + 1L))
    }
    fun captureBaseline() {
        val now = SystemClock.elapsedRealtimeNanos()
        val candidate = samples.values.filter {
            active && it.fresh(now) && !it.softwareMock && it.accuracyM != null && it.accuracyM <= 100f
        }.minByOrNull { it.accuracyM!! }
        if (candidate == null) { message = "baseline_unavailable"; return }
        baseline = candidate
        recoveryStartNanos = null
        message = "baseline_captured"
    }
    fun beginRecoveryObservation() {
        if (!active || baseline == null) { message = "baseline_unavailable"; return }
        recoveryStartNanos = SystemClock.elapsedRealtimeNanos()
        message = "recovery_observing"
    }
    fun clearMemory() {
        samples = emptyMap(); counts = emptyMap(); errors = emptyMap()
        baseline = null; recoveryStartNanos = null; message = null
    }
}
