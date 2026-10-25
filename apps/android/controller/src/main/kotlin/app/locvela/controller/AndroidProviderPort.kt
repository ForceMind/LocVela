// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.controller

import android.annotation.SuppressLint
import android.app.AppOpsManager
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.location.provider.ProviderProperties
import android.os.Looper
import android.os.Process
import app.locvela.model.FixedPointSession
import app.locvela.model.Journal
import app.locvela.model.ProviderPort
import app.locvela.model.Target

fun mockAppSelected(context: Context): Boolean = runCatching {
    context.getSystemService(AppOpsManager::class.java)
        .unsafeCheckOpNoThrow(AppOpsManager.OPSTR_MOCK_LOCATION, Process.myUid(), context.packageName) == AppOpsManager.MODE_ALLOWED
}.getOrDefault(false)

class PreferenceJournal(context: Context) : Journal {
    private val preferences = context.getSharedPreferences("cleanup-journal", Context.MODE_PRIVATE)
    override fun pending(): Set<String> = preferences.getStringSet("providers", emptySet())!!.toSet()
    override fun replace(names: Set<String>) {
        check(FixedPointSession.ALLOWED.containsAll(names))
        check(preferences.edit().putStringSet("providers", names.toSet()).commit()) { "journal_write_failed" }
    }
}

/** Framework providers only. This is not the Google Play services FLP API. */
class AndroidProviderPort(private val context: Context) : ProviderPort {
    private val manager = context.getSystemService(LocationManager::class.java)
    private val listeners = mutableMapOf<String, LocationListener>()
    private fun authorize(name: String) {
        require(name in FixedPointSession.ALLOWED)
        check(mockAppSelected(context)) { "select_mock_app" }
    }
    @SuppressLint("MissingPermission") // Service requires FINE permission before configuration; exceptions propagate.
    override fun enable(name: String) {
        authorize(name)
        require(name in manager.allProviders) { "provider_unavailable" }
        val properties = ProviderProperties.Builder()
            .setAccuracy(ProviderProperties.ACCURACY_FINE)
            .setPowerUsage(ProviderProperties.POWER_USAGE_LOW)
            .setHasSpeedSupport(true)
            .build()
        manager.addTestProvider(name, properties)
        manager.setTestProviderEnabled(name, true)
        // Keep the source requested. This listener is NOT independent verification.
        val listener = object : LocationListener {
            override fun onLocationChanged(location: Location) = Unit
        }
        listeners[name] = listener
        manager.requestLocationUpdates(name, 1000L, 0f, listener, Looper.getMainLooper())
    }
    override fun submit(name: String, target: Target, wallTimeMs: Long, elapsedNanos: Long) {
        authorize(name)
        val fix = Location(name).apply {
            latitude = target.latitude
            longitude = target.longitude
            accuracy = target.accuracyM
            time = wallTimeMs
            elapsedRealtimeNanos = elapsedNanos
            speed = 0f
            speedAccuracyMetersPerSecond = 0f
        }
        // Android sets the mock-source flag. Never conceal or overwrite it.
        manager.setTestProviderLocation(name, fix)
    }
    override fun remove(name: String) {
        authorize(name)
        var listenerFailure: Exception? = null
        listeners[name]?.let {
            try { manager.removeUpdates(it); listeners.remove(name) }
            catch (e: Exception) { listenerFailure = e }
        }
        manager.removeTestProvider(name)
        listenerFailure?.let { throw it }
    }
}
