use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    Idle,
    Preparing,
    Ready,
    Running,
    Paused,
    Stopping,
    ClearedWaitingForFix,
    Unknown,
    RecoveryRequired,
}
#[derive(Debug, Clone, Copy)]
pub enum Event {
    Prepare,
    Prepared,
    Submitted(u64),
    Pause,
    Resume,
    StopRequested,
    ClearAcknowledged,
    /// Supplied only by an independent observer after cleanup acknowledgement.
    RecoveryObserved { fresh: bool, software_mock: Option<bool>, baseline_matches: bool },
    ConnectionLost,
    Failure,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionError {
    InvalidTransition,
    NonIncreasingSequence,
    InsufficientRecoveryEvidence,
}
impl fmt::Display for SessionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for SessionError {}

/// Callers must correlate device/session IDs and reject late receipts before apply().
#[derive(Debug, Clone)]
pub struct Session {
    state: State,
    last_sequence: u64,
}
impl Default for Session {
    fn default() -> Self {
        Self { state: State::Idle, last_sequence: 0 }
    }
}
impl Session {
    pub fn state(&self) -> State {
        self.state
    }
    pub fn last_sequence(&self) -> u64 {
        self.last_sequence
    }
    /// Errors leave both state and sequence unchanged. Submission is not verification.
    pub fn apply(&mut self, event: Event) -> Result<State, SessionError> {
        use Event::*;
        use State::*;
        let next = match (self.state, event) {
            (Idle, Prepare) => {
                self.last_sequence = 0;
                Preparing
            }
            (Preparing, Prepared) => Ready,
            (Ready | Running | Paused, Submitted(sequence)) => {
                if sequence <= self.last_sequence {
                    return Err(SessionError::NonIncreasingSequence);
                }
                self.last_sequence = sequence;
                if self.state == Paused { Paused } else { Running }
            }
            (Running, Pause) => Paused,
            (Paused, Resume) => Running,
            (Preparing | Ready | Running | Paused | Unknown | RecoveryRequired, StopRequested) => Stopping,
            (Stopping, StopRequested) => Stopping,
            (Stopping, ClearAcknowledged) => ClearedWaitingForFix,
            (ClearedWaitingForFix, RecoveryObserved { fresh, software_mock, baseline_matches }) => {
                if !fresh || software_mock != Some(false) || !baseline_matches {
                    return Err(SessionError::InsufficientRecoveryEvidence);
                }
                Idle
            }
            (state, ConnectionLost) if state != Idle => Unknown,
            (state, Failure) if state != Idle => RecoveryRequired,
            _ => return Err(SessionError::InvalidTransition),
        };
        self.state = next;
        Ok(next)
    }
}
