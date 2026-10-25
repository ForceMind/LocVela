// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.probe

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.*
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import java.util.Locale

class MainActivity : ComponentActivity() {
    private var refresh by mutableIntStateOf(0)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme(colorScheme = if (isSystemInDarkTheme()) dynamicDarkColorScheme(this) else dynamicLightColorScheme(this)) {
                ProbeScreen(refresh, { refresh++ })
            }
        }
    }
    override fun onResume() { super.onResume(); refresh++ }
}

@Composable
private fun ProbeScreen(refresh: Int, onRefresh: () -> Unit) {
    val context = LocalContext.current
    var now by remember { mutableLongStateOf(SystemClock.elapsedRealtimeNanos()) }
    LaunchedEffect(Unit) { while (true) { delay(1000L); now = SystemClock.elapsedRealtimeNanos() } }
    val permitted = remember(refresh) {
        context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { onRefresh() }
    Scaffold(contentWindowInsets = WindowInsets.safeDrawing) { inset ->
        LazyColumn(Modifier.fillMaxSize().padding(inset), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            item {
                Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
                Text(stringResource(R.string.boundary))
                Text(stringResource(if (ProbeStore.active) R.string.active else R.string.inactive), style = MaterialTheme.typography.titleMedium)
            }
            item {
                OutlinedButton(onClick = {
                    val values = mutableListOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION)
                    if (Build.VERSION.SDK_INT >= 33) values += Manifest.permission.POST_NOTIFICATIONS
                    permissions.launch(values.toTypedArray())
                }) { Text(stringResource(R.string.permissions)) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(enabled = permitted && !ProbeStore.active, onClick = {
                        runCatching { context.startForegroundService(Intent(context, ProbeService::class.java).setAction(ProbeService.START)) }
                            .onFailure { ProbeStore.message = "start_failed" }
                    }) { Text(stringResource(R.string.start)) }
                    OutlinedButton(enabled = ProbeStore.active, onClick = {
                        runCatching { context.startService(Intent(context, ProbeService::class.java).setAction(ProbeService.STOP)) }
                            .onFailure { ProbeStore.message = "stop_failed" }
                    }) { Text(stringResource(R.string.stop)) }
                }
            }
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(stringResource(R.string.recovery_title), style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.baseline_explanation))
                        OutlinedButton(enabled = ProbeStore.active, onClick = { ProbeStore.captureBaseline() }) { Text(stringResource(R.string.capture_baseline)) }
                        OutlinedButton(enabled = ProbeStore.active && ProbeStore.baseline != null, onClick = { ProbeStore.beginRecoveryObservation() }) { Text(stringResource(R.string.mark_cleanup)) }
                        Text(stringResource(R.string.no_auto_pass))
                        ProbeStore.message?.let { message ->
                            val label = when (message) {
                                "baseline_captured" -> R.string.baseline_captured
                                "baseline_unavailable" -> R.string.baseline_unavailable
                                "recovery_observing" -> R.string.recovery_observing
                                else -> R.string.observer_error
                            }
                            Text(stringResource(label))
                        }
                    }
                }
            }
            if (ProbeStore.samples.isEmpty()) item { Text(stringResource(R.string.waiting)) }
            for ((name, sample) in ProbeStore.samples.toSortedMap()) {
                item(key = name) {
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(name, style = MaterialTheme.typography.titleMedium)
                            Text(stringResource(R.string.coordinates, sample.latitude, sample.longitude))
                            val age = if (sample.elapsedNanos > 0 && now >= sample.elapsedNanos)
                                String.format(Locale.ROOT, "%.1f", (now - sample.elapsedNanos) / 1e9) else "unknown"
                            Text(stringResource(R.string.details, age, sample.accuracyM?.toString() ?: "unknown", sample.softwareMock.toString()))
                            Text(stringResource(if (sample.fresh(now) && ProbeStore.active) R.string.fresh else R.string.stale))
                            Text(stringResource(R.string.count, ProbeStore.counts[name] ?: 0L))
                            val baseline = ProbeStore.baseline
                            val marker = ProbeStore.recoveryStartNanos
                            if (baseline != null) Text(stringResource(R.string.baseline_distance, sample.distanceM(baseline)))
                            if (marker != null && sample.elapsedNanos > marker && sample.fresh(now) && !sample.softwareMock && ProbeStore.active)
                                Text(stringResource(R.string.recovery_candidate))
                        }
                    }
                }
            }
            for ((name, error) in ProbeStore.errors.toSortedMap()) item { Text(name + ": " + error, color = MaterialTheme.colorScheme.error) }
            item {
                OutlinedButton(onClick = {
                    val text = buildString {
                        appendLine("LocVela Probe ${BuildConfig.VERSION_NAME}; Android ${Build.VERSION.RELEASE}; build ${Build.DISPLAY}")
                        appendLine("Redacted: no coordinates, no device serial. Not a compatibility pass.")
                        for ((name, sample) in ProbeStore.samples.toSortedMap()) {
                            appendLine("$name: mock=${sample.softwareMock}; fresh=${sample.fresh(now) && ProbeStore.active}; accuracy=${sample.accuracyM}; samples=${ProbeStore.counts[name]}")
                        }
                    }
                    context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("LocVela Probe", text))
                }) { Text(stringResource(R.string.copy_redacted)) }
                TextButton(onClick = { ProbeStore.clearMemory() }) { Text(stringResource(R.string.clear_memory)) }
                Text(stringResource(R.string.privacy))
                Text(stringResource(R.string.license), style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = {
                    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/ForceMind/LocVela"))) }
                        .onFailure { ProbeStore.message = "browser_failed" }
                }) { Text(stringResource(R.string.source)) }
            }
        }
    }
}
