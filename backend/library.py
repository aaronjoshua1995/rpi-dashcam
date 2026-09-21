from pathlib import Path

from .models import Recording


class LibraryFunction:
    """List and safely delete completed recordings on disk."""

    RECORDINGS_DIRECTORY = Path("/usr/share/rpi-dashcam/recordings")

    def __init__(self, recordings_directory: Path | str | None = None):
        """Create a library backed by the supplied recordings directory."""
        self.recordings_directory = Path(recordings_directory or self.RECORDINGS_DIRECTORY)

    def list_recordings(self) -> list[Recording]:
        """Read recording files and return lightweight metadata for each one."""
        if not self.recordings_directory.is_dir():
            return []

        recordings = []
        for path in self.recordings_directory.iterdir():
            if path.is_file():
                recordings.append(
                    Recording(
                        id=path.name,
                        filename=path.name,
                        stem=path.stem,
                        duration_seconds=0.0,
                        size_bytes=path.stat().st_size,
                    )
                )

        return sorted(
            recordings,
            key=lambda recording: recording.stem,
            reverse=True,
        )

    def delete_recording(self, recording_id: str) -> None:
        """Delete one file after validating that it stays inside the library."""
        recording_path = self.recordings_directory / recording_id
        recordings_directory = self.recordings_directory.resolve()

        if Path(recording_id).name != recording_id or Path(recording_id).is_absolute():
            raise ValueError("recording_id must be a filename")

        try:
            recording_path.resolve().relative_to(recordings_directory)
        except ValueError as error:
            raise ValueError("recording_id must refer to the recordings directory") from error

        if not recording_path.is_file():
            raise FileNotFoundError(recording_path)

        recording_path.unlink()
