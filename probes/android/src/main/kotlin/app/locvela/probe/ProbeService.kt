// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.probe

import android.Manifest
import android.annotation.SuppressLint
import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.*

class ProbeService : Service(), LocationListener {
    companion object {
        const val START = "app.locvela.probe.START"
        const val STOP = "app.locvela.probe.STOP"
        private const val CHANNEL = "location-observer"
        private const val NOTIFICATION = 200
    }
    private lateinit var manager: LocationManager
    private val handler = Handler(Looper.getMainLooper())
    private var startedAt = 0L
    override fun onCreate() {
        super.onCreate()
        manager = getSystemService(LocationManager::class.java)
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW)
        )
    }
    override fun onBind(intent: Intent?) = null
    @SuppressLint("MissingPermission") // Explicit FINE check; each subscription catches permission revocation.
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action != START) { stopObservation(); return START_NOT_STICKY }
        if (ProbeStore.active) return START_NOT_STICKY
        try {
            check(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
            check(manager.isLocationEnabled)
            startForeground(NOTIFICATION, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
            ProbeStore.clearMemory()
            startedAt = SystemClock.elapsedRealtimeNanos()
            var subscriptions = 0
            for (name in manager.allProviders.filter { it in setOf("gps", "network", "fused") }) {
                try {
                    manager.requestLocationUpdates(name, 1000L, 0f, this, Looper.getMainLooper())
                    subscriptions++
                } catch (_: Exception) { ProbeStore.errors = ProbeStore.errors + (name to "subscription_failed") }
            }
            check(subscriptions > 0)
            ProbeStore.active = true
            handler.postDelayed({ stopObservation() }, 60L * 60 * 1000)
        } catch (_: Exception) {
            ProbeStore.message = "start_failed"
            stopObservation()
        }
        return START_NOT_STICKY
    }
    override fun onLocationChanged(location: Location) {
        if (ProbeStore.active) ProbeStore.receive(Location(location), startedAt)
    }
    override fun onProviderDisabled(provider: String) {
        ProbeStore.errors = ProbeStore.errors + (provider to "provider_disabled")
    }
    override fun onProviderEnabled(provider: String) {
        ProbeStore.errors = ProbeStore.errors - provider
    }
    private fun notification(): Notification {
        val stop = PendingIntent.getService(this, 3, Intent(this, ProbeService::class.java).setAction(STOP), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val open = PendingIntent.getActivity(this, 4, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return Notification.Builder(this, CHANNEL).setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentTitle(getString(R.string.app_name)).setContentText(getString(R.string.notification_text))
            .setContentIntent(open).setOngoing(true)
            .addAction(Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel, getString(R.string.stop), stop).build()).build()
    }
    private fun stopObservation() {
        handler.removeCallbacksAndMessages(null)
        try { manager.removeUpdates(this) } catch (_: Exception) { ProbeStore.message = "stop_failed" }
        ProbeStore.active = false
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        runCatching { manager.removeUpdates(this) }.onFailure { ProbeStore.message = "stop_failed" }
        ProbeStore.active = false
        super.onDestroy()
    }
}
