# -*- coding: utf-8 -*-
import uuid
import json
import time
import logging
import threading
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

logger = logging.getLogger("recorder")


class RecordingManager:
    STATE_IDLE = "idle"
    STATE_RECORDING = "recording"
    STATE_PAUSED = "paused"
    STATE_PLAYING = "playing"
    STATE_PLAYBACK_PAUSED = "playback_paused"

    MAX_DURATION_SECONDS = 3600

    def __init__(self):
        self._lock = threading.Lock()
        self._recordings: Dict[str, Dict[str, Any]] = {}

        self._rec_state = self.STATE_IDLE
        self._rec_start_time = 0.0
        self._rec_pause_time = 0.0
        self._rec_offset = 0.0
        self._rec_frames: List[Dict[str, Any]] = []
        self._rec_name = ""

        self._play_state = self.STATE_IDLE
        self._play_recording: Optional[Dict[str, Any]] = None
        self._play_frame_index = 0
        self._play_speed = 1.0
        self._play_start_time = 0.0
        self._play_pause_time = 0.0
        self._play_offset = 0.0
        self._play_thread: Optional[threading.Thread] = None
        self._play_running = False

        self._pending_save = False
        self._state_callbacks_pending: List[str] = []
        self._callback_lock = threading.Lock()

        self.on_state_change: Optional[Callable[[str], None]] = None
        self.on_frame: Optional[Callable[[Dict[str, Any]], None]] = None

    def _set_rec_state(self, new_state: str):
        if self._rec_state != new_state:
            self._rec_state = new_state
            combined = self._get_combined_state()
            self._queue_state_callback(combined)

    def _set_play_state(self, new_state: str):
        if self._play_state != new_state:
            self._play_state = new_state
            combined = self._get_combined_state()
            self._queue_state_callback(combined)

    def _queue_state_callback(self, state: str):
        with self._callback_lock:
            self._state_callbacks_pending.append(state)
        threading.Thread(target=self._dispatch_state_callbacks, daemon=True).start()

    def _dispatch_state_callbacks(self):
        if not self.on_state_change:
            return
        while True:
            with self._callback_lock:
                if not self._state_callbacks_pending:
                    return
                state = self._state_callbacks_pending.pop(0)
            try:
                self.on_state_change(state)
            except Exception as e:
                logger.error(f"on_state_change callback error: {e}")

    def _get_combined_state(self) -> str:
        if self._rec_state == self.STATE_RECORDING:
            return self.STATE_RECORDING
        if self._rec_state == self.STATE_PAUSED:
            return self.STATE_PAUSED
        if self._play_state == self.STATE_PLAYING:
            return self.STATE_PLAYING
        if self._play_state == self.STATE_PLAYBACK_PAUSED:
            return self.STATE_PLAYBACK_PAUSED
        return self.STATE_IDLE

    def get_state(self) -> str:
        with self._lock:
            return self._get_combined_state()

    def start_recording(self, name: Optional[str] = None) -> bool:
        with self._lock:
            if self._rec_state in (self.STATE_RECORDING, self.STATE_PAUSED):
                logger.warning("start_recording called while already recording/paused")
                return False

            now = time.time()
            self._rec_frames = []
            self._rec_start_time = now
            self._rec_offset = 0.0
            self._rec_pause_time = 0.0
            self._rec_name = name or f"录制_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._set_rec_state(self.STATE_RECORDING)
            logger.info(f"Recording started: {self._rec_name}")
            return True

    def pause_recording(self) -> bool:
        with self._lock:
            if self._rec_state != self.STATE_RECORDING:
                logger.warning("pause_recording called but not recording")
                return False

            self._rec_pause_time = time.time()
            self._set_rec_state(self.STATE_PAUSED)
            logger.info("Recording paused")
            return True

    def resume_recording(self) -> bool:
        with self._lock:
            if self._rec_state != self.STATE_PAUSED:
                logger.warning("resume_recording called but not paused")
                return False

            pause_duration = time.time() - self._rec_pause_time
            self._rec_offset += pause_duration
            self._rec_pause_time = 0.0
            self._set_rec_state(self.STATE_RECORDING)
            logger.info("Recording resumed")
            return True

    def stop_recording(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._rec_state not in (self.STATE_RECORDING, self.STATE_PAUSED):
                logger.warning("stop_recording called but not recording/paused")
                return None

            end_time = time.time()
            if self._rec_state == self.STATE_PAUSED:
                duration = self._rec_pause_time - self._rec_start_time - self._rec_offset
            else:
                duration = end_time - self._rec_start_time - self._rec_offset

            if duration < 0:
                duration = 0.0

            rec_id = str(uuid.uuid4())
            recording = {
                "id": rec_id,
                "name": self._rec_name,
                "created_at": datetime.now().isoformat(),
                "duration": round(duration, 3),
                "frame_count": len(self._rec_frames),
                "frames": self._rec_frames,
            }

            self._recordings[rec_id] = recording
            self._rec_frames = []
            self._rec_start_time = 0.0
            self._rec_offset = 0.0
            self._rec_pause_time = 0.0
            self._rec_name = ""
            self._set_rec_state(self.STATE_IDLE)

            logger.info(
                f"Recording stopped: {recording['name']} — "
                f"{recording['frame_count']} frames, "
                f"{recording['duration']:.2f}s"
            )
            return recording

    def add_frame(self, state: Dict[str, Any]) -> bool:
        with self._lock:
            if self._rec_state != self.STATE_RECORDING:
                return False

            now = time.time()
            relative_time = now - self._rec_start_time - self._rec_offset

            if relative_time < 0:
                relative_time = 0.0

            if relative_time > self.MAX_DURATION_SECONDS:
                logger.warning("Max recording duration reached, stopping recording")
                self._set_rec_state(self.STATE_IDLE)
                self._pending_save = True
                return False

            frame = {
                "timestamp": round(relative_time, 3),
                "buttons": state.get("buttons", {}).copy(),
                "axes": state.get("axes", {}).copy(),
                "triggers": state.get("triggers", {}).copy(),
            }
            self._rec_frames.append(frame)
            return True

    def get_recording_status(self) -> Dict[str, Any]:
        with self._lock:
            current_time = 0.0
            if self._rec_state == self.STATE_RECORDING:
                current_time = time.time() - self._rec_start_time - self._rec_offset
            elif self._rec_state == self.STATE_PAUSED:
                current_time = self._rec_pause_time - self._rec_start_time - self._rec_offset

            if current_time < 0:
                current_time = 0.0

            return {
                "state": self._rec_state,
                "name": self._rec_name,
                "frame_count": len(self._rec_frames),
                "current_time": round(current_time, 3),
            }

    def start_playback(self, recording_id: str, speed: float = 1.0) -> bool:
        with self._lock:
            if self._play_state in (self.STATE_PLAYING, self.STATE_PLAYBACK_PAUSED):
                logger.warning("start_playback called while already playing/paused")
                return False

            recording = self._recordings.get(recording_id)
            if not recording:
                logger.warning(f"Recording not found: {recording_id}")
                return False

            if not recording.get("frames"):
                logger.warning("Recording has no frames")
                return False

            self._play_recording = recording
            self._play_frame_index = 0
            self._play_speed = speed
            self._play_start_time = time.time()
            self._play_offset = 0.0
            self._play_pause_time = 0.0
            self._play_running = True
            self._play_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._set_play_state(self.STATE_PLAYING)

            logger.info(f"Playback started: {recording['name']} at {speed}x speed")
            self._play_thread.start()
            return True

    def _playback_loop(self):
        last_frame_index = -1
        while self._play_running:
            frame_state = None
            with self._lock:
                if not self._play_running:
                    break

                if self._play_state != self.STATE_PLAYING:
                    time.sleep(0.01)
                    continue

                if not self._play_recording or not self._play_recording.get("frames"):
                    break

                frames = self._play_recording["frames"]
                current_time = (time.time() - self._play_start_time - self._play_offset) * self._play_speed
                total_duration = self._play_recording["duration"]

                if current_time >= total_duration:
                    self._play_frame_index = len(frames) - 1
                    self._play_running = False
                    self._set_play_state(self.STATE_IDLE)
                    logger.info("Playback finished")
                    break

                current_index = 0
                for i, frame in enumerate(frames):
                    if frame["timestamp"] <= current_time:
                        current_index = i
                    else:
                        break

                self._play_frame_index = current_index

                if current_index != last_frame_index and self.on_frame:
                    frame_state = {
                        "buttons": frames[current_index]["buttons"].copy(),
                        "axes": frames[current_index]["axes"].copy(),
                        "triggers": frames[current_index]["triggers"].copy(),
                        "timestamp": frames[current_index]["timestamp"],
                    }
                    last_frame_index = current_index

            if frame_state and self.on_frame:
                try:
                    self.on_frame(frame_state)
                except Exception as e:
                    logger.error(f"on_frame callback error: {e}")

            time.sleep(0.01)

    def pause_playback(self) -> bool:
        with self._lock:
            if self._play_state != self.STATE_PLAYING:
                logger.warning("pause_playback called but not playing")
                return False

            self._play_pause_time = time.time()
            self._set_play_state(self.STATE_PLAYBACK_PAUSED)
            logger.info("Playback paused")
            return True

    def resume_playback(self) -> bool:
        with self._lock:
            if self._play_state != self.STATE_PLAYBACK_PAUSED:
                logger.warning("resume_playback called but not paused")
                return False

            pause_duration = time.time() - self._play_pause_time
            self._play_offset += pause_duration
            self._play_pause_time = 0.0
            self._set_play_state(self.STATE_PLAYING)
            logger.info("Playback resumed")
            return True

    def stop_playback(self) -> bool:
        with self._lock:
            if self._play_state not in (self.STATE_PLAYING, self.STATE_PLAYBACK_PAUSED):
                logger.warning("stop_playback called but not playing/paused")
                return False

            self._play_running = False
            self._play_recording = None
            self._play_frame_index = 0
            self._play_speed = 1.0
            self._play_start_time = 0.0
            self._play_offset = 0.0
            self._play_pause_time = 0.0
            self._set_play_state(self.STATE_IDLE)
            logger.info("Playback stopped")
            return True

    def seek_playback(self, progress: float) -> bool:
        with self._lock:
            if not self._play_recording or not self._play_recording.get("frames"):
                logger.warning("seek_playback called but no recording loaded")
                return False

            if progress < 0.0:
                progress = 0.0
            if progress > 1.0:
                progress = 1.0

            total_duration = self._play_recording["duration"]
            target_time = total_duration * progress

            was_playing = self._play_state == self.STATE_PLAYING

            self._play_start_time = time.time()
            if self._play_speed != 0:
                self._play_offset = -(target_time / self._play_speed)
            else:
                self._play_offset = 0.0
            if was_playing:
                self._play_pause_time = 0.0
            else:
                self._play_pause_time = time.time()

            frames = self._play_recording["frames"]
            current_index = 0
            for i, frame in enumerate(frames):
                if frame["timestamp"] <= target_time:
                    current_index = i
                else:
                    break
            self._play_frame_index = current_index

            if not was_playing and self._play_state == self.STATE_IDLE:
                self._set_play_state(self.STATE_PLAYBACK_PAUSED)

            logger.info(f"Playback seeked to {progress*100:.1f}%")
            return True

    def set_playback_speed(self, speed: float) -> bool:
        with self._lock:
            if speed <= 0:
                logger.warning(f"Invalid playback speed: {speed}")
                return False

            if self._play_recording and self._play_state in (self.STATE_PLAYING, self.STATE_PLAYBACK_PAUSED):
                if self._play_state == self.STATE_PLAYING:
                    ref_time = time.time()
                else:
                    ref_time = self._play_pause_time
                current_time = (ref_time - self._play_start_time - self._play_offset) * self._play_speed
                self._play_speed = speed
                if speed != 0:
                    self._play_offset = ref_time - self._play_start_time - current_time / speed
                logger.info(f"Playback speed set to {speed}x")
            else:
                self._play_speed = speed
                logger.info(f"Playback speed preset to {speed}x")

            return True

    def get_current_frame(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._play_recording or not self._play_recording.get("frames"):
                return None

            frames = self._play_recording["frames"]
            if self._play_frame_index < 0 or self._play_frame_index >= len(frames):
                return None

            frame = frames[self._play_frame_index]
            return {
                "buttons": frame["buttons"].copy(),
                "axes": frame["axes"].copy(),
                "triggers": frame["triggers"].copy(),
                "timestamp": frame["timestamp"],
            }

    def get_playback_status(self) -> Dict[str, Any]:
        with self._lock:
            if not self._play_recording:
                return {
                    "state": self.STATE_IDLE,
                    "recording_id": None,
                    "recording_name": None,
                    "progress": 0.0,
                    "current_time": 0.0,
                    "total_duration": 0.0,
                    "frame_index": 0,
                    "frame_count": 0,
                    "speed": self._play_speed,
                }

            total_duration = self._play_recording["duration"]
            current_time = 0.0

            if self._play_state == self.STATE_PLAYING:
                current_time = (time.time() - self._play_start_time - self._play_offset) * self._play_speed
            elif self._play_state == self.STATE_PLAYBACK_PAUSED:
                current_time = (self._play_pause_time - self._play_start_time - self._play_offset) * self._play_speed

            if current_time < 0:
                current_time = 0.0
            if current_time > total_duration:
                current_time = total_duration

            progress = current_time / total_duration if total_duration > 0 else 0.0

            return {
                "state": self._play_state,
                "recording_id": self._play_recording["id"],
                "recording_name": self._play_recording["name"],
                "progress": round(progress, 4),
                "current_time": round(current_time, 3),
                "total_duration": round(total_duration, 3),
                "frame_index": self._play_frame_index,
                "frame_count": self._play_recording["frame_count"],
                "speed": self._play_speed,
            }

    def list_recordings(self) -> List[Dict[str, Any]]:
        with self._lock:
            result = []
            for rec_id, rec in self._recordings.items():
                result.append({
                    "id": rec["id"],
                    "name": rec["name"],
                    "created_at": rec["created_at"],
                    "duration": rec["duration"],
                    "frame_count": rec["frame_count"],
                })
            result.sort(key=lambda x: x["created_at"], reverse=True)
            return result

    def get_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._recordings.get(recording_id)
            if not rec:
                return None
            return {
                "id": rec["id"],
                "name": rec["name"],
                "created_at": rec["created_at"],
                "duration": rec["duration"],
                "frame_count": rec["frame_count"],
                "frames": [f.copy() for f in rec["frames"]],
            }

    def rename_recording(self, recording_id: str, new_name: str) -> bool:
        with self._lock:
            rec = self._recordings.get(recording_id)
            if not rec:
                logger.warning(f"Recording not found for rename: {recording_id}")
                return False
            old_name = rec["name"]
            rec["name"] = new_name
            logger.info(f"Recording renamed: '{old_name}' -> '{new_name}'")
            return True

    def delete_recording(self, recording_id: str) -> bool:
        with self._lock:
            if recording_id not in self._recordings:
                logger.warning(f"Recording not found for delete: {recording_id}")
                return False

            if self._play_recording and self._play_recording["id"] == recording_id:
                self._play_running = False
                self._play_recording = None
                self._play_frame_index = 0
                self._set_play_state(self.STATE_IDLE)

            rec = self._recordings.pop(recording_id)
            logger.info(f"Recording deleted: {rec['name']}")
            return True

    def export_recording(self, recording_id: str) -> Optional[str]:
        with self._lock:
            rec = self._recordings.get(recording_id)
            if not rec:
                logger.warning(f"Recording not found for export: {recording_id}")
                return None
            try:
                return json.dumps(rec, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Export recording error: {e}")
                return None

    def import_recording(self, json_data: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            try:
                rec = json.loads(json_data)
            except Exception as e:
                logger.error(f"Import recording parse error: {e}")
                return None

            required_fields = ["name", "duration", "frame_count", "frames"]
            for field in required_fields:
                if field not in rec:
                    logger.error(f"Import recording missing field: {field}")
                    return None

            if not isinstance(rec["frames"], list) or len(rec["frames"]) == 0:
                logger.error("Import recording has invalid frames")
                return None

            rec_id = str(uuid.uuid4())
            rec["id"] = rec_id
            if "created_at" not in rec:
                rec["created_at"] = datetime.now().isoformat()

            self._recordings[rec_id] = rec
            logger.info(f"Recording imported: {rec['name']} ({rec['frame_count']} frames)")
            return {
                "id": rec["id"],
                "name": rec["name"],
                "created_at": rec["created_at"],
                "duration": rec["duration"],
                "frame_count": rec["frame_count"],
            }

    def save_to_file(self, filepath: str) -> bool:
        with self._lock:
            try:
                data = {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "recordings": list(self._recordings.values()),
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved {len(self._recordings)} recordings to {filepath}")
                return True
            except Exception as e:
                logger.error(f"Save to file error: {e}")
                return False

    def load_from_file(self, filepath: str) -> int:
        with self._lock:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                recordings = data.get("recordings", [])
                if not isinstance(recordings, list):
                    logger.error("Invalid file format: recordings not a list")
                    return 0

                count = 0
                for rec in recordings:
                    if all(k in rec for k in ["name", "duration", "frame_count", "frames"]):
                        rec_id = rec.get("id", str(uuid.uuid4()))
                        rec["id"] = rec_id
                        if "created_at" not in rec:
                            rec["created_at"] = datetime.now().isoformat()
                        self._recordings[rec_id] = rec
                        count += 1

                logger.info(f"Loaded {count} recordings from {filepath}")
                return count
            except Exception as e:
                logger.error(f"Load from file error: {e}")
                return 0


recording_manager = RecordingManager()
