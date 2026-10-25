//! Device-independent geometry and conservative session state.
//! No device injection, coordinate conversion, or application compatibility is implied.
#![forbid(unsafe_code)]
mod coordinate;
mod route;
mod session;
pub use coordinate::{Coordinate, GeometryError};
pub use route::{Route, TimedPoint};
pub use session::{Event, Session, SessionError, State};
