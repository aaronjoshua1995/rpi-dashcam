from .interface import BackendServiceInterface
from .library import LibraryFunction
from .record import RecordFunction
from .system import SystemFunction
from .models import Recording, RecordingStatus, SystemStats


class BackendService(BackendServiceInterface):
    """Compose the recorder, library, and system functions behind one API."""

    def __init__(self):
        """Create the backend services used by all screens."""
        self.record_function = RecordFunction()
        self.system_function = SystemFunction()
        self.library_function = LibraryFunction()

    def start_recording(self) -> None:
        """Start the camera recording pipeline."""
        self.record_function.start()

    def stop_recording(self) -> None:
        """Stop and synchronously finalize the active recording."""
        self.record_function.stop()

    def rotate_recording(self) -> None:
        """Rotate to a new recording while finalizing the old one asynchronously."""
        self.record_function.rotate()

    def get_recording_status(self) -> RecordingStatus:
        """Return the current camera recording status."""
        return self.record_function.status()

    def list_recordings(self) -> list[Recording]:
        """Return completed recordings from the library."""
        return self.library_function.list_recordings()

    def delete_recording(self, recording_id: str) -> None:
        """Delete a completed recording from the library."""
        self.library_function.delete_recording(recording_id)

    def get_system_stats(self) -> SystemStats:
        """Return current system statistics."""
        return self.system_function.get_stats()
