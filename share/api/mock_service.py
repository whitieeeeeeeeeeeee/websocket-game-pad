# -*- coding: utf-8 -*-
import logging
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("mock_service")


class MockService:
    def __init__(self):
        self.mock_enabled = True
        self.connected = False
        self.device_info = None
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
        self.on_state_change: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def connect_controller(self, name: Optional[str] = None):
        with self._lock:
            self.connected = True
            self.device_info = {
                "name": name or "Mock Gamepad",
                "index": 0,
                "is_mock": True,
            }
            self.state["timestamp"] = datetime.now()
        logger.info(f"Mock controller connected: {self.device_info['name']}")
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception as e:
                logger.error(f"State change callback error: {e}")
        return True

    def disconnect_controller(self):
        with self._lock:
            was_connected = self.connected
            self.connected = False
            self.device_info = None
            self.state["timestamp"] = datetime.now()
        if was_connected:
            logger.info("Mock controller disconnected")
            if self.on_state_change:
                try:
                    self.on_state_change()
                except Exception as e:
                    logger.error(f"State change callback error: {e}")
        return True

    def get_state(self) -> Dict[str, Any]:
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

    def is_connected(self) -> bool:
        with self._lock:
            return self.connected

    def set_state(self, buttons: Optional[Dict[str, bool]] = None,
                  axes: Optional[Dict[str, float]] = None,
                  triggers: Optional[Dict[str, float]] = None):
        with self._lock:
            if buttons is not None:
                for key, value in buttons.items():
                    if key in self.state["buttons"]:
                        self.state["buttons"][key] = bool(value)
            if axes is not None:
                for key, value in axes.items():
                    if key in self.state["axes"]:
                        self.state["axes"][key] = float(value)
            if triggers is not None:
                for key, value in triggers.items():
                    if key in self.state["triggers"]:
                        self.state["triggers"][key] = float(value)
            self.state["timestamp"] = datetime.now()
        logger.debug("Mock controller state updated")
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception as e:
                logger.error(f"State change callback error: {e}")
        return True

    def press_button(self, button: str, pressed: bool = True):
        with self._lock:
            if button not in self.state["buttons"]:
                logger.warning(f"Unknown button: {button}")
                return False
            self.state["buttons"][button] = pressed
            self.state["timestamp"] = datetime.now()
        logger.debug(f"Mock button {button}: {pressed}")
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception as e:
                logger.error(f"State change callback error: {e}")
        return True

    def move_axis(self, axis: str, value: float):
        with self._lock:
            if axis in self.state["axes"]:
                self.state["axes"][axis] = float(value)
                self.state["timestamp"] = datetime.now()
            elif axis in self.state["triggers"]:
                self.state["triggers"][axis] = float(value)
                self.state["timestamp"] = datetime.now()
            else:
                logger.warning(f"Unknown axis/trigger: {axis}")
                return False
        logger.debug(f"Mock axis {axis}: {value}")
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception as e:
                logger.error(f"State change callback error: {e}")
        return True


mock_service = MockService()
