// SPDX-License-Identifier: AGPL-3.0-only
package app.locvela.model

import org.junit.Assert.*
import org.junit.Test

class FixedPointSessionTest {
    private class MemoryJournal : Journal {
        var names = emptySet<String>()
        var writes = 0
        var failAt = -1
        override fun pending() = names.toSet()
        override fun replace(names: Set<String>) {
            writes++
            if (writes == failAt) error("disk_failure")
            this.names = names.toSet()
        }
    }
    private class Port(private val journal: MemoryJournal) : ProviderPort {
        val enabled = mutableSetOf<String>()
        val removed = mutableListOf<String>()
        var count = 0
        var failEnable = ""
        var failSubmit = ""
        var failRemove = ""
        var last: Target? = null
        override fun enable(name: String) {
            check(name in journal.pending()) { "write_ahead_required" }
            if (name == failEnable) error("enable_failure")
            enabled += name
        }
        override fun submit(name: String, target: Target, wallTimeMs: Long, elapsedNanos: Long) {
            check(name in enabled)
            if (name == failSubmit) error("submit_failure")
            count++; last = target
        }
        override fun remove(name: String) {
            removed += name
            if (name == failRemove) error("remove_failure")
            enabled -= name
        }
    }
    private class Rig {
        val journal = MemoryJournal()
        val port = Port(journal)
        val session = FixedPointSession(port, journal)
        fun start(names: Set<String> = setOf("gps")) = session.start(Target(1.0, 2.0), names, FixedPointSession.ALLOWED, 1000, 1000)
    }
    @Test fun rejectsNonFiniteAndOutOfRange() {
        for ((lat, lon) in listOf(Double.NaN to 1.0, 1.0 to Double.POSITIVE_INFINITY, 91.0 to 1.0, 1.0 to -181.0)) {
            assertThrows(IllegalArgumentException::class.java) { Target(lat, lon) }
        }
    }
    @Test fun acceptsCoordinateBounds() { Target(-90.0, 180.0); Target(90.0, -180.0) }
    @Test fun rejectsBadAccuracy() {
        for (value in listOf(0f, Float.NaN, 101f)) assertThrows(IllegalArgumentException::class.java) { Target(0.0, 0.0, value) }
    }
    @Test fun startsAndJournalsBeforeMutation() {
        val r = Rig(); r.start(setOf("gps", "network"))
        assertEquals(Phase.RUNNING, r.session.phase)
        assertEquals(setOf("gps", "network"), r.journal.names)
        assertEquals(1L, r.session.sequence)
        assertEquals(2, r.port.count)
    }
    @Test fun rejectsUnavailableProviderWithoutMutation() {
        val r = Rig()
        assertThrows(IllegalArgumentException::class.java) { r.session.start(Target(0.0, 0.0), setOf("network"), setOf("gps"), 1, 1) }
        assertTrue(r.journal.names.isEmpty()); assertTrue(r.port.enabled.isEmpty())
    }
    @Test fun rejectsUnknownOrEmptySelection() {
        for (names in listOf(emptySet(), setOf("passive"))) {
            val r = Rig()
            assertThrows(IllegalArgumentException::class.java) { r.start(names) }
            assertTrue(r.port.enabled.isEmpty())
        }
    }
    @Test fun rejectsInvalidInitialClockWithoutMutation() {
        val r = Rig()
        assertThrows(IllegalArgumentException::class.java) { r.session.start(Target(0.0, 0.0), setOf("gps"), setOf("gps"), 0, 1) }
        assertTrue(r.journal.names.isEmpty())
    }
    @Test fun runningSessionCannotBeReplaced() {
        val r = Rig(); r.start()
        assertThrows(IllegalStateException::class.java) { r.start() }
        assertTrue(r.session.active); assertEquals(1L, r.session.sequence)
    }
    @Test fun holdingStillSendsSamePoint() {
        val r = Rig(); r.start(); r.session.hold(); r.session.pulse(2000, 2000)
        assertEquals(Phase.HOLDING, r.session.phase)
        assertEquals(Target(1.0, 2.0), r.port.last)
        assertEquals(2L, r.session.sequence)
        r.session.resume(); assertEquals(Phase.RUNNING, r.session.phase)
    }
    @Test fun stopConfirmsCleanupNotRealLocation() {
        val r = Rig(); r.start(); assertTrue(r.session.stop())
        assertEquals(Phase.CLEARED_WAITING, r.session.phase)
        assertTrue(r.journal.names.isEmpty()); assertFalse(r.session.active)
    }
    @Test fun stopIsIdempotent() {
        val r = Rig(); r.start(); r.session.stop(); r.session.stop()
        assertEquals(listOf("gps"), r.port.removed)
        assertEquals(Phase.CLEARED_WAITING, r.session.phase)
    }
    @Test fun cannotPulseAfterStop() {
        val r = Rig(); r.start(); r.session.stop()
        assertThrows(IllegalStateException::class.java) { r.session.pulse(2, 2000) }
    }
    @Test fun failedRegistrationRollsBackAllIntents() {
        val r = Rig(); r.port.failEnable = "network"
        assertThrows(SessionFault::class.java) { r.start(setOf("gps", "network")) }
        assertTrue(r.port.enabled.isEmpty()); assertTrue(r.journal.names.isEmpty())
        assertEquals(setOf("gps", "network"), r.port.removed.toSet())
    }
    @Test fun failedFirstJournalWriteDoesNotMutateProvider() {
        val r = Rig(); r.journal.failAt = 1
        assertThrows(SessionFault::class.java) { r.start() }
        assertTrue(r.port.enabled.isEmpty()); assertEquals(0, r.port.count)
    }
    @Test fun partialSubmitCannotCountAsCompletedBatch() {
        val r = Rig(); r.port.failSubmit = "network"
        assertThrows(SessionFault::class.java) { r.start(setOf("gps", "network")) }
        assertEquals(0L, r.session.sequence); assertTrue(r.journal.names.isEmpty())
    }
    @Test fun nonIncreasingClockTriggersCleanup() {
        val r = Rig(); r.start()
        assertThrows(SessionFault::class.java) { r.session.pulse(1000, 1000) }
        assertFalse(r.session.active); assertTrue(r.journal.names.isEmpty())
    }
    @Test fun wallClockMayMoveBackButElapsedMustIncrease() {
        val r = Rig(); r.start(); r.session.pulse(500, 2000)
        assertEquals(2L, r.session.sequence)
    }
    @Test fun removeFailureDoesNotSkipOtherProviders() {
        val r = Rig(); r.start(setOf("gps", "network")); r.port.failRemove = "gps"
        assertFalse(r.session.stop())
        assertEquals(setOf("gps"), r.journal.names)
        assertEquals(Phase.RECOVERY_REQUIRED, r.session.phase)
        assertTrue("network" in r.port.removed)
    }
    @Test fun cleanupCanBeExplicitlyRetried() {
        val r = Rig(); r.start(); r.port.failRemove = "gps"; r.session.stop()
        assertThrows(IllegalStateException::class.java) { r.start() }
        r.port.failRemove = ""; assertTrue(r.session.stop())
        r.start(); assertEquals(Phase.RUNNING, r.session.phase)
    }
    @Test fun restartWithPendingJournalDoesNotInject() {
        val j = MemoryJournal(); j.names = setOf("gps")
        val p = Port(j); val s = FixedPointSession(p, j)
        assertEquals(Phase.RECOVERY_REQUIRED, s.phase); assertEquals(0, p.count)
        assertTrue(s.stop()); assertEquals(Phase.CLEARED_WAITING, s.phase)
    }
    @Test fun cleanupAcknowledgementWriteFailureIsConservative() {
        val r = Rig(); r.start(); r.journal.failAt = 2
        assertFalse(r.session.stop()); assertEquals(Phase.RECOVERY_REQUIRED, r.session.phase)
        assertEquals(setOf("gps"), r.journal.names)
        assertTrue(r.session.stop())
    }
    @Test fun corruptJournalNeverRemovesArbitraryProvider() {
        val j = MemoryJournal(); j.names = setOf("foreign")
        val p = Port(j)
        assertThrows(IllegalStateException::class.java) { FixedPointSession(p, j) }
        assertTrue(p.removed.isEmpty())
    }
    @Test fun idleStopIsNotRecoveryEvidence() {
        val r = Rig(); assertTrue(r.session.stop()); assertEquals(Phase.IDLE, r.session.phase)
    }
}
