// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.model

/** Platform-adapter transaction logic, not a replacement for the shared Rust route engine. */
data class Target(val latitude: Double, val longitude: Double, val accuracyM: Float = 5f) {
    init {
        require(latitude.isFinite() && latitude in -90.0..90.0) { "invalid_latitude" }
        require(longitude.isFinite() && longitude in -180.0..180.0) { "invalid_longitude" }
        require(accuracyM.isFinite() && accuracyM in 1f..100f) { "invalid_accuracy" }
    }
}

enum class Phase { IDLE, RUNNING, HOLDING, CLEARED_WAITING, RECOVERY_REQUIRED }

interface ProviderPort {
    fun enable(name: String)
    fun submit(name: String, target: Target, wallTimeMs: Long, elapsedNanos: Long)
    /** Must be idempotent for an already-absent TEST provider; never remove a real provider. */
    fun remove(name: String)
}

interface Journal {
    fun pending(): Set<String>
    /** Synchronous durable write, throwing on failure. Contains provider names, never coordinates. */
    fun replace(names: Set<String>)
}

class SessionFault(val stage: String, cause: Exception) : Exception(stage, cause)

/** All methods are confined to one service thread. Cleanup is a transaction, not a location claim. */
class FixedPointSession(private val port: ProviderPort, private val journal: Journal) {
    companion object { val ALLOWED = setOf("gps", "network", "fused") }
    var phase: Phase = if (checkedPending().isEmpty()) Phase.IDLE else Phase.RECOVERY_REQUIRED
        private set
    var sequence: Long = 0
        private set
    private var target: Target? = null
    private var selected = emptySet<String>()
    private var lastElapsed = 0L
    val active: Boolean get() = phase == Phase.RUNNING || phase == Phase.HOLDING
    val pending: Set<String> get() = checkedPending()

    private fun checkedPending(): Set<String> = journal.pending().toSet().also {
        check(ALLOWED.containsAll(it)) { "invalid_journal_do_not_clear" }
    }

    fun start(point: Target, names: Set<String>, available: Set<String>, wallMs: Long, elapsedNs: Long) {
        check(!active && phase != Phase.RECOVERY_REQUIRED && checkedPending().isEmpty()) { "cleanup_required" }
        require(names.isNotEmpty() && ALLOWED.containsAll(names) && available.containsAll(names)) { "invalid_provider_selection" }
        require(wallMs > 0 && elapsedNs > 0) { "invalid_clock" }
        target = point
        selected = names.toSet()
        sequence = 0
        lastElapsed = 0
        try {
            for (name in selected.sorted()) {
                // Write intent BEFORE mutation, including the crash window during enable().
                journal.replace(checkedPending() + name)
                port.enable(name)
            }
            phase = Phase.RUNNING
            pulse(wallMs, elapsedNs)
        } catch (e: Exception) {
            stop()
            throw SessionFault("start", e)
        }
    }

    fun pulse(wallMs: Long, elapsedNs: Long) {
        check(active) { "not_running" }
        try {
            require(wallMs > 0 && elapsedNs > lastElapsed) { "non_increasing_clock" }
            val point = checkNotNull(target)
            for (name in selected.sorted()) port.submit(name, point, wallMs, elapsedNs)
            lastElapsed = elapsedNs
            sequence = Math.addExact(sequence, 1L)
        } catch (e: Exception) {
            stop()
            throw SessionFault("submit", e)
        }
    }

    /** Fixed-point pause keeps delivering the same coordinate. It does not clear mock mode. */
    fun hold() { check(phase == Phase.RUNNING); phase = Phase.HOLDING }
    fun resume() { check(phase == Phase.HOLDING); phase = Phase.RUNNING }

    /** Retry every journaled provider even if an earlier removal fails. Never auto-restart. */
    fun stop(): Boolean {
        target = null
        selected = emptySet()
        val names = try { checkedPending() } catch (_: Exception) {
            phase = Phase.RECOVERY_REQUIRED
            return false
        }
        var failed = false
        for (name in names.sorted()) {
            try {
                port.remove(name)
                // A failed durable acknowledgement remains conservatively pending.
                journal.replace(checkedPending() - name)
            } catch (_: Exception) { failed = true }
        }
        val remaining = try { checkedPending().isNotEmpty() } catch (_: Exception) { true }
        phase = when {
            failed || remaining -> Phase.RECOVERY_REQUIRED
            phase == Phase.IDLE && names.isEmpty() -> Phase.IDLE
            else -> Phase.CLEARED_WAITING
        }
        return !failed && !remaining
    }
}
