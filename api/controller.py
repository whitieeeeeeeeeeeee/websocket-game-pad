# -*- coding: utf-8 -*-
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Callable
from inputs import UnpluggedError, devices, get_gamepad
import ctypes
import sys

logger = logging.getLogger("controller")


class ControllerManager:
    STATE_IDLE = "idle"
    STATE_WAITING = "waiting"
    STATE_ACTIVE = "active"

    def __init__(self):
        self.state = {
            "buttons": {
                "A": False, "B": False, "X": False, "Y": False,
                "LB": False, "RB": False,
                "Back": False, "Start": False,
                "LS": False, "RS": False,
                "DpadUp": False, "DpadDown": False, "DpadLeft": False, "DpadRight": False,
            },
            "axes": {
                "LX": 0.0, "LY": 0.0,
                "RX": 0.0, "RY": 0.0,
            },
            "triggers": {
                "LT": 0.0, "RT": 0.0,
            },
            "timestamp": datetime.now(),
        }
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.connected = False
        self.device_info = None
        self.on_connection_change: Optional[Callable[[bool, Optional[dict]], None]] = None
        self._lock = threading.Lock()
        self._current_state = self.STATE_IDLE
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._last_axes = {"LX": 0.0, "LY": 0.0, "RX": 0.0, "RY": 0.0}
        self._last_triggers = {"LT": 0.0, "RT": 0.0}
        self._axis_changed = False
        self._trigger_changed = False
        self.AXIS_CHANGE_THRESHOLD = 0.05
        self.WAITING_POLL_INTERVAL = 0.5

    def start(self):
        if self.running:
            logger.warning("ControllerManager already running, ignoring start()")
            return
        self.running = True
        self._consecutive_failures = 0
        self._set_state(self.STATE_WAITING)
        self.thread = threading.Thread(target=self._read_gamepad, daemon=True)
        self.thread.start()
        logger.info("ControllerManager thread started")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._set_state(self.STATE_IDLE)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
            if self.thread.is_alive():
                logger.warning("ControllerManager thread did not stop within 3s")
            else:
                logger.info("ControllerManager thread stopped cleanly")
        self.thread = None

    def get_state(self):
        with self._lock:
            state_copy = {
                "buttons": self.state["buttons"].copy(),
                "axes": self.state["axes"].copy(),
                "triggers": self.state["triggers"].copy(),
                "timestamp": self.state["timestamp"],
                "connected": self.connected,
                "device_info": self.device_info.copy() if self.device_info else None,
            }
            return state_copy

    def is_connected(self):
        with self._lock:
            return self.connected

    def _set_state(self, new_state: str, device_info: Optional[dict] = None):
        with self._lock:
            if self._current_state == new_state:
                return
            old_state = self._current_state
            self._current_state = new_state
            was_connected = self.connected
            is_connected = (new_state == self.STATE_ACTIVE)
            self.connected = is_connected
            if is_connected:
                self.device_info = device_info
            else:
                self.device_info = None
            logger.info(f"State change: {old_state} -> {new_state}")
            if was_connected != is_connected:
                if is_connected:
                    logger.info(f"Gamepad connected — device: {device_info.get('name', 'unknown') if device_info else 'unknown'}")
                else:
                    logger.info("Gamepad disconnected")
        if was_connected != is_connected and self.on_connection_change:
            try:
                self.on_connection_change(is_connected, device_info)
            except Exception as e:
                logger.error(f"Connection change callback error: {e}")

    def _refresh_gamepads(self):
        """刷新 inputs 库的设备列表（修复热插拔检测失败）。"""
        try:
            devices.gamepads.clear()
            devices._detect_gamepads()
            devices._update_all_devices()
        except Exception as e:
            logger.debug(f"Device refresh error: {e}")

    def force_detect(self):
        if not self.running:
            return False, "ControllerManager not running"

        logger.info("Force detecting gamepad...")
        self._refresh_gamepads()

        try:
            gamepads = devices.gamepads
            if gamepads:
                device_info = self._get_device_info()
                if not device_info:
                    device_info = {"name": "Unknown Gamepad"}
                self._consecutive_failures = 0
                self._set_state(self.STATE_ACTIVE, device_info)
                logger.info(f"Force detect successful — found {len(gamepads)} gamepad(s) via devices.gamepads")
                return True, f"Found {len(gamepads)} gamepad(s)"
        except Exception as e:
            logger.debug(f"Error in force_detect via devices.gamepads: {e}")
        
        try:
            get_gamepad()
            device_info = self._get_device_info()
            if not device_info:
                device_info = {"name": "Unknown Gamepad"}
            self._consecutive_failures = 0
            self._set_state(self.STATE_ACTIVE, device_info)
            logger.info("Force detect successful — found gamepad via get_gamepad()")
            return True, "Gamepad found"
        except UnpluggedError:
            pass
        except Exception as e:
            logger.debug(f"Error in force_detect via get_gamepad: {type(e).__name__}: {e}")
        
        if self._current_state == self.STATE_ACTIVE:
            self._set_state(self.STATE_WAITING)
        logger.info("Force detect — no gamepads found")
        return False, "No gamepads found"

    def _get_device_info(self):
        try:
            gamepads = devices.gamepads
            if not gamepads:
                return {"name": "Unknown Gamepad"}
            gamepad = gamepads[0]
            info = {
                "name": getattr(gamepad, "name", "Unknown Gamepad"),
            }
            if hasattr(gamepad, "index"):
                info["index"] = gamepad.index
            return info
        except Exception as e:
            logger.warning(f"Failed to get device info ({type(e).__name__}): {e}")
            return {"name": "Unknown Gamepad"}

    def _read_gamepad(self):
        while self.running:
            try:
                if self._current_state == self.STATE_WAITING:
                    self._loop_waiting()
                elif self._current_state == self.STATE_ACTIVE:
                    self._loop_active()
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Controller read loop error ({type(e).__name__}): {e}")
                if self._current_state == self.STATE_ACTIVE:
                    self._set_state(self.STATE_WAITING)
                time.sleep(1.0)

    def _loop_waiting(self):
        self._refresh_gamepads()
        try:
            gamepads = devices.gamepads
            if gamepads:
                device_info = self._get_device_info()
                if not device_info:
                    device_info = {"name": "Unknown Gamepad"}
                self._consecutive_failures = 0
                self._set_state(self.STATE_ACTIVE, device_info)
                return
        except Exception as e:
            logger.debug(f"Error checking gamepads in waiting loop: {e}")
        
        try:
            get_gamepad()
            device_info = self._get_device_info()
            if not device_info:
                device_info = {"name": "Unknown Gamepad"}
            self._consecutive_failures = 0
            self._set_state(self.STATE_ACTIVE, device_info)
            return
        except UnpluggedError:
            pass
        except Exception as e:
            logger.debug(f"get_gamepad in waiting loop: {type(e).__name__}: {e}")
        
        time.sleep(self.WAITING_POLL_INTERVAL)

    def _loop_active(self):
        gamepads = devices.gamepads
        if not gamepads:
            self._set_state(self.STATE_WAITING)
            return

        try:
            events = get_gamepad()
            self._consecutive_failures = 0
        except UnpluggedError:
            self._consecutive_failures += 1
            logger.warning(f"UnpluggedError detected (failure {self._consecutive_failures}/{self._max_consecutive_failures})")
            if self._consecutive_failures >= self._max_consecutive_failures:
                logger.info("Gamepad unplugged — max consecutive failures reached")
                self._set_state(self.STATE_WAITING)
            return
        except OSError as e:
            self._consecutive_failures += 1
            logger.error(
                f"OSError in get_gamepad() (likely Bluetooth disconnect) "
                f"(failure {self._consecutive_failures}/{self._max_consecutive_failures}): {type(e).__name__}: {e}"
            )
            if self._consecutive_failures >= self._max_consecutive_failures:
                logger.info("Gamepad disconnected due to OSError — max consecutive failures reached")
                self._set_state(self.STATE_WAITING)
            return
        except Exception as e:
            self._consecutive_failures += 1
            logger.error(
                f"Unexpected get_gamepad() error ({type(e).__name__}) "
                f"(failure {self._consecutive_failures}/{self._max_consecutive_failures}): {e}"
            )
            if self._consecutive_failures >= self._max_consecutive_failures:
                logger.info("Gamepad disconnected due to unexpected error — max consecutive failures reached")
                self._set_state(self.STATE_WAITING)
            return

        with self._lock:
            self.state["timestamp"] = datetime.now()
            for event in events:
                self._process_event(event)

    def _process_event(self, event):
        if event.code == "ABS_HAT0Y":
            self.state["buttons"]["DpadUp"] = (event.state == -1)
            self.state["buttons"]["DpadDown"] = (event.state == 1)
        elif event.code == "ABS_HAT0X":
            self.state["buttons"]["DpadLeft"] = (event.state == -1)
            self.state["buttons"]["DpadRight"] = (event.state == 1)
        elif event.code == "BTN_SOUTH":
            self.state["buttons"]["A"] = (event.state == 1)
        elif event.code == "BTN_EAST":
            self.state["buttons"]["B"] = (event.state == 1)
        elif event.code == "BTN_NORTH":
            self.state["buttons"]["Y"] = (event.state == 1)
        elif event.code == "BTN_WEST":
            self.state["buttons"]["X"] = (event.state == 1)
        # 备用按钮映射：某些蓝牙/第三方手柄使用 BTN_A/B/X/Y 事件码
        elif event.code == "BTN_A":
            self.state["buttons"]["A"] = (event.state == 1)
        elif event.code == "BTN_B":
            self.state["buttons"]["B"] = (event.state == 1)
        elif event.code == "BTN_X":
            self.state["buttons"]["X"] = (event.state == 1)
        elif event.code == "BTN_Y":
            self.state["buttons"]["Y"] = (event.state == 1)
        elif event.code == "BTN_TL":
            self.state["buttons"]["LB"] = (event.state == 1)
        elif event.code == "BTN_TR":
            self.state["buttons"]["RB"] = (event.state == 1)
        elif event.code == "BTN_SELECT":
            self.state["buttons"]["Start"] = (event.state == 1)
        elif event.code == "BTN_START":
            self.state["buttons"]["Back"] = (event.state == 1)
        elif event.code == "BTN_THUMBL":
            self.state["buttons"]["LS"] = (event.state == 1)
        elif event.code == "BTN_THUMBR":
            self.state["buttons"]["RS"] = (event.state == 1)
        elif event.code == "ABS_X":
            new_val = self._normalize_axis(event.state)
            if abs(new_val - self._last_axes["LX"]) > self.AXIS_CHANGE_THRESHOLD:
                self._axis_changed = True
                self._last_axes["LX"] = new_val
            self.state["axes"]["LX"] = new_val
        elif event.code == "ABS_Y":
            new_val = self._normalize_axis(event.state)
            if abs(new_val - self._last_axes["LY"]) > self.AXIS_CHANGE_THRESHOLD:
                self._axis_changed = True
                self._last_axes["LY"] = new_val
            self.state["axes"]["LY"] = new_val
        elif event.code == "ABS_RX":
            new_val = self._normalize_axis(event.state)
            if abs(new_val - self._last_axes["RX"]) > self.AXIS_CHANGE_THRESHOLD:
                self._axis_changed = True
                self._last_axes["RX"] = new_val
            self.state["axes"]["RX"] = new_val
        elif event.code == "ABS_RY":
            new_val = self._normalize_axis(event.state)
            if abs(new_val - self._last_axes["RY"]) > self.AXIS_CHANGE_THRESHOLD:
                self._axis_changed = True
                self._last_axes["RY"] = new_val
            self.state["axes"]["RY"] = new_val
        elif event.code == "ABS_Z":
            new_val = self._normalize_trigger(event.state)
            if abs(new_val - self._last_triggers["LT"]) > self.AXIS_CHANGE_THRESHOLD:
                self._trigger_changed = True
                self._last_triggers["LT"] = new_val
            self.state["triggers"]["LT"] = new_val
        elif event.code == "ABS_RZ":
            new_val = self._normalize_trigger(event.state)
            if abs(new_val - self._last_triggers["RT"]) > self.AXIS_CHANGE_THRESHOLD:
                self._trigger_changed = True
                self._last_triggers["RT"] = new_val
            self.state["triggers"]["RT"] = new_val
        # 备用扳机映射：Xbox 蓝牙模式或某些第三方手柄使用 ABS_BRAKE/ABS_GAS
        elif event.code == "ABS_BRAKE":
            new_val = self._normalize_trigger(event.state)
            if abs(new_val - self._last_triggers["LT"]) > self.AXIS_CHANGE_THRESHOLD:
                self._trigger_changed = True
                self._last_triggers["LT"] = new_val
            self.state["triggers"]["LT"] = new_val
        elif event.code == "ABS_GAS":
            new_val = self._normalize_trigger(event.state)
            if abs(new_val - self._last_triggers["RT"]) > self.AXIS_CHANGE_THRESHOLD:
                self._trigger_changed = True
                self._last_triggers["RT"] = new_val
            self.state["triggers"]["RT"] = new_val

    def _normalize_axis(self, value):
        norm = value / 32768.0
        if norm > 1.0:
            norm = 1.0
        if norm < -1.0:
            norm = -1.0
        if abs(norm) < 0.01:
            norm = 0.0
        return norm

    def _normalize_trigger(self, value):
        return value / 255.0

    def has_linear_control_changed(self):
        with self._lock:
            return self._axis_changed or self._trigger_changed

    def clear_linear_control_flags(self):
        with self._lock:
            self._axis_changed = False
            self._trigger_changed = False


controller_manager = ControllerManager()
