use crate::{Coordinate, GeometryError};

#[derive(Debug, Clone, Copy)]
pub struct TimedPoint {
    pub offset_ms: u64,
    pub position: Coordinate,
}

/// Immutable, bounded timeline; timestamps are relative, not wall-clock time.
#[derive(Debug, Clone)]
pub struct Route {
    points: Vec<TimedPoint>,
}
impl Route {
    pub fn new(points: Vec<TimedPoint>) -> Result<Self, GeometryError> {
        if !(2..=100_000).contains(&points.len()) || points[0].offset_ms != 0 {
            return Err(GeometryError::InvalidTimeline);
        }
        for pair in points.windows(2) {
            if pair[0].offset_ms >= pair[1].offset_ms {
                return Err(GeometryError::InvalidTimeline);
            }
            pair[0].position.interpolate(pair[1].position, 0.5)?;
        }
        Ok(Self { points })
    }
    pub fn duration_ms(&self) -> u64 {
        self.points[self.points.len() - 1].offset_ms
    }
    /// Clamp to the last point after completion. Repeating is a caller decision.
    pub fn sample(&self, elapsed_ms: u64) -> Result<Coordinate, GeometryError> {
        let last = self.points[self.points.len() - 1];
        if elapsed_ms >= last.offset_ms {
            return Ok(last.position);
        }
        let index = self.points.partition_point(|p| p.offset_ms <= elapsed_ms);
        let a = self.points[index - 1];
        let b = self.points[index];
        let fraction = (elapsed_ms - a.offset_ms) as f64 / (b.offset_ms - a.offset_ms) as f64;
        a.position.interpolate(b.position, fraction)
    }
}
