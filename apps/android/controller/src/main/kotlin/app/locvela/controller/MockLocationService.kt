// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.controller

import android.Manifest
import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.LocationManager
import android.os.*
import app.locvela.model.FixedPointSession
import app.locvela.model.Phase
import app.locvela.model.Target

/** Explicit user start, one main-thread writer, bounded lifetime, never START_STICKY. */
class MockLocationService : Service() {
    companion object {
        const val START = "app.locvela.START"
        const val STOP = "app.locvela.STOP"
        const val HOLD = "app.locvela.HOLD"
        const val RESUME = "app.locvela.RESUME"
        private const val CHANNEL = "location-control"
        private const val NOTIFICATION = 100
        private const val MAX_SESSION_MS = 60L * 60 * 1000
    }
    private val handler = Handler(Looper.getMainLooper())
    private var session: FixedPointSession? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var deadline = 0L
    private var ownsLiveSession = false
    private var lastError: String? = null
    private val pulse = object : Runnable {
        override fun run() {
            val current = session ?: return
            if (!current.active) return
            if (SystemClock.elapsedRealtime() >= deadline) { finishSession(); return }
            try {
                current.pulse(System.currentTimeMillis(), SystemClock.elapsedRealtimeNanos())
                ControllerStore.publish(current)
                handler.postDelayed(this, 1000L)
            } catch (_: Exception) { lastError = "submit"; finishSession() }
        }
    }
    override fun onCreate() {
        super.onCreate()
        ControllerStore.initialize(this)
        session = runCatching { FixedPointSession(AndroidProviderPort(this), PreferenceJournal(this)) }
            .getOrElse { ControllerStore.error("journal"); null }
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW)
        )
    }
    override fun onBind(intent: Intent?) = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val current = session
        if (current == null) { stopSelf(); return START_NOT_STICKY }
        when (intent?.action) {
            STOP -> finishSession()
            HOLD -> if (current.phase == Phase.RUNNING) { current.hold(); ControllerStore.publish(current) }
            RESUME -> if (current.phase == Phase.HOLDING) { current.resume(); ControllerStore.publish(current) }
            START -> {
                if (current.active) return START_NOT_STICKY
                if (current.phase == Phase.RECOVERY_REQUIRED) {
                    ControllerStore.error("cleanup_required"); stopSelf(); return START_NOT_STICKY
                }
                try {
                    check(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
                    val manager = getSystemService(LocationManager::class.java)
                    check(manager.isLocationEnabled && mockAppSelected(this))
                    val point = Target(intent.getDoubleExtra("latitude", Double.NaN), intent.getDoubleExtra("longitude", Double.NaN))
                    val names = intent.getStringArrayListExtra("providers")?.toSet() ?: emptySet()
                    startForeground(NOTIFICATION, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
                    wakeLock = getSystemService(PowerManager::class.java)
                        .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "LocVela:FixedPoint")
                        .also { it.acquire(MAX_SESSION_MS + 10_000L) }
                    ownsLiveSession = true
                    lastError = null
                    current.start(point, names, manager.allProviders.toSet(), System.currentTimeMillis(), SystemClock.elapsedRealtimeNanos())
                    deadline = SystemClock.elapsedRealtime() + MAX_SESSION_MS
                    ControllerStore.publish(current, target = point)
                    handler.postDelayed(pulse, 1000L)
                } catch (_: Exception) {
                    lastError = "start"
                    if (ownsLiveSession) finishSession()
                    else { ControllerStore.error("start"); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf() }
                }
            }
            else -> { if (ownsLiveSession) finishSession() else stopSelf() }
        }
        return START_NOT_STICKY
    }
    private fun notification(): Notification {
        val stop = PendingIntent.getService(this, 1, Intent(this, MockLocationService::class.java).setAction(STOP), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val open = PendingIntent.getActivity(this, 2, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(getString(R.string.notification_text))
            .setContentIntent(open).setOngoing(true)
            .addAction(Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel, getString(R.string.stop), stop).build())
            .build()
    }
    private fun releaseLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }
    private fun finishSession() {
        handler.removeCallbacks(pulse)
        session?.let {
            val clean = it.stop()
            ControllerStore.publish(it, if (clean) lastError else "cleanup")
        }
        ownsLiveSession = false
        releaseLock()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        // Best effort only. Android force-stop/process death need not invoke onDestroy.
        if (ownsLiveSession) session?.let {
            val clean = it.stop()
            ControllerStore.publish(it, if (clean) lastError else "cleanup")
        }
        releaseLock()
        super.onDestroy()
    }
}
