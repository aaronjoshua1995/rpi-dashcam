import time
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from .models import RecordingStatus


class _EmulatedGst:
    """Minimal GStreamer-like constants used to simulate recording without hardware."""

    class Event:
        @staticmethod
        def new_eos():
            return "eos"

    class State:
        NULL = "null"
        PLAYING = "playing"

    class StateChangeReturn:
        SUCCESS = "success"
        FAILURE = "failure"

    class MessageType:
        EOS = 1
        ERROR = 2

    SECOND = 1_000_000_000


class _EmulatedMessage:
    """Fake bus message standing in for a GStreamer EOS message."""

    def __init__(self, message_type):
        self.type = message_type


class _EmulatedPipeline:
    """No-op pipeline standing in for GStreamer when running the desktop emulator."""

    def __init__(self):
        self._state = _EmulatedGst.State.NULL

    def send_event(self, _event):
        return True

    def get_bus(self):
        return self

    def timed_pop_filtered(self, _timeout, requested_types):
        if requested_types & _EmulatedGst.MessageType.EOS:
            return _EmulatedMessage(_EmulatedGst.MessageType.EOS)
        return None

    def set_state(self, state):
        self._state = state
        return _EmulatedGst.StateChangeReturn.SUCCESS

    def get_state(self, _timeout):
        return _EmulatedGst.StateChangeReturn.SUCCESS, self._state, None


class RecordFunction:
    """Manage camera capture, fragment sessions, and stitched recordings."""

    SEGMENT_DURATION_NS = 1 * 60 * 1_000_000_000
    MAX_SEGMENTS = 6
    RECORDINGS_DIRECTORY = Path("/usr/share/rpi-dashcam/recordings")
    STAGING_DIRECTORY = Path("/mnt/ramdisk/rpi-dashcam-recordings")
    EMULATOR_STAGING_DIRECTORY = Path(tempfile.gettempdir()) / "rpi-dashcam-recordings"
    WIDTH = 1920
    HEIGHT = 1080
    FRAMERATE = 30
    BITRATE = 4_000_000
    PIPELINE_STOP_TIMEOUT_NS = 5 * 1_000_000_000

    def __init__(
        self,
        recordings_directory: Path | str | None = None,
        staging_directory: Path | str | None = None,
        emulate: bool = False,
        gst=None,
        clock=time.monotonic,
        command_runner=subprocess.run,
    ):
        """Configure storage paths and injectable dependencies for recording."""
        default_staging = self.EMULATOR_STAGING_DIRECTORY if emulate else self.STAGING_DIRECTORY
        self.recordings_directory = Path(recordings_directory or self.RECORDINGS_DIRECTORY)
        self.staging_directory = Path(staging_directory or default_staging)
        self._emulate = emulate
        self._gst = gst
        self._clock = clock
        self._command_runner = command_runner
        self._pipeline = None
        self._recording_id = None
        self._started_at = None
        self._session_directory = None
        self._state_lock = threading.Lock()
        self._staging_initialized = False

    def start(self) -> None:
        """Start a new camera session and write fragments to its temp directory."""
        if self._pipeline is not None:
            return

        gst = self._load_gstreamer()
        self.recordings_directory.mkdir(parents=True, exist_ok=True)
        self.staging_directory.mkdir(parents=True, exist_ok=True)
        if not self._staging_initialized:
            self._clear_staging_directory()
            self._staging_initialized = True
        self._session_directory = Path(tempfile.mkdtemp(prefix="session-", dir=self.staging_directory))
        recording_timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")

        if self._emulate:
            pipeline = _EmulatedPipeline()
            pipeline.set_state(gst.State.PLAYING)
            self._pipeline = pipeline
            self._recording_id = recording_timestamp
            self._started_at = self._clock()
            return

        location = self._session_directory / "video_%03d.mp4"
        pipeline_description = (
            "libcamerasrc name=camera ! "
            f"video/x-raw,format=NV21,width={self.WIDTH},height={self.HEIGHT},"
            f"framerate={self.FRAMERATE}/1 ! "
            "videoconvert name=video_convert ! "
            "queue name=pre_encoder_queue ! "
            "v4l2h264enc name=h264_encoder ! "
            "video/x-h264,level=(string)4 ! "
            "queue name=post_encoder_queue ! "
            "h264parse name=h264_parser ! "
            f"splitmuxsink name=segmenter location={location} "
            f"max-size-time={self.SEGMENT_DURATION_NS} "
            f"max-files={self.MAX_SEGMENTS} muxer-factory=mp4mux"
        )

        try:
            pipeline = gst.parse_launch(pipeline_description)
            encoder = pipeline.get_by_name("h264_encoder")
            splitmuxsink = pipeline.get_by_name("segmenter")
            if encoder is None or splitmuxsink is None:
                raise RuntimeError("recording pipeline is missing required elements")
            controls = gst.Structure.new_empty("controls")
            controls.set_value("video_bitrate", self.BITRATE)
            encoder.set_property("extra-controls", controls)
            splitmuxsink.connect(
                "format-location",
                lambda sink, fragment_id, session_directory=self._session_directory:
                self._format_location(sink, fragment_id, session_directory),
            )
            result = pipeline.set_state(gst.State.PLAYING)
            if result == gst.StateChangeReturn.FAILURE:
                raise RuntimeError(self._pipeline_error(pipeline, "could not start recording"))
            result, state, _pending = pipeline.get_state(5 * gst.SECOND)
            if result == gst.StateChangeReturn.FAILURE or state != gst.State.PLAYING:
                raise RuntimeError(self._pipeline_error(pipeline, "recording pipeline did not reach PLAYING"))
        except Exception:
            if "pipeline" in locals() and pipeline is not None:
                pipeline.set_state(gst.State.NULL)
            self._remove_session_directory()
            raise

        self._pipeline = pipeline
        self._recording_id = recording_timestamp
        self._started_at = self._clock()

    def stop(self) -> None:
        """Stop recording, stitch the session, and remove its temp directory."""
        if self._pipeline is None:
            return

        gst = self._load_gstreamer()
        with self._state_lock:
            pipeline, session_directory, recording_id = self._detach_recording()
        try:
            self._finish_pipeline(gst, pipeline)
            self._stitch_session(session_directory, recording_id)
        finally:
            self._remove_session_directory(session_directory)

    def rotate(self) -> None:
        """Start a fresh session while stitching the previous one in the background."""
        if self._pipeline is None:
            self._start_with_retry()
            return

        gst = self._load_gstreamer()
        with self._state_lock:
            pipeline, session_directory, recording_id = self._detach_recording()
        try:
            self._finish_pipeline(gst, pipeline)
        except RuntimeError as error:
            print(f"Could not finalize recording {recording_id}: {error}")
        threading.Thread(
            target=self._stitch_and_remove,
            args=(session_directory, recording_id),
            name="recording-stitcher",
            daemon=True,
        ).start()
        self._start_with_retry()

    def _start_with_retry(self, attempts: int = 3, delay_seconds: float = 1.0) -> None:
        """Retry starting a session to ride out the camera release delay after a rotation."""
        for attempt in range(1, attempts + 1):
            try:
                self.start()
                return
            except RuntimeError as error:
                if attempt == attempts:
                    print(f"Could not start a new recording after rotation: {error}")
                    return
                print(f"Retrying recording start ({attempt}/{attempts}): {error}")
                time.sleep(delay_seconds)

    def status(self) -> RecordingStatus:
        """Return recording status, raising when the pipeline reports an error."""
        if self._pipeline is None or self._started_at is None:
            return RecordingStatus(recording=False)

        error = self._pipeline_error(self._pipeline, None)
        if error is not None:
            self._pipeline.set_state(self._gst.State.NULL)
            self._clear_state()
            raise RuntimeError(error)

        return RecordingStatus(
            recording=True,
            recording_id=str(self._recording_id),
            duration_seconds=self._clock() - self._started_at,
        )

    def _clear_state(self) -> None:
        """Reset active recording state and remove its temporary session."""
        self._pipeline = None
        self._recording_id = None
        self._started_at = None
        self._remove_session_directory()

    def _detach_recording(self):
        """Detach the active pipeline and session for synchronous or async finalization."""
        pipeline = self._pipeline
        session_directory = self._session_directory
        recording_id = self._recording_id
        self._pipeline = None
        self._recording_id = None
        self._started_at = None
        self._session_directory = None
        return pipeline, session_directory, recording_id

    def _finish_pipeline(self, gst, pipeline) -> None:
        """Send EOS, wait for GStreamer to finish, and stop the pipeline."""
        pipeline.send_event(gst.Event.new_eos())
        message = pipeline.get_bus().timed_pop_filtered(
            10 * gst.SECOND,
            gst.MessageType.EOS | gst.MessageType.ERROR,
        )
        pipeline.set_state(gst.State.NULL)
        stop_result, stop_state, _pending = pipeline.get_state(self.PIPELINE_STOP_TIMEOUT_NS)

        if message is None:
            raise RuntimeError("timed out while finalizing the recording")
        if message.type == gst.MessageType.ERROR:
            error, debug = message.parse_error()
            raise RuntimeError(f"recording pipeline failed: {error}; {debug}")
        if stop_result == gst.StateChangeReturn.FAILURE or stop_state != gst.State.NULL:
            raise RuntimeError("timed out while stopping the recording pipeline")

    def _stitch_and_remove(self, session_directory, recording_id) -> None:
        """Stitch a detached session and always remove its temporary directory."""
        try:
            self._stitch_session(session_directory, recording_id)
        except (OSError, RuntimeError) as error:
            print(f"Could not stitch recording {recording_id}: {error}")
        finally:
            self._remove_session_directory(session_directory)

    def _format_location(self, _splitmuxsink, fragment_id: int, session_directory) -> str:
        """Build the path for one splitmuxsink fragment in a specific session."""
        return str(session_directory / f"video_{fragment_id + 1:03d}.mp4")

    def _stitch_session(self, session_directory, recording_id) -> None:
        """Stitch the five newest session fragments into a completed MP4."""
        if session_directory is None or self._emulate:
            return

        segments = sorted(session_directory.glob("video_*.mp4"))
        segments = segments[-5:]
        if not segments:
            raise RuntimeError("recording stopped without producing any segments")

        output_name = f"{recording_id}.mp4"
        output_path = self.recordings_directory / output_name
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="concat-", suffix=".txt", dir=session_directory, delete=False
        ) as concat_file:
            concat_path = Path(concat_file.name)
            for segment in segments:
                concat_file.write(f"file '{segment.as_posix()}'\n")

        try:
            if shutil.which("ffmpeg") is None:
                raise RuntimeError("ffmpeg is required to stitch recording segments")
            result = self._command_runner(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_path),
                    "-c",
                    "copy",
                    str(output_path),
                ],
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed while stitching recording: {result.returncode}")
        finally:
            concat_path.unlink(missing_ok=True)

    def _remove_session_directory(self, session_directory=None) -> None:
        """Delete a temporary session directory without affecting other sessions."""
        session_directory = session_directory or self._session_directory
        if session_directory is not None:
            shutil.rmtree(session_directory, ignore_errors=True)
            if session_directory == self._session_directory:
                self._session_directory = None

    def _clear_staging_directory(self) -> None:
        """Remove stale files and sessions left in staging by an earlier run."""
        for path in self.staging_directory.iterdir():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    def _pipeline_error(self, pipeline, fallback):
        """Read one immediate GStreamer error message or return a fallback."""
        message = pipeline.get_bus().timed_pop_filtered(
            0,
            self._gst.MessageType.ERROR,
        )
        if message is None:
            return fallback
        error, debug = message.parse_error()
        return f"recording pipeline failed: {error}; {debug}"

    def _load_gstreamer(self):
        """Load and initialize GStreamer lazily, or use the emulated stand-in without hardware."""
        if self._gst is None:
            if self._emulate:
                self._gst = _EmulatedGst
                return self._gst
            try:
                import gi
                gi.require_version("Gst", "1.0")
                from gi.repository import Gst
            except (ImportError, ValueError) as error:
                raise RuntimeError(
                    "GStreamer Python bindings are required on the Raspberry Pi"
                ) from error
            Gst.init(None)
            self._gst = Gst
        return self._gst
