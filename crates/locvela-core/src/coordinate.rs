use std::fmt;

const EARTH_RADIUS_M: f64 = 6_371_008.8;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GeometryError {
    InvalidCoordinate,
    InvalidFraction,
    AmbiguousAntipodes,
    InvalidTimeline,
}
impl fmt::Display for GeometryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for GeometryError {}

/// Validated WGS-84 degrees. Fields are private to preserve finite/range invariants.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Coordinate {
    latitude: f64,
    longitude: f64,
}
impl Coordinate {
    pub fn new(latitude: f64, longitude: f64) -> Result<Self, GeometryError> {
        if !latitude.is_finite()
            || !longitude.is_finite()
            || !(-90.0..=90.0).contains(&latitude)
            || !(-180.0..=180.0).contains(&longitude)
        {
            return Err(GeometryError::InvalidCoordinate);
        }
        Ok(Self { latitude, longitude })
    }
    pub fn latitude(self) -> f64 {
        self.latitude
    }
    pub fn longitude(self) -> f64 {
        self.longitude
    }
    /// Spherical distance, not a survey-grade ellipsoidal geodesic.
    pub fn distance_m(self, other: Self) -> f64 {
        let lat1 = self.latitude.to_radians();
        let lat2 = other.latitude.to_radians();
        let dlat = lat2 - lat1;
        let dlon = (other.longitude - self.longitude).to_radians();
        let a = (dlat / 2.0).sin().powi(2)
            + lat1.cos() * lat2.cos() * (dlon / 2.0).sin().powi(2);
        2.0 * EARTH_RADIUS_M * a.clamp(0.0, 1.0).sqrt().asin()
    }
    fn unit(self) -> [f64; 3] {
        let lat = self.latitude.to_radians();
        let lon = self.longitude.to_radians();
        [lat.cos() * lon.cos(), lat.cos() * lon.sin(), lat.sin()]
    }
    /// Short-arc spherical interpolation, including date-line crossings.
    /// Opposite points have no unique short arc and require a waypoint.
    pub fn interpolate(self, other: Self, fraction: f64) -> Result<Self, GeometryError> {
        if !fraction.is_finite() || !(0.0..=1.0).contains(&fraction) {
            return Err(GeometryError::InvalidFraction);
        }
        if fraction == 0.0 {
            return Ok(self);
        }
        if fraction == 1.0 {
            return Ok(other);
        }
        let a = self.unit();
        let b = other.unit();
        let dot = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]).clamp(-1.0, 1.0);
        if dot < -1.0 + 1e-12 {
            return Err(GeometryError::AmbiguousAntipodes);
        }
        let angle = dot.acos();
        let (wa, wb) = if angle < 1e-8 {
            (1.0 - fraction, fraction)
        } else {
            (((1.0 - fraction) * angle).sin() / angle.sin(),
             (fraction * angle).sin() / angle.sin())
        };
        let x = wa * a[0] + wb * b[0];
        let y = wa * a[1] + wb * b[1];
        let z = wa * a[2] + wb * b[2];
        Self::new(z.atan2(x.hypot(y)).to_degrees(), y.atan2(x).to_degrees())
    }
}
