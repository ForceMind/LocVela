// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.controller

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
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
import app.locvela.model.*

class MainActivity : ComponentActivity() {
    private var refresh by mutableIntStateOf(0)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        ControllerStore.initialize(this)
        setContent {
            val dark = isSystemInDarkTheme()
            MaterialTheme(colorScheme = if (dark) dynamicDarkColorScheme(this) else dynamicLightColorScheme(this)) {
                Screen(refresh, { refresh++ })
            }
        }
    }
    override fun onResume() { super.onResume(); refresh++ }
}

@Composable
private fun Screen(refresh: Int, onRefresh: () -> Unit) {
    val context = LocalContext.current
    val status = ControllerStore.status
    val active = status.phase == Phase.RUNNING || status.phase == Phase.HOLDING
    val editable = !active && status.phase != Phase.RECOVERY_REQUIRED
    val manager = remember { context.getSystemService(LocationManager::class.java) }
    val providers = remember(refresh) { manager.allProviders.filter { it in FixedPointSession.ALLOWED }.toSet() }
    val fine = remember(refresh) { context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED }
    val mock = remember(refresh) { mockAppSelected(context) }
    val locationOn = remember(refresh) { manager.isLocationEnabled }
    val gms = remember(refresh) { runCatching { context.packageManager.getApplicationInfo("com.google.android.gms", 0).enabled }.getOrDefault(false) }
    var latitude by remember { mutableStateOf("") }
    var longitude by remember { mutableStateOf("") }
    var selection by remember { mutableStateOf(setOf("gps")) }
    var consent by remember { mutableStateOf<Target?>(null) }
    var confirmCleanup by remember { mutableStateOf(false) }
    var inputError by remember { mutableStateOf(false) }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { onRefresh() }
    fun command(action: String) {
        runCatching { context.startService(Intent(context, MockLocationService::class.java).setAction(action)) }
            .onFailure { ControllerStore.error("command") }
    }
    fun openSettings(action: String) {
        runCatching { context.startActivity(Intent(action)) }.onFailure { ControllerStore.error("settings") }
    }
    val phaseText = when (status.phase) {
        Phase.IDLE -> R.string.state_idle
        Phase.RUNNING -> R.string.state_running
        Phase.HOLDING -> R.string.state_holding
        Phase.CLEARED_WAITING -> R.string.state_cleared
        Phase.RECOVERY_REQUIRED -> R.string.state_recovery
    }
    Scaffold(contentWindowInsets = WindowInsets.safeDrawing) { inset ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(inset).imePadding(),
            contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item {
                Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
                Text(stringResource(R.string.subtitle), style = MaterialTheme.typography.bodyMedium)
            }
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(stringResource(phaseText), style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.submitted, status.submittedBatches))
                        Text(stringResource(R.string.verification_boundary))
                        status.error?.let { Text(stringResource(R.string.error_detail, it), color = MaterialTheme.colorScheme.error) }
                    }
                }
            }
            item {
                Text(stringResource(R.string.prepare), style = MaterialTheme.typography.titleMedium)
                Text(stringResource(R.string.permission_summary, fine.toString(), mock.toString(), locationOn.toString()))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = {
                        val values = mutableListOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION)
                        if (Build.VERSION.SDK_INT >= 33) values += Manifest.permission.POST_NOTIFICATIONS
                        permissions.launch(values.toTypedArray())
                    }) { Text(stringResource(R.string.permissions)) }
                    OutlinedButton(onClick = { openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS) }) { Text(stringResource(R.string.mock_settings)) }
                }
                TextButton(onClick = { openSettings(Settings.ACTION_LOCATION_SOURCE_SETTINGS) }) { Text(stringResource(R.string.location_settings)) }
                Text(stringResource(R.string.gms_note, gms.toString()), style = MaterialTheme.typography.bodySmall)
            }
            item {
                Text(stringResource(R.string.target), style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = status.target?.latitude?.toString() ?: latitude,
                    onValueChange = { latitude = it; inputError = false },
                    label = { Text(stringResource(R.string.latitude)) }, singleLine = true,
                    enabled = editable, modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = status.target?.longitude?.toString() ?: longitude,
                    onValueChange = { longitude = it; inputError = false },
                    label = { Text(stringResource(R.string.longitude)) }, singleLine = true,
                    enabled = editable, modifier = Modifier.fillMaxWidth(),
                )
                if (inputError) Text(stringResource(R.string.invalid_point), color = MaterialTheme.colorScheme.error)
                Text(stringResource(R.string.coordinate_note), style = MaterialTheme.typography.bodySmall)
            }
            item {
                Text(stringResource(R.string.provider_heading), style = MaterialTheme.typography.titleMedium)
                for (name in listOf("gps", "network", "fused")) {
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = name in selection, enabled = editable && name in providers, onCheckedChange = {
                            selection = if (it) selection + name else selection - name
                        })
                        Text(name + if (name !in providers) " — " + stringResource(R.string.unavailable) else "")
                    }
                }
                Text(stringResource(R.string.provider_note), style = MaterialTheme.typography.bodySmall)
            }
            item {
                Button(
                    enabled = editable && fine && mock && locationOn && selection.isNotEmpty() && providers.containsAll(selection),
                    onClick = {
                        val parsed = runCatching { Target(latitude.trim().toDouble(), longitude.trim().toDouble()) }.getOrNull()
                        if (parsed == null) inputError = true else consent = parsed
                    }, modifier = Modifier.fillMaxWidth(),
                ) { Text(stringResource(R.string.start)) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(enabled = active, onClick = {
                        command(if (status.phase == Phase.HOLDING) MockLocationService.RESUME else MockLocationService.HOLD)
                    }) { Text(stringResource(if (status.phase == Phase.HOLDING) R.string.resume else R.string.hold)) }
                    Button(enabled = active || status.phase == Phase.RECOVERY_REQUIRED, onClick = {
                        if (status.phase == Phase.RECOVERY_REQUIRED) confirmCleanup = true else command(MockLocationService.STOP)
                    }) { Text(stringResource(R.string.stop)) }
                }
                Text(stringResource(R.string.lifetime_note), style = MaterialTheme.typography.bodySmall)
            }
            item {
                OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = {
                    val launch = context.packageManager.getLaunchIntentForPackage("app.locvela.probe")
                    if (launch == null) ControllerStore.error("install_probe")
                    else runCatching { context.startActivity(launch) }.onFailure { ControllerStore.error("probe") }
                }) { Text(stringResource(R.string.open_probe)) }
                Text(stringResource(R.string.wechat_note))
                Text(Build.MODEL + " · Android " + Build.VERSION.RELEASE + " · " + Build.DISPLAY, style = MaterialTheme.typography.bodySmall)
                Text("LocVela " + BuildConfig.VERSION_NAME, style = MaterialTheme.typography.bodySmall)
                Text(stringResource(R.string.license), style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = {
                    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/ForceMind/LocVela"))) }
                        .onFailure { ControllerStore.error("browser") }
                }) { Text(stringResource(R.string.source)) }
            }
        }
    }
    consent?.let { point ->
        AlertDialog(
            onDismissRequest = { consent = null }, title = { Text(stringResource(R.string.confirm_start)) },
            text = { Text(stringResource(R.string.consent)) },
            confirmButton = { TextButton(onClick = {
                consent = null
                val intent = Intent(context, MockLocationService::class.java).setAction(MockLocationService.START)
                    .putExtra("latitude", point.latitude).putExtra("longitude", point.longitude)
                    .putStringArrayListExtra("providers", ArrayList(selection))
                runCatching { context.startForegroundService(intent) }.onFailure { ControllerStore.error("foreground_start") }
            }) { Text(stringResource(R.string.start)) } },
            dismissButton = { TextButton(onClick = { consent = null }) { Text(stringResource(R.string.cancel)) } },
        )
    }
    if (confirmCleanup) AlertDialog(
        onDismissRequest = { confirmCleanup = false }, title = { Text(stringResource(R.string.stop)) },
        text = { Text(stringResource(R.string.cleanup_confirmation)) },
        confirmButton = { TextButton(onClick = { confirmCleanup = false; command(MockLocationService.STOP) }) { Text(stringResource(R.string.confirm)) } },
        dismissButton = { TextButton(onClick = { confirmCleanup = false }) { Text(stringResource(R.string.cancel)) } },
    )
}
