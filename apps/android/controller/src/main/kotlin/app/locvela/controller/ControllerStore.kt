// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.controller

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import app.locvela.model.FixedPointSession
import app.locvela.model.Phase
import app.locvela.model.Target

data class ControllerStatus(
    val phase: Phase = Phase.IDLE,
    val submittedBatches: Long = 0,
    val providers: Set<String> = emptySet(),
    val target: Target? = null,
    val error: String? = null,
)

/** Process-local presentation only. No coordinates are persisted or exported. */
object ControllerStore {
    var status by mutableStateOf(ControllerStatus())
        private set
    private var initialized = false
    fun initialize(context: Context) {
        if (initialized) return
        initialized = true
        try {
            val pending = PreferenceJournal(context).pending()
            check(FixedPointSession.ALLOWED.containsAll(pending))
            status = ControllerStatus(
                phase = if (pending.isEmpty()) Phase.IDLE else Phase.RECOVERY_REQUIRED,
                providers = pending,
            )
        } catch (_: Exception) { status = ControllerStatus(phase = Phase.RECOVERY_REQUIRED, error = "journal") }
    }
    fun publish(session: FixedPointSession, error: String? = null, target: Target? = status.target) {
        status = ControllerStatus(
            phase = session.phase,
            submittedBatches = session.sequence,
            providers = runCatching { session.pending }.getOrDefault(status.providers),
            target = if (session.active) target else null,
            error = error,
        )
    }
    fun error(code: String) { status = status.copy(error = code) }
}
