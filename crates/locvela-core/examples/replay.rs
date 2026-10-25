use locvela_core::{Coordinate, Route, TimedPoint};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let route = Route::new(vec![
        TimedPoint { offset_ms: 0, position: Coordinate::new(0.0, 179.0)? },
        TimedPoint { offset_ms: 10_000, position: Coordinate::new(0.0, -179.0)? },
    ])?;
    println!("DRY RUN ONLY: no device connection or location injection");
    for ms in (0..=10_000).step_by(2_000) {
        let p = route.sample(ms)?;
        println!("{ms}ms: {:.6}, {:.6}", p.latitude(), p.longitude());
    }
    Ok(())
}
