use locvela_core::{Coordinate, Event, GeometryError, Route, Session, SessionError, State, TimedPoint};
fn point(lat: f64, lon: f64) -> Coordinate { Coordinate::new(lat, lon).unwrap() }
fn running() -> Session {
    let mut s = Session::default();
    s.apply(Event::Prepare).unwrap();
    s.apply(Event::Prepared).unwrap();
    s.apply(Event::Submitted(1)).unwrap();
    s
}
fn cleared() -> Session {
    let mut s = running();
    s.apply(Event::StopRequested).unwrap();
    s.apply(Event::ClearAcknowledged).unwrap();
    s
}
#[test]
fn rejects_invalid_coordinates() {
    for (lat, lon) in [(91.0, 0.0), (0.0, 181.0), (f64::NAN, 0.0), (0.0, f64::INFINITY)] {
        assert_eq!(Coordinate::new(lat, lon), Err(GeometryError::InvalidCoordinate));
    }
}
#[test]
fn includes_bounds() { assert!(Coordinate::new(-90.0, 180.0).is_ok()); }
#[test]
fn distance_sanity() {
    assert!(point(0.0, 0.0).distance_m(point(0.0, 0.0)) < 1e-6);
    assert!((point(0.0, 0.0).distance_m(point(0.0, 1.0)) - 111_195.08).abs() < 0.1);
}
#[test]
fn interpolate_crosses_date_line() {
    let p = point(0.0, 179.0).interpolate(point(0.0, -179.0), 0.5).unwrap();
    assert!((p.longitude().abs() - 180.0).abs() < 1e-6);
}
#[test]
fn interpolates_endpoints_exactly() {
    let (a, b) = (point(45.0, 10.0), point(55.0, 20.0));
    assert_eq!(a.interpolate(b, 0.0).unwrap(), a);
    assert_eq!(a.interpolate(b, 1.0).unwrap(), b);
}
#[test]
fn interpolate_identical_point() {
    let p = point(23.0, 91.0);
    assert!(p.distance_m(p.interpolate(p, 0.3).unwrap()) < 1e-6);
}
#[test]
fn refuses_antipodal_ambiguity() {
    assert_eq!(point(0.0, 0.0).interpolate(point(0.0, 180.0), 0.5), Err(GeometryError::AmbiguousAntipodes));
}
#[test]
fn rejects_bad_fraction() {
    for t in [-0.1, 1.1, f64::NAN] {
        assert_eq!(point(0.0, 0.0).interpolate(point(0.0, 1.0), t), Err(GeometryError::InvalidFraction));
    }
}
#[test]
fn route_validation() {
    assert!(Route::new(vec![]).is_err());
    let p = TimedPoint { offset_ms: 0, position: point(0.0, 0.0) };
    assert!(Route::new(vec![p, p]).is_err());
    assert!(Route::new(vec![TimedPoint { offset_ms: 1, ..p }, TimedPoint { offset_ms: 2, ..p }]).is_err());
}
#[test]
fn route_rejects_antipodes() {
    assert!(Route::new(vec![TimedPoint { offset_ms: 0, position: point(0.0, 0.0) }, TimedPoint { offset_ms: 1000, position: point(0.0, 180.0) }]).is_err());
}
#[test]
fn route_samples_and_clamps() {
    let a = point(0.0, 0.0);
    let b = point(0.0, 1.0);
    let r = Route::new(vec![TimedPoint { offset_ms: 0, position: a }, TimedPoint { offset_ms: 1000, position: b }]).unwrap();
    assert_eq!(r.duration_ms(), 1000);
    assert_eq!(r.sample(0).unwrap(), a);
    assert!((r.sample(500).unwrap().longitude() - 0.5).abs() < 1e-6);
    assert_eq!(r.sample(u64::MAX).unwrap(), b);
    assert_eq!(r.sample(500).unwrap(), r.sample(500).unwrap());
}
#[test]
fn stationary_segment_is_valid() {
    let p = point(0.0, 1.0);
    let r = Route::new(vec![TimedPoint { offset_ms: 0, position: p }, TimedPoint { offset_ms: 500, position: p }]).unwrap();
    assert!(r.sample(200).unwrap().distance_m(p) < 1e-6);
}
#[test]
fn no_start_without_preparation() {
    let mut s = Session::default();
    assert_eq!(s.apply(Event::Submitted(1)), Err(SessionError::InvalidTransition));
    assert_eq!(s.state(), State::Idle);
}
#[test]
fn rejects_duplicate_and_old_sequence() {
    let mut s = running();
    for seq in [0, 1] {
        assert_eq!(s.apply(Event::Submitted(seq)), Err(SessionError::NonIncreasingSequence));
    }
    assert_eq!(s.last_sequence(), 1);
    assert_eq!(s.apply(Event::Submitted(2)), Ok(State::Running));
}
#[test]
fn pause_is_not_stop() {
    let mut s = running();
    assert_eq!(s.apply(Event::Pause), Ok(State::Paused));
    assert_eq!(s.apply(Event::Submitted(2)), Ok(State::Paused));
    assert_eq!(s.apply(Event::Resume), Ok(State::Running));
}
#[test]
fn clear_does_not_prove_real_location() {
    assert_eq!(cleared().state(), State::ClearedWaitingForFix);
}
#[test]
fn disconnect_never_means_restored() {
    let mut s = running();
    assert_eq!(s.apply(Event::ConnectionLost), Ok(State::Unknown));
    assert!(s.apply(Event::ClearAcknowledged).is_err());
    assert_eq!(s.apply(Event::StopRequested), Ok(State::Stopping));
    assert_eq!(s.apply(Event::ClearAcknowledged), Ok(State::ClearedWaitingForFix));
}
#[test]
fn stale_or_incomplete_recovery_rejected() {
    let mut s = cleared();
    for (fresh, flag, matches) in [(false, Some(false), true), (true, None, true), (true, Some(true), true), (true, Some(false), false)] {
        assert_eq!(s.apply(Event::RecoveryObserved { fresh, software_mock: flag, baseline_matches: matches }), Err(SessionError::InsufficientRecoveryEvidence));
        assert_eq!(s.state(), State::ClearedWaitingForFix);
    }
}
#[test]
fn valid_recovery_then_explicit_restart() {
    let mut s = cleared();
    assert_eq!(s.apply(Event::RecoveryObserved { fresh: true, software_mock: Some(false), baseline_matches: true }), Ok(State::Idle));
    assert!(s.apply(Event::Submitted(2)).is_err());
    s.apply(Event::Prepare).unwrap();
    assert_eq!(s.last_sequence(), 0);
}
#[test]
fn failure_requires_recovery() {
    let mut s = running();
    assert_eq!(s.apply(Event::Failure), Ok(State::RecoveryRequired));
    assert!(s.apply(Event::Prepare).is_err());
}
#[test]
fn unexpected_ack_does_not_mutate_state() {
    let mut s = running();
    assert!(s.apply(Event::ClearAcknowledged).is_err());
    assert_eq!(s.state(), State::Running);
}
