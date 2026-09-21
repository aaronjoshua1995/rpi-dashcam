from typing import Protocol

from .models import Recording, RecordingStatus, SystemStats


class BackendServiceInterface(Protocol):
    """Operations required by UI screens from the application backend."""

    def start_recording(self) -> None:
        """Start recording if no recording is currently active."""
        ...

    def stop_recording(self) -> None:
        """Stop recording and synchronously finalize its output file."""
        ...

    def rotate_recording(self) -> None:
        """Start a new session while finalizing the previous one in the background."""
        ...

    def get_recording_status(self) -> RecordingStatus:
        """Return the active recording state and duration."""
        ...

    def list_recordings(self) -> list[Recording]:
        """Return completed recordings ordered newest first."""
        ...

    def delete_recording(self, recording_id: str) -> None:
        """Delete a completed recording identified by its filename."""
        ...

    def get_system_stats(self) -> SystemStats:
        """Return current CPU, memory, disk, battery, and temperature values."""
        ...
