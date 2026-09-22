import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.models import RecordingStatus
from backend.record import RecordFunction
from ui.screens.record import RecordScreen


class RecordingTests(unittest.TestCase):
    """Unit tests for recording storage and stitching behavior."""

    def test_startup_cleanup_removes_files_and_old_sessions(self):
        """Verify startup cleanup removes stale files and session directories."""
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            (staging / "stale.mp4").write_bytes(b"stale")
            old_session = staging / "session-old"
            old_session.mkdir()
            (old_session / "video_001.mp4").write_bytes(b"fragment")

            recorder = RecordFunction(staging_directory=staging)
            getattr(recorder, "_clear_staging_directory")()

            self.assertEqual(list(staging.iterdir()), [])

    def test_format_location_uses_the_session_directory(self):
        """Verify fragments are named relative to their owning session."""
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            recorder = RecordFunction(staging_directory=session)

            location = getattr(recorder, "_format_location")(None, 2, session)

            self.assertEqual(location, str(session / "video_003.mp4"))

    def test_stitch_uses_the_five_newest_segments(self):
        """Verify stitching includes only the five newest fragments."""
        with tempfile.TemporaryDirectory() as staging_directory, tempfile.TemporaryDirectory() as recordings_directory:
            staging = Path(staging_directory)
            recordings = Path(recordings_directory)
            for number in range(1, 7):
                (staging / f"video_{number:03d}.mp4").write_bytes(str(number).encode())

            concat_contents = []

            def run_ffmpeg(command, **_kwargs):
                """Capture the generated concat list instead of invoking FFmpeg."""
                concat_contents.append(
                    Path(command[command.index("-i") + 1]).read_text(encoding="utf-8")
                )
                return SimpleNamespace(returncode=0)

            recorder = RecordFunction(
                recordings_directory=recordings,
                staging_directory=staging,
                command_runner=run_ffmpeg,
            )
            with patch("backend.record.shutil.which", return_value="ffmpeg"):
                getattr(recorder, "_stitch_session")(staging, "recording-1")

            self.assertEqual(
                concat_contents,
                [
                    "file '" + str(staging / "video_002.mp4") + "'\n"
                    "file '" + str(staging / "video_003.mp4") + "'\n"
                    "file '" + str(staging / "video_004.mp4") + "'\n"
                    "file '" + str(staging / "video_005.mp4") + "'\n"
                    "file '" + str(staging / "video_006.mp4") + "'\n"
                ],
            )

    def test_stitch_stops_at_the_given_boundary_fragment(self):
        """Verify a boundary excludes fragments opened after a forced split."""
        with tempfile.TemporaryDirectory() as staging_directory, tempfile.TemporaryDirectory() as recordings_directory:
            staging = Path(staging_directory)
            recordings = Path(recordings_directory)
            for number in range(1, 7):
                (staging / f"video_{number:03d}.mp4").write_bytes(str(number).encode())

            concat_contents = []

            def run_ffmpeg(command, **_kwargs):
                """Capture the generated concat list instead of invoking FFmpeg."""
                concat_contents.append(
                    Path(command[command.index("-i") + 1]).read_text(encoding="utf-8")
                )
                return SimpleNamespace(returncode=0)

            recorder = RecordFunction(
                recordings_directory=recordings,
                staging_directory=staging,
                command_runner=run_ffmpeg,
            )
            with patch("backend.record.shutil.which", return_value="ffmpeg"):
                getattr(recorder, "_stitch_session")(staging, "recording-1", boundary_fragment_number=5)

            self.assertEqual(
                concat_contents,
                [
                    "file '" + str(staging / "video_001.mp4") + "'\n"
                    "file '" + str(staging / "video_002.mp4") + "'\n"
                    "file '" + str(staging / "video_003.mp4") + "'\n"
                    "file '" + str(staging / "video_004.mp4") + "'\n"
                    "file '" + str(staging / "video_005.mp4") + "'\n"
                ],
            )

    def test_finish_pipeline_waits_for_null_state(self):
        """Verify camera teardown completes before a replacement can start."""
        class Gst:
            class Event:
                @staticmethod
                def new_eos():
                    return "eos"

            class MessageType:
                EOS = 1
                ERROR = 2

            class State:
                NULL = "null"

            class StateChangeReturn:
                FAILURE = "failure"

            SECOND = 1

        class Bus:
            def timed_pop_filtered(self, *_args, **_kwargs):
                return SimpleNamespace(type=Gst.MessageType.EOS)

        class Pipeline:
            def __init__(self):
                self.calls = []

            def send_event(self, event):
                self.calls.append(("send_event", event))

            def get_bus(self):
                return Bus()

            def set_state(self, state):
                self.calls.append(("set_state", state))

            def get_state(self, timeout):
                self.calls.append(("get_state", timeout))
                return "success", Gst.State.NULL, None

        recorder = RecordFunction(gst=Gst)
        pipeline = Pipeline()

        getattr(recorder, "_finish_pipeline")(Gst, pipeline)

        self.assertEqual(
            pipeline.calls,
            [
                ("send_event", "eos"),
                ("set_state", Gst.State.NULL),
                ("get_state", recorder.PIPELINE_STOP_TIMEOUT_NS),
            ],
        )


    def test_rotate_retries_start_and_does_not_raise(self):
        """Verify rotate() rides out a transient start() failure instead of crashing."""
        recorder = RecordFunction()
        recorder._pipeline = None

        with patch.object(recorder, "start", side_effect=[RuntimeError("busy"), None]) as start_mock, \
                patch("backend.record.time.sleep") as sleep_mock:
            recorder.rotate()

        self.assertEqual(start_mock.call_count, 2)
        sleep_mock.assert_called_once()

    def test_rotate_gives_up_after_repeated_start_failures(self):
        """Verify rotate() logs and returns instead of raising when start() keeps failing."""
        recorder = RecordFunction()
        recorder._pipeline = None

        with patch.object(recorder, "start", side_effect=RuntimeError("busy")) as start_mock, \
                patch("backend.record.time.sleep"):
            recorder.rotate()

        self.assertEqual(start_mock.call_count, 3)

    def test_rotate_does_not_touch_the_running_pipeline(self):
        """Verify rotate() only stitches in the background and never restarts the camera."""
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            recorder = RecordFunction()
            recorder._session_directory = session
            recorder._recording_id = "recording-1"
            recorder._started_at = 0.0
            pipeline = SimpleNamespace()
            recorder._pipeline = pipeline

            with patch.object(recorder, "start") as start_mock, \
                    patch.object(recorder, "_finish_pipeline") as finish_mock, \
                    patch.object(recorder, "_finalize_rotation") as finalize_mock:
                recorder.rotate()
                for thread in threading.enumerate():
                    if thread.name == "recording-stitcher":
                        thread.join(timeout=1)

            start_mock.assert_not_called()
            finish_mock.assert_not_called()
            self.assertIs(recorder._pipeline, pipeline)
            self.assertEqual(recorder._session_directory, session)
            self.assertNotEqual(recorder._recording_id, "recording-1")
            finalize_mock.assert_called_once_with(session, "recording-1", None)

    def test_rotate_forces_an_immediate_split(self):
        """Verify rotate() asks splitmuxsink to split now instead of waiting for the timer."""
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            recorder = RecordFunction()
            recorder._session_directory = session
            recorder._recording_id = "recording-1"
            recorder._started_at = 0.0
            recorder._latest_fragment_id = 3
            recorder._pipeline = SimpleNamespace()
            splitmuxsink = SimpleNamespace(emit=lambda *_args: None)
            recorder._splitmuxsink = splitmuxsink

            with patch.object(splitmuxsink, "emit") as emit_mock, \
                    patch.object(recorder, "_finalize_rotation") as finalize_mock:
                recorder.rotate()
                for thread in threading.enumerate():
                    if thread.name == "recording-stitcher":
                        thread.join(timeout=1)

            emit_mock.assert_called_once_with("split-now")
            finalize_mock.assert_called_once_with(session, "recording-1", 3)

    def test_finalize_rotation_stitches_through_the_boundary_after_split(self):
        """Verify _finalize_rotation waits for the split, then stitches up to the boundary."""
        recorder = RecordFunction()
        recorder._latest_fragment_id = 2

        with patch.object(recorder, "_stitch_session") as stitch_mock:
            getattr(recorder, "_finalize_rotation")(Path("/tmp"), "recording-1", 1)

        stitch_mock.assert_called_once_with(Path("/tmp"), "recording-1", boundary_fragment_number=2)

    def test_finalize_rotation_skips_when_no_fragment_opened_yet(self):
        """Verify _finalize_rotation does nothing when rotate() precedes the first fragment."""
        recorder = RecordFunction()

        with patch.object(recorder, "_stitch_session") as stitch_mock:
            getattr(recorder, "_finalize_rotation")(Path("/tmp"), "recording-1", None)

        stitch_mock.assert_not_called()


class RecordScreenTests(unittest.TestCase):
    """Unit tests for default recording and button edge handling."""

    class Backend:
        """Minimal backend double used by record-screen tests."""

        def __init__(self):
            """Initialize the call history for the backend double."""
            self.calls = []

        def start_recording(self):
            """Record a start request."""
            self.calls.append("start")

        def rotate_recording(self):
            """Record a rotation request."""
            self.calls.append("rotate")

        def get_recording_status(self):
            """Return an always-active status for screen tests."""
            return RecordingStatus(recording=True, duration_seconds=1.0)

    def test_recording_starts_by_default(self):
        """Verify constructing the record screen starts recording."""
        backend = self.Backend()

        RecordScreen(backend)

        self.assertEqual(backend.calls, ["start"])

    def test_holding_b_only_rotates_once(self):
        """Verify a held B button does not repeatedly rotate recordings."""
        backend = self.Backend()
        screen = RecordScreen(backend)

        screen.update(0.0, {"B": True})
        screen.update(0.0, {"B": True})
        screen.update(0.0, {"B": False})

        self.assertEqual(backend.calls, ["start", "rotate"])


if __name__ == "__main__":
    unittest.main()
