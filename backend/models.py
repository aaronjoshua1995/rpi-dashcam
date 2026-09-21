from dataclasses import dataclass


@dataclass(frozen=True)
class Recording:
    """Metadata for a completed recording file."""

    id: str
    filename: str
    stem: str
    duration_seconds: float
    size_bytes: int


@dataclass(frozen=True)
class SystemStats:
    """Normalized system and hardware measurements shown by the UI."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    battery_percent: float
    temperature_celsius: float


@dataclass(frozen=True)
class RecordingStatus:
    """Current state and elapsed duration of the active recording session."""

    recording: bool
    recording_id: str | None = None
    duration_seconds: float = 0.0
